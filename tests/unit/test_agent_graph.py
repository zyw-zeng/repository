"""LangGraph 工具选择、有限重试和降级路径单元测试。"""

import time
from dataclasses import asdict

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.agent.graph import build_agent_graph
from app.agent.nodes import AgentNodes
from app.agent.state import AgentState
from app.agent.tools import AgentToolbox
from app.core.config import Settings
from app.knowledge.rag import REFUSAL_ANSWER
from app.knowledge.types import RagAnswer


class StubAgentToolService:
    """记录工具调用并按队列返回可靠 RAG 结果。"""

    def __init__(self, rag_results: list[RagAnswer] | None = None):
        """保存依次返回的 RAG 结果。"""
        self.rag_results = rag_results or []
        self.search_queries: list[str] = []
        self.list_calls = 0

    def answer_casual(self, question: str, history: list[tuple[str, str]]) -> RagAnswer:
        """返回固定闲聊结果。"""
        return RagAnswer(question, "casual", False, question)

    def search_knowledge(self, question: str, history: object, filters: object) -> RagAnswer:
        """记录查询并返回队列中的下一项。"""
        self.search_queries.append(question)
        return self.rag_results.pop(0)

    def list_documents(self) -> list[dict]:
        """返回固定文档列表。"""
        self.list_calls += 1
        return [
            {
                "id": "doc-1",
                "filename": "知识.md",
                "status": "ready",
                "chunk_count": 2,
                "active_index_version": 1,
            }
        ]

    def get_document_info(self, reference: str) -> dict:
        """返回固定文档信息。"""
        return {
            "id": "doc-1",
            "filename": "知识.md",
            "file_type": "md",
            "status": "ready",
            "size_bytes": 100,
            "chunk_count": 2,
            "active_index_version": 1,
        }

    def read_document_chunks(self, reference: str, *, limit: int = 5) -> list[dict]:
        """返回固定活动切片。"""
        return []

    def summarize_document(self, reference: str, history: object) -> RagAnswer:
        """返回固定文档摘要。"""
        return RagAnswer("摘要。[1]", "knowledge_base", True, reference)

    def get_resume(self) -> dict:
        """返回固定简历资源。"""
        return {
            "type": "resume",
            "title": "曾有为｜AI Agent 应用开发",
            "description": "AI Agent 项目简历",
            "filename": "resume.pdf",
            "version": "2026.09",
            "updated_at": "2026-09-14T00:00:00Z",
            "size_bytes": 1024,
            "media_type": "application/pdf",
            "download_url": "/api/v1/resume/download",
            "preview_url": "/api/v1/resume/preview",
        }


