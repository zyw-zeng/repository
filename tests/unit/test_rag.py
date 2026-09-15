"""查询改写、上下文组装和证据回答的独立单元测试。"""

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.agent.runtime import bind_agent_runtime
from app.knowledge.context import assemble_context
from app.knowledge.rag import (
    REFUSAL_ANSWER,
    GroundedAnswerGenerator,
    QueryRewriter,
    answer_system_prompt,
    is_profile_introduction_request,
)
from app.knowledge.types import SearchResult


def make_result(chunk_id: str, content: str, *, score: float = 0.9) -> SearchResult:
    """创建用于上下文测试的检索结果。"""
    return SearchResult(
        chunk_id=chunk_id,
        document_id="doc-1",
        filename="知识.md",
        content=content,
        score=score,
        page_number=2,
        heading="可靠 RAG",
        index_version=1,
    )


def test_query_rewriter_uses_history_for_follow_up() -> None:
    """存在聊天历史时应调用模型生成独立查询。"""
    model = FakeListChatModel(responses=["个人知识库支持增量更新吗？"])

    rewritten = QueryRewriter(model).rewrite(
        "它支持吗？",
        [("user", "个人知识库如何更新文档？"), ("assistant", "可以重新索引。")],
    )

    assert rewritten == "个人知识库支持增量更新吗？"


def test_query_rewriter_skips_model_without_history() -> None:
    """独立问题不需要额外消耗一次模型调用。"""
    model = FakeListChatModel(responses=[])

    assert QueryRewriter(model).rewrite("  什么是 RAG？  ", []) == "什么是 RAG？"


def test_query_rewriter_skips_model_for_independent_question_with_history() -> None:
    """新问题已经包含明确主体时，不应仅因存在会话历史而调用模型。"""
    model = FakeListChatModel(responses=[])

    rewritten = QueryRewriter(model).rewrite(
        "介绍一下 ZYW",
        [("user", "上一个问题"), ("assistant", "上一个回答")],
    )

    assert rewritten == "介绍一下 ZYW"


def test_profile_introduction_only_matches_broad_person_request() -> None:
    """个人介绍策略只处理宽泛介绍，不抢占具体项目和技术问题。"""
    assert is_profile_introduction_request("请介绍一下 ZYW") is True
    assert is_profile_introduction_request("曾有为是谁？") is True
    assert is_profile_introduction_request("介绍一下 ZYW 的知识库项目") is False
    assert is_profile_introduction_request("ZYW 会哪些技术？") is False


def test_profile_introduction_prompt_uses_narrative_structure() -> None:
    """个人介绍应强调访客可读性，同时继续执行证据与引用约束。"""
    prompt = answer_system_prompt(profile_introduction=True)

    assert "3 至 4 个短段落" in prompt
    assert "不要堆砌技术关键词" in prompt
    assert "每个事实陈述后必须标注" in prompt
    assert "不得使用外部知识或猜测" in prompt
    assert "‘参与’不能写成‘负责’或‘主导’" in prompt
    assert "不要使用‘擅长’‘扎实’‘资深’‘优秀’" in prompt


def test_context_keeps_complete_numbered_chunks() -> None:
    """上下文达到上限时应保留完整切片和连续引用编号。"""
    context, items = assemble_context(
        [make_result("chunk-1", "第一条证据"), make_result("chunk-2", "第二条证据")],
        max_chars=80,
    )

    assert len(items) == 1
    assert context.startswith("[1] 文件：知识.md；页码：2；章节：可靠 RAG")
    assert "第一条证据" in context
    assert "第二条证据" not in context


def test_grounded_answer_requires_valid_citations() -> None:
    """有依据的答案必须包含上下文中存在的引用编号。"""
    context, items = assemble_context([make_result("chunk-1", "引用来自权威正文。")], max_chars=500)
    valid = GroundedAnswerGenerator(FakeListChatModel(responses=["答案来自权威正文。[1]"]))
    answer, references = valid.generate("引用来自哪里？", context)

    assert answer == "答案来自权威正文。[1]"
    assert references == [1]

    invalid = GroundedAnswerGenerator(FakeListChatModel(responses=["这是伪造引用。[9]"]))
    _, invalid_references = invalid.generate("引用来自哪里？", context)
    assert invalid_references == [9]


def test_grounded_answer_refuses_uncited_or_unsupported_output() -> None:
    """模型拒答或遗漏引用时，系统应统一转换为无依据回答。"""
    unsupported = GroundedAnswerGenerator(
        FakeListChatModel(responses=["INSUFFICIENT_EVIDENCE"])
    )
    uncited = GroundedAnswerGenerator(FakeListChatModel(responses=["看起来应该是这样。"]))

    assert unsupported.generate("未知问题", "证据")[0] == REFUSAL_ANSWER
    assert uncited.generate("未知问题", "证据")[0] == REFUSAL_ANSWER


def test_grounded_answer_emits_model_stream_as_draft() -> None:
    """回答生成时应直接转发正式模型流，并保留片段中的空格。"""
    events: list[tuple[str, object]] = []
    generator = GroundedAnswerGenerator(
        FakeListChatModel(responses=["这是 实时草稿。[1]"])
    )

    with bind_agent_runtime(lambda event, data: events.append((event, data)), lambda: False):
        answer, references = generator.generate("如何流式回答？", "[1] 权威证据")

    streamed = "".join(
        payload["delta"]
        for event, payload in events
        if event == "answer_delta" and isinstance(payload, dict)
    )
    assert streamed == answer
    assert references == [1]
    assert events[0][0] == "answer_delta"
