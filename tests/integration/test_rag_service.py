"""可靠 RAG 服务的权威引用和拒答集成测试。"""

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.knowledge.rag import REFUSAL_ANSWER
from app.knowledge.types import SearchFilters, SearchResult
from app.services.chat_service import ChatService
from app.storage.models import DocumentChunk, DocumentRecord


class StubRetriever:
    """返回固定结果并记录是否执行过检索。"""

    def __init__(self, results: list[SearchResult]):
        """保存固定检索结果。"""
        self.results = results
        self.calls = 0
        self.last_query = ""
        self.last_options: dict[str, object] = {}

    def search(self, query: str, **options: object) -> list[SearchResult]:
        """记录检索调用并返回结果。"""
        assert query
        self.calls += 1
        self.last_query = query
        self.last_options = options
        return self.results


def seed_authoritative_chunk(session: Session) -> None:
    """创建处于活动版本的权威切片。"""
    document = DocumentRecord(
        id="doc-1",
        filename="设计.md",
        file_hash="c" * 64,
        file_type="md",
        storage_path="design.md",
        status="ready",
        visibility="public",
        active_index_version=2,
        chunk_count=1,
    )
    session.add(document)
    session.flush()
    session.add(
        DocumentChunk(
            id="chunk-authority",
            document_id=document.id,
            index_version=2,
            chunk_index=0,
            content="SQLite 保存权威切片正文。",
            content_hash="d" * 64,
            token_count=18,
            vector_id="chunk-authority",
        )
    )
    session.commit()


def make_candidate() -> SearchResult:
    """创建与权威记录同 ID 的候选，正文故意使用非权威副本。"""
    return SearchResult(
        chunk_id="chunk-authority",
        document_id="doc-1",
        filename="设计.md",
        content="这个候选正文不应作为最终引用返回。",
        score=0.95,
        page_number=None,
        heading=None,
        index_version=2,
    )


def test_service_returns_only_authoritative_active_citation(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """模型引用存在时，响应引用正文仍应从 SQLite 活动版本重读。"""
    with session_factory() as session:
        seed_authoritative_chunk(session)
        retriever = StubRetriever([make_candidate()])
        service = ChatService(
            session,
            test_settings,
            model=FakeListChatModel(responses=["权威正文保存在 SQLite。[1]"]),
            retriever=retriever,
        )

        result = service.ask("权威正文保存在哪里？", filters=SearchFilters())

    assert retriever.calls == 1
    assert result.grounded is True
    assert result.citations[0].quote == "SQLite 保存权威切片正文。"
    assert result.citations[0].index_version == 2


def test_service_refuses_when_retrieval_is_empty(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """知识库没有候选时不能让模型凭常识强行作答。"""
    with session_factory() as session:
        retriever = StubRetriever([])
        service = ChatService(
            session,
            test_settings,
            model=FakeListChatModel(responses=[]),
            retriever=retriever,
        )
        result = service.ask("作者生日是哪一天？")

    assert retriever.calls == 1
    assert result.answer == REFUSAL_ANSWER
    assert result.grounded is False
    assert result.citations == []


def test_service_filters_fabricated_reference_number(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """模型引用不存在的编号时保留回答，但不得展示伪造来源。"""
    with session_factory() as session:
        seed_authoritative_chunk(session)
        service = ChatService(
            session,
            test_settings,
            model=FakeListChatModel(responses=["一个未经支持的结论。[7]"]),
            retriever=StubRetriever([make_candidate()]),
        )
        result = service.ask("结论是什么？")

    assert result.answer == "一个未经支持的结论。[7]"
    assert result.grounded is False
    assert result.citations == []
    assert result.retry_allowed is False


def test_service_does_not_call_a_second_verifier_model(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """回答生成完成后应直接返回，不再等待额外核验模型。"""
    with session_factory() as session:
        seed_authoritative_chunk(session)
        service = ChatService(
            session,
            test_settings,
            model=FakeListChatModel(responses=["作者生日是明天。[1]"]),
            retriever=StubRetriever([make_candidate()]),
        )
        result = service.ask("作者生日是哪天？")

    assert result.answer == "作者生日是明天。[1]"
    assert result.grounded is True
    assert result.retry_allowed is False


def test_casual_mode_does_not_query_knowledge_base(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """只有明确的闲聊模式可以跳过检索，且不得标记为有依据。"""
    with session_factory() as session:
        retriever = StubRetriever([])
        service = ChatService(
            session,
            test_settings,
            model=FakeListChatModel(responses=["你好！有什么可以帮你？"]),
            retriever=retriever,
        )
        result = service.ask("你好", mode="casual")

    assert retriever.calls == 0
    assert result.answer_mode == "casual"
    assert result.grounded is False
    assert result.citations == []


def test_profile_introduction_uses_broader_retrieval_query(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """宽泛个人介绍应一次覆盖概述、经历、能力和代表项目。"""
    with session_factory() as session:
        seed_authoritative_chunk(session)
        retriever = StubRetriever([make_candidate()])
        service = ChatService(
            session,
            test_settings,
            model=FakeListChatModel(responses=["这是一段自然的个人介绍。[1]"]),
            retriever=retriever,
        )

        result = service.ask("介绍一下 ZYW")

    assert "个人概述" in retriever.last_query
    assert "代表项目" in retriever.last_query
    assert retriever.last_options["limit"] >= 8
    assert result.answer == "这是一段自然的个人介绍。[1]"
