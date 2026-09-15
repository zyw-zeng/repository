"""协调 LangGraph 执行、会话消息和 Agent 运行记录持久化。"""

import time
from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models import BaseChatModel
from sqlalchemy.orm import Session

from app.agent.graph import build_agent_graph
from app.agent.nodes import AGENT_FAILURE_ANSWER, AgentNodes
from app.agent.router import route_by_rule
from app.agent.runtime import AgentCancelledError, raise_if_agent_cancelled
from app.agent.state import AgentState
from app.agent.tools import AgentToolbox
from app.career_agent.graph import build_career_agent_graph
from app.career_agent.nodes import CareerAgentNodes
from app.career_agent.router import select_career_tools
from app.career_agent.state import CareerAgentState
from app.career_agent.tools import CareerToolbox
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.knowledge.types import SearchFilters
from app.llm.factory import create_chat_model, create_router_model
from app.services.agent_tool_service import AgentToolService
from app.services.career_advice_service import CareerAdviceService
from app.services.chat_service import ChatService
from app.storage.models import AgentRun, Conversation, Message
from app.storage.repositories.agent_runs import AgentRunRepository
from app.storage.repositories.conversations import ConversationRepository


@dataclass(slots=True)
class AgentExecution:
    """一次 Agent 请求的最终结果和可展示执行轨迹。"""

    run_id: str
    conversation_id: str
    request_id: str
    answer: str
    answer_mode: str
    grounded: bool
    degraded: bool
    citations: list[dict[str, Any]] = field(default_factory=list)
    resources: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    timings: dict[str, int] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    cancelled: bool = False