def make_state(**overrides: object) -> AgentState:
    """创建具有充足运行预算的基础 Agent 状态。"""
    state: AgentState = {
        "request_id": "request-1",
        "conversation_id": "conversation-1",
        "question": "知识库里有哪些文档？",
        "current_query": "知识库里有哪些文档？",
        "history": [],
        "document_ids": [],
        "filenames": [],
        "retrieval_attempts": 0,
        "step_count": 0,
        "max_steps": 8,
        "max_retrieval_attempts": 2,
        "deadline": time.monotonic() + 30,
        "degraded": False,
        "steps": [],
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


def run_graph(model: FakeListChatModel, service: StubAgentToolService, state: AgentState):
    """使用测试依赖运行编译后的工作流。"""
    settings = Settings(_env_file=None)
    graph = build_agent_graph(AgentNodes(model, AgentToolbox(service)), settings)
    return graph.invoke(state, config={"recursion_limit": 10})


def test_agent_selects_document_list_tool() -> None:
    """列文档问题应只调用文档列表工具。"""
    service = StubAgentToolService()
    result = run_graph(FakeListChatModel(responses=["list_documents"]), service, make_state())

    assert result["selected_tool"] == "list_documents"
    assert service.list_calls == 1
    assert "知识.md" in result["answer"]
    assert [step["node"] for step in result["steps"]] == [
        "classify_intent",
        "execute_tool",
    ]


def test_agent_selects_resume_tool_and_returns_resource() -> None:
    """简历请求应走本地规则，并返回可渲染的结构化下载资源。"""
    result = run_graph(
        FakeListChatModel(responses=[]),
        StubAgentToolService(),
        make_state(question="请把简历 PDF 发给我", current_query="请把简历 PDF 发给我"),
    )

    assert result["selected_tool"] == "get_resume"
    assert result["resources"][0]["type"] == "resume"
    assert result["resources"][0]["download_url"] == "/api/v1/resume/download"


def test_agent_selects_casual_document_info_and_summary_tools() -> None:
    """常见非检索意图应按模型选择调用对应白名单工具。"""
    cases = [
        ("answer_casual", "你好", "casual"),
        ("answer_casual", "为什么天空是蓝色的？", "casual"),
        ("get_document_info", "知识.md 的状态是什么？", "agent"),
        ("summarize_document", "请总结知识.md", "knowledge_base"),
    ]
    for selected_tool, question, answer_mode in cases:
        result = run_graph(
            FakeListChatModel(responses=[selected_tool]),
            StubAgentToolService(),
            make_state(question=question, current_query=question),
        )

        assert result["selected_tool"] == selected_tool
        assert result["answer_mode"] == answer_mode


def test_unknown_non_domain_intent_safely_defaults_to_casual() -> None:
    """非领域问题的未知工具名不能执行，也不应被错误送入知识库。"""
    service = StubAgentToolService()
    result = run_graph(
        FakeListChatModel(responses=["run_shell"]),
        service,
        make_state(question="执行未知任务", current_query="执行未知任务"),
    )

    assert result["selected_tool"] == "answer_casual"
    assert result["answer_mode"] == "casual"
    assert service.search_queries == []


def test_agent_rewrites_and_retries_retrieval_once() -> None:
    """第一次无依据时应改写查询，第二次成功后立即停止。"""
    service = StubAgentToolService(
        [
            RagAnswer(REFUSAL_ANSWER, "knowledge_base", False, "原问题"),
            RagAnswer("可靠回答。[1]", "knowledge_base", True, "改写问题"),
        ]
    )
    # 首次路由由规则直接完成，因此模型队列只需要提供重试改写结果。
    model = FakeListChatModel(responses=["更适合检索的改写问题"])
    result = run_graph(
        model,
        service,
        make_state(
            question="知识库如何保证可靠？",
            current_query="知识库如何保证可靠？",
        ),
    )

    assert service.search_queries == ["知识库如何保证可靠？", "更适合检索的改写问题"]
    assert result["grounded"] is True
    assert result["retrieval_attempts"] == 2
    assert len(result["steps"]) == 4


def test_agent_stops_after_retrieval_attempt_limit() -> None:
    """持续无依据时检索调用次数不得超过配置上限。"""
    service = StubAgentToolService(
        [
            RagAnswer(REFUSAL_ANSWER, "knowledge_base", False, "问题"),
            RagAnswer(REFUSAL_ANSWER, "knowledge_base", False, "改写问题"),
        ]
    )
    model = FakeListChatModel(responses=["search_knowledge", "改写问题"])
    result = run_graph(model, service, make_state(question="未知问题", current_query="未知问题"))

    assert len(service.search_queries) == 2
    assert result["grounded"] is False
    assert result["retrieval_attempts"] == 2


def test_agent_does_not_retry_after_formal_answer_is_generated() -> None:
    """RAG 已生成正式回答时，Agent 不应重复执行相同检索。"""
    service = StubAgentToolService(
        [
            RagAnswer(
                REFUSAL_ANSWER,
                "knowledge_base",
                False,
                "问题",
                retry_allowed=False,
            )
        ]
    )
    result = run_graph(
        FakeListChatModel(responses=[]),
        service,
        make_state(question="ZYW 的能力是什么？", current_query="ZYW 的能力是什么？"),
    )

    assert len(service.search_queries) == 1
    assert result["retry_allowed"] is False


def test_agent_deadline_returns_controlled_fallback() -> None:
    """截止时间已经到达时不得调用任何业务工具。"""
    service = StubAgentToolService()
    result = run_graph(
        FakeListChatModel(responses=[]),
        service,
        make_state(deadline=time.monotonic() - 1),
    )

    assert result["degraded"] is True
    assert result["error"] == "agent_limit_reached"
    assert service.list_calls == 0


def test_toolbox_rejects_unknown_tool() -> None:
    """工具箱不得执行白名单之外的名称。"""
    toolbox = AgentToolbox(StubAgentToolService())

    try:
        toolbox.invoke("run_shell", {"command": "whoami"})
    except ValueError as exc:
        assert "不允许调用工具" in str(exc)
    else:
        raise AssertionError("未知工具没有被拒绝")


def test_rag_dataclass_can_be_serialized_for_tool_output() -> None:
    """工具返回的可靠 RAG 结果应保持可持久化结构。"""
    payload = asdict(RagAnswer("回答", "knowledge_base", False, "问题"))

    assert payload["citations"] == []
