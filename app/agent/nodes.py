"""实现意图判断、工具执行、检索评价和有界重试节点。"""

import time
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import INTENT_SYSTEM_PROMPT, REWRITE_SYSTEM_PROMPT
from app.agent.router import route_by_rule
from app.agent.runtime import (
    AgentCancelledError,
    emit_agent_event,
    emit_agent_step,
    raise_if_agent_cancelled,
)
from app.agent.state import AgentState
from app.agent.tools import ALLOWED_TOOL_NAMES, AgentToolbox
from app.knowledge.rag import REFUSAL_ANSWER, message_text

AGENT_FAILURE_ANSWER = "Agent 暂时无法完成这次请求，请稍后重试。"


class AgentNodes:
    """持有模型和工具依赖，供 LangGraph 节点安全复用。"""

    def __init__(self, model: BaseChatModel | None, toolbox: AgentToolbox):
        """绑定模型与白名单工具箱。"""
        self.model = model
        self.toolbox = toolbox

    @staticmethod
    def _limit_reached(state: AgentState) -> bool:
        """统一检查总步骤和截止时间。"""
        return (
            state.get("step_count", 0) >= state["max_steps"]
            or time.monotonic() >= state["deadline"]
        )

    @staticmethod
    def _step(name: str, **details: Any) -> list[dict[str, Any]]:
        """创建可持久化但不包含文档正文的简洁轨迹。"""
        return emit_agent_step(name, **details)

    def classify_intent(self, state: AgentState) -> dict[str, Any]:
        """规则优先选择工具，只有含糊输入才调用快速路由模型。"""
        if self._limit_reached(state):
            return self._limit_fallback(state, "classify_intent")
        started_at = time.perf_counter()
        try:
            raise_if_agent_cancelled()
            selected_tool = route_by_rule(state["question"])
            router = "rule"
            if selected_tool is None:
                if self.model is None:
                    raise RuntimeError("当前请求需要路由模型，但模型尚未初始化")
                response = self.model.invoke(
                    [
                        SystemMessage(content=INTENT_SYSTEM_PROMPT),
                        HumanMessage(content=state["question"]),
                    ]
                )
                raise_if_agent_cancelled()
                selected_tool = message_text(response).strip().lower()
                router = "model"
            if selected_tool not in ALLOWED_TOOL_NAMES - {"read_document_chunks"}:
                # 明确的知识问题已由本地规则提前拦截；模型异常输出按普通对话降级，
                # 避免无关闲聊被错误送入知识库并触发拒答。
                selected_tool = "answer_casual"
            router_ms = self._finish_timing("router", started_at)
            return {
                "intent": selected_tool,
                "selected_tool": selected_tool,
                "step_count": state.get("step_count", 0) + 1,
                "timings": {**state.get("timings", {}), "router_ms": router_ms},
                "steps": self._step(
                    "classify_intent",
                    status="completed",
                    selected_tool=selected_tool,
                    router=router,
                    duration_ms=router_ms,
                ),
            }
        except AgentCancelledError:
            raise
        except Exception as exc:
            # ZYW 相关问题已由本地规则命中；剩余含糊输入失败时按普通对话降级。
            router_ms = self._finish_timing("router", started_at)
            return {
                "intent": "answer_casual",
                "selected_tool": "answer_casual",
                "step_count": state.get("step_count", 0) + 1,
                "degraded": True,
                "error": str(exc),
                "timings": {**state.get("timings", {}), "router_ms": router_ms},
                "steps": self._step(
                    "classify_intent",
                    status="fallback",
                    selected_tool="answer_casual",
                    router="fallback",
                    duration_ms=router_ms,
                ),
            }

    def execute_tool(self, state: AgentState) -> dict[str, Any]:
        """调用模型选择的白名单工具，并把输出转换为统一状态。"""
        if self._limit_reached(state):
            return self._limit_fallback(state, "execute_tool")
        tool_name = state["selected_tool"]
        started_at = time.perf_counter()
        try:
            raise_if_agent_cancelled()
            arguments = self._tool_arguments(tool_name, state)
            result = self.toolbox.invoke(tool_name, arguments)
            raise_if_agent_cancelled()
            update = self._normalize_tool_result(tool_name, result, state)
            tool_ms = self._finish_timing("tool", started_at)
            update["timings"] = {
                **state.get("timings", {}),
                **update.get("timings", {}),
                "tool_ms": tool_ms,
            }
            update.update(
                {
                    "step_count": state.get("step_count", 0) + 1,
                    "steps": self._step(
                        "execute_tool",
                        status="completed",
                        tool=tool_name,
                        attempt=update.get(
                            "retrieval_attempts",
                            state.get("retrieval_attempts", 0),
                        ),
                        duration_ms=tool_ms,
                    ),
                }
            )
            return update
        except AgentCancelledError:
            raise
        except Exception as exc:
            tool_ms = self._finish_timing("tool", started_at)
            return {
                "answer": AGENT_FAILURE_ANSWER,
                "answer_mode": "agent",
                "grounded": False,
                "citations": [],
                "degraded": True,
                "error": str(exc),
                "timings": {**state.get("timings", {}), "tool_ms": tool_ms},
                "step_count": state.get("step_count", 0) + 1,
                "steps": self._step(
                    "execute_tool",
                    status="failed",
                    tool=tool_name,
                    error_type=type(exc).__name__,
                    duration_ms=tool_ms,
                ),
            }

    def rewrite_for_retry(self, state: AgentState) -> dict[str, Any]:
        """为第二次检索生成不同表述，不改变用户问题的事实边界。"""
        if self._limit_reached(state):
            return self._limit_fallback(state, "rewrite_for_retry")
        started_at = time.perf_counter()
        try:
            raise_if_agent_cancelled()
            if self.model is None:
                raise RuntimeError("检索重写需要模型，但模型尚未初始化")
            response = self.model.invoke(
                [
                    SystemMessage(content=REWRITE_SYSTEM_PROMPT),
                    HumanMessage(content=f"原问题：{state['question']}\n当前查询：{state['current_query']}"),
                ]
            )
            raise_if_agent_cancelled()
            rewritten = message_text(response).strip('“”"') or state["current_query"]
            rewrite_ms = self._finish_timing("retry_rewrite", started_at)
            return {
                "current_query": rewritten,
                "step_count": state.get("step_count", 0) + 1,
                "timings": {
                    **state.get("timings", {}),
                    "retry_rewrite_ms": rewrite_ms,
                },
                "steps": self._step(
                    "rewrite_for_retry",
                    status="completed",
                    duration_ms=rewrite_ms,
                ),
            }
        except AgentCancelledError:
            raise
        except Exception as exc:
            rewrite_ms = self._finish_timing("retry_rewrite", started_at)
            return {
                "answer": REFUSAL_ANSWER,
                "answer_mode": "knowledge_base",
                "grounded": False,
                "citations": [],
                "degraded": True,
                "error": str(exc),
                "timings": {
                    **state.get("timings", {}),
                    "retry_rewrite_ms": rewrite_ms,
                },
                "step_count": state.get("step_count", 0) + 1,
                "steps": self._step(
                    "rewrite_for_retry",
                    status="failed",
                    error_type=type(exc).__name__,
                    duration_ms=rewrite_ms,
                ),
            }

    @staticmethod
    def route_after_tool(state: AgentState) -> str:
        """只有知识检索无依据且仍有预算时才进入重试节点。"""
        should_retry = (
            state.get("selected_tool") == "search_knowledge"
            and not state.get("grounded", False)
            and not state.get("degraded", False)
            and state.get("retry_allowed", True)
            and state.get("retrieval_attempts", 0) < state["max_retrieval_attempts"]
            and state.get("step_count", 0) < state["max_steps"]
            and time.monotonic() < state["deadline"]
        )
        return "retry" if should_retry else "finish"

    @staticmethod
    def route_after_retry(state: AgentState) -> str:
        """改写失败或达到限制时结束，否则再次调用知识检索工具。"""
        if state.get("degraded", False) or state.get("step_count", 0) >= state["max_steps"]:
            return "finish"
        if time.monotonic() >= state["deadline"]:
            return "finish"
        return "execute"

    @staticmethod
    def _tool_arguments(tool_name: str, state: AgentState) -> dict[str, Any]:
        """按工具名称构造经过限制的结构化参数。"""
        if tool_name == "answer_casual":
            return {"question": state["question"], "history": state.get("history", [])}
        if tool_name == "search_knowledge":
            return {
                "question": state["current_query"],
                # 第二次检索已经由重试节点改写，不再让 RAG 根据历史覆盖这次改写。
                "history": (
                    state.get("history", [])
                    if state.get("retrieval_attempts", 0) == 0
                    else []
                ),
                "document_ids": state.get("document_ids", []),
                "filenames": state.get("filenames", []),
            }
        if tool_name == "list_documents":
            return {}
        if tool_name == "get_document_info":
            return {"reference": state["question"]}
        if tool_name == "summarize_document":
            return {"reference": state["question"], "history": state.get("history", [])}
        if tool_name == "get_resume":
            return {}
        raise ValueError(f"工具缺少参数映射：{tool_name}")

    @staticmethod
    def _normalize_tool_result(
        tool_name: str,
        result: Any,
        state: AgentState,
    ) -> dict[str, Any]:
        """把不同工具输出整理成 API 可直接返回的统一字段。"""
        if tool_name in {"answer_casual", "search_knowledge", "summarize_document"}:
            attempts = state.get("retrieval_attempts", 0)
            if tool_name == "search_knowledge":
                attempts += 1
            return {
                "answer": result["answer"],
                "answer_mode": result["answer_mode"],
                "grounded": result["grounded"],
                "citations": result["citations"],
                "retrieved_count": result["retrieved_count"],
                "retrieval_attempts": attempts,
                "timings": result.get("timings", {}),
                "retry_allowed": result.get("retry_allowed", True),
            }
        if tool_name == "list_documents":
            if not result:
                answer = "知识库中还没有文档。"
            else:
                lines = [
                    f"- {item['filename']}（状态：{item['status']}，ID：{item['id']}）"
                    for item in result
                ]
                answer = "知识库文档：\n" + "\n".join(lines)
            return {"answer": answer, "answer_mode": "agent", "grounded": False, "citations": []}
        if tool_name == "get_document_info":
            answer = (
                f"文档《{result['filename']}》状态为 {result['status']}，"
                f"共 {result['chunk_count']} 个切片，活动索引版本为 "
                f"{result['active_index_version']}。"
            )
            return {"answer": answer, "answer_mode": "agent", "grounded": False, "citations": []}
        if tool_name == "get_resume":
            return {
                "answer": "这是曾有为的 AI Agent 应用开发简历，你可以在线查看或直接下载 PDF。",
                "answer_mode": "agent",
                "grounded": False,
                "citations": [],
                "resources": [result],
            }
        raise ValueError(f"无法处理工具结果：{tool_name}")

    @staticmethod
    def _limit_fallback(state: AgentState, node_name: str) -> dict[str, Any]:
        """步骤或时间用尽时立即构造可控降级结果。"""
        return {
            "answer": AGENT_FAILURE_ANSWER,
            "answer_mode": "agent",
            "grounded": False,
            "citations": [],
            "degraded": True,
            "error": "agent_limit_reached",
            "step_count": state.get("step_count", 0),
            "steps": AgentNodes._step(node_name, status="limit_reached"),
        }

    @staticmethod
    def _finish_timing(stage: str, started_at: float) -> int:
        """结束计时并将阶段耗时实时发送给流式客户端。"""
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        emit_agent_event("timing", {"stage": stage, "duration_ms": duration_ms})
        return duration_ms