class AgentService:
    """提供有状态、有界并且执行结果可审计的 Agent 能力。"""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        model: BaseChatModel | None = None,
        router_model: BaseChatModel | None = None,
        answer_model: BaseChatModel | None = None,
        tool_service: AgentToolService | None = None,
    ):
        """绑定工作单元，并允许测试注入模型和工具服务。"""
        self.session = session
        self.settings = settings or get_settings()
        self.model = model
        self.router_model = router_model
        self.answer_model = answer_model
        self.tool_service = tool_service
        self.conversations = ConversationRepository(session)
        self.runs = AgentRunRepository(session)

    def create_conversation(self, title: str = "新会话") -> Conversation:
        """创建并持久化一个会话。"""
        conversation = self.conversations.add(Conversation(title=title.strip() or "新会话"))
        self.session.commit()
        return conversation

    def get_conversation(self, conversation_id: str) -> Conversation:
        """读取会话，不存在时返回统一业务错误。"""
        conversation = self.conversations.get(conversation_id)
        if conversation is None:
            raise AppError("会话不存在", status_code=404, code="conversation_not_found")
        return conversation

    def get_messages(self, conversation_id: str, *, limit: int = 50) -> list[Message]:
        """读取会话最近消息。"""
        self.get_conversation(conversation_id)
        return self.conversations.list_messages(conversation_id, limit=limit)

    def list_conversations(self, *, offset: int = 0, limit: int = 50) -> list[Conversation]:
        """分页列出全部会话；调用入口必须先完成管理员鉴权。"""
        return self.conversations.list_conversations(offset=offset, limit=limit)

    def delete_conversation(self, conversation_id: str) -> None:
        """删除会话及其消息，不存在时返回统一 404。"""
        self.get_conversation(conversation_id)
        self.conversations.delete(conversation_id)
        self.session.commit()

    def validate_run_request(self, conversation_id: str, request_id: str) -> Conversation:
        """在开始普通或流式响应前验证会话和请求幂等键。"""
        conversation = self.get_conversation(conversation_id)
        if self.runs.get_by_request_id(request_id) is not None:
            raise AppError("该请求已经执行", status_code=409, code="duplicate_request")
        return conversation

    def run(
        self,
        conversation_id: str,
        question: str,
        request_id: str,
        *,
        filters: SearchFilters | None = None,
    ) -> AgentExecution:
        """执行一次 Agent 工作流，并在成功或失败路径上都持久化结果。"""
        conversation = self.validate_run_request(conversation_id, request_id)

        run = self.runs.add(
            AgentRun(
                conversation_id=conversation.id,
                request_id=request_id,
                status="running",
                tool_calls_json=[],
            )
        )
        self.session.commit()
        start_time = time.perf_counter()
        try:
            raise_if_agent_cancelled()
            history_messages = self.conversations.list_messages(
                conversation.id,
                limit=self.settings.rag_max_history_messages,
            )
            history = [(message.role, message.content) for message in history_messages]
            career_tools = select_career_tools(question)
            if conversation.active_jd_analysis_id and career_tools:
                final_state = self._run_career_agent(conversation, question)
                raise_if_agent_cancelled()
                return self._persist_result(
                    conversation,
                    run,
                    question,
                    final_state,  # type: ignore[arg-type]
                    start_time,
                )
            # 本地确定性工具不需要创建或调用模型，简历下载因此可以即时响应。
            local_tools = {"list_documents", "get_document_info", "get_resume"}
            selected_by_rule = route_by_rule(question)
            requires_models = selected_by_rule not in local_tools
            # 单一 model 参数只用于兼容测试；生产环境拆分路由与回答模型。
            router_model = self.router_model or self.model
            answer_model = self.answer_model or self.model
            if requires_models:
                router_model = router_model or create_router_model(self.settings)
                answer_model = answer_model or create_chat_model(self.settings)
            tool_service = self.tool_service
            if tool_service is None:
                chat_service = None
                if answer_model is not None and router_model is not None:
                    chat_service = ChatService(
                        self.session,
                        self.settings,
                        model=answer_model,
                        rewrite_model=router_model,
                    )
                tool_service = AgentToolService(
                    self.session,
                    self.settings,
                    chat_service=chat_service,
                )
            graph = build_agent_graph(
                AgentNodes(router_model, AgentToolbox(tool_service)),
                self.settings,
            )
            active_filters = filters or SearchFilters()
            initial_state: AgentState = {
                "request_id": request_id,
                "conversation_id": conversation.id,
                "question": question.strip(),
                "current_query": question.strip(),
                "history": history,
                "document_ids": active_filters.document_ids,
                "filenames": active_filters.filenames,
                "retrieval_attempts": 0,
                "step_count": 0,
                "max_steps": self.settings.agent_max_steps,
                "max_retrieval_attempts": self.settings.agent_max_retrieval_attempts,
                "deadline": time.monotonic() + self.settings.agent_timeout_seconds,
                "degraded": False,
                "timings": {},
                "steps": [],
            }
            final_state = graph.invoke(
                initial_state,
                config={"recursion_limit": self.settings.agent_max_steps + 2},
            )
            raise_if_agent_cancelled()
            return self._persist_result(conversation, run, question, final_state, start_time)
        except AgentCancelledError:
            self.session.rollback()
            return self._persist_cancelled(conversation_id, run.id, question, start_time)
        except Exception as exc:
            # 图级异常仍需保存用户请求、降级答复和失败运行记录。
            self.session.rollback()
            return self._persist_failure(conversation_id, run.id, question, exc, start_time)

    def _run_career_agent(
        self,
        conversation: Conversation,
        question: str,
    ) -> CareerAgentState:
        """使用当前会话绑定岗位运行独立、只读且有界的 Career Agent。"""
        advice_service = CareerAdviceService(self.session, self.settings, conversation)
        if advice_service.context is None:
            raise RuntimeError("当前会话绑定的岗位报告不存在或尚未完成")
        graph = build_career_agent_graph(
            CareerAgentNodes(CareerToolbox(advice_service), advice_service.context)
        )
        initial_state: CareerAgentState = {
            "question": question.strip(),
            "analysis_id": advice_service.context.analysis_id,
            "job_title": advice_service.context.job_title,
            "profile_version": advice_service.context.profile_version,
            "selected_tools": [],
            "next_tool_index": 0,
            "sections": [],
            "evidence": [],
            "step_count": 0,
            "max_steps": self.settings.career_agent_max_steps,
            "deadline": time.monotonic() + self.settings.career_agent_timeout_seconds,
            "degraded": False,
            "timings": {},
            "steps": [],
        }
        return graph.invoke(
            initial_state,
            config={"recursion_limit": self.settings.career_agent_max_steps + 2},
        )

    def _persist_result(
        self,
        conversation: Conversation,
        run: AgentRun,
        question: str,
        state: AgentState,
        start_time: float,
    ) -> AgentExecution:
        """在同一事务中保存双方消息和 Agent 最终状态。"""
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        answer = state.get("answer") or AGENT_FAILURE_ANSWER
        degraded = state.get("degraded", False) or not state.get("answer")
        citations = state.get("citations", [])
        resources = state.get("resources", [])
        steps = state.get("steps", [])
        timings = {**state.get("timings", {}), "total_ms": duration_ms}
        self._add_messages(conversation, question, answer, citations, resources)
        self.runs.finish(
            run,
            status="degraded" if degraded else "completed",
            tool_calls=steps,
            duration_ms=duration_ms,
            error_message=state.get("error"),
        )
        self.session.commit()
        return AgentExecution(
            run_id=run.id,
            conversation_id=conversation.id,
            request_id=run.request_id,
            answer=answer,
            answer_mode=state.get("answer_mode", "agent"),
            grounded=state.get("grounded", False),
            degraded=degraded,
            citations=citations,
            resources=resources,
            steps=steps,
            duration_ms=duration_ms,
            timings=timings,
        )

    def _persist_cancelled(
        self,
        conversation_id: str,
        run_id: str,
        question: str,
        start_time: float,
    ) -> AgentExecution:
        """保存用户主动停止的运行，避免误记为系统故障或完整回答。"""
        conversation = self.get_conversation(conversation_id)
        run = self.runs.get(run_id)
        if run is None:
            raise RuntimeError("Agent 运行记录意外丢失")
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        answer = "回答已停止。"
        steps = [{"node": "cancel", "status": "cancelled"}]
        self._add_messages(conversation, question, answer, [], [])
        self.runs.finish(
            run,
            status="cancelled",
            tool_calls=steps,
            duration_ms=duration_ms,
            error_message="agent_cancelled",
        )
        self.session.commit()
        return AgentExecution(
            run_id=run.id,
            conversation_id=conversation.id,
            request_id=run.request_id,
            answer=answer,
            answer_mode="agent",
            grounded=False,
            degraded=False,
            steps=steps,
            duration_ms=duration_ms,
            timings={"total_ms": duration_ms},
            cancelled=True,
        )

    def _persist_failure(
        self,
        conversation_id: str,
        run_id: str,
        question: str,
        exc: Exception,
        start_time: float,
    ) -> AgentExecution:
        """图执行抛出异常时恢复 ORM 对象并持久化可控降级结果。"""
        conversation = self.get_conversation(conversation_id)
        run = self.runs.get(run_id)
        if run is None:
            raise RuntimeError("Agent 运行记录意外丢失") from exc
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        steps = [{"node": "graph", "status": "failed", "error_type": type(exc).__name__}]
        self._add_messages(conversation, question, AGENT_FAILURE_ANSWER, [], [])
        self.runs.finish(
            run,
            status="failed",
            tool_calls=steps,
            duration_ms=duration_ms,
            error_message=f"{type(exc).__name__}: {exc}",
        )
        self.session.commit()
        return AgentExecution(
            run_id=run.id,
            conversation_id=conversation.id,
            request_id=run.request_id,
            answer=AGENT_FAILURE_ANSWER,
            answer_mode="agent",
            grounded=False,
            degraded=True,
            steps=steps,
            duration_ms=duration_ms,
            timings={"total_ms": duration_ms},
        )

    def _add_messages(
        self,
        conversation: Conversation,
        question: str,
        answer: str,
        citations: list[dict[str, Any]],
        resources: list[dict[str, Any]],
    ) -> None:
        """追加用户与助手消息，并用首个问题更新默认标题。"""
        self.conversations.add_message(
            Message(conversation_id=conversation.id, role="user", content=question)
        )
        self.conversations.add_message(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=answer,
                citations_json=citations,
                resources_json=resources,
            )
        )
        if conversation.title == "新会话":
            conversation.title = question[:50]
