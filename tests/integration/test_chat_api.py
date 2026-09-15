"""可靠 RAG HTTP 接口和请求校验的集成测试。"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

import app.api.routes.chat as chat_routes
from app.knowledge.types import CitationRecord, RagAnswer
from app.main import app
from app.storage.database import get_db_session


class StubChatService:
    """避免 HTTP 契约测试访问真实模型和向量库。"""

    def __init__(self, _: Session):
        """接收路由传入的数据库会话。"""

    def ask(self, question: str, **_: object) -> RagAnswer:
        """返回带权威引用结构的固定回答。"""
        return RagAnswer(
            answer="SQLite 保存权威切片。[1]",
            answer_mode="knowledge_base",
            grounded=True,
            rewritten_query=question,
            retrieved_count=1,
            citations=[
                CitationRecord(
                    reference_number=1,
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    filename="设计.md",
                    quote="SQLite 保存权威切片。",
                    page_number=None,
                    heading="数据设计",
                    index_version=1,
                )
            ],
        )


def test_chat_query_contract_and_request_id(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
) -> None:
    """问答接口应返回模式、依据、引用和可追踪请求 ID。"""

    def override_session() -> Generator[Session, None, None]:
        """为接口测试提供隔离数据库会话。"""
        with session_factory() as session:
            yield session

    monkeypatch.setattr(chat_routes, "ChatService", StubChatService)
    app.dependency_overrides[get_db_session] = override_session
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/query",
                headers={"X-Request-ID": "rag-request-1"},
                json={"question": "权威正文保存在哪里？"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["grounded"] is True
    assert payload["answer_mode"] == "knowledge_base"
    assert payload["request_id"] == "rag-request-1"
    assert payload["citations"][0]["quote"] == "SQLite 保存权威切片。"


def test_chat_query_rejects_blank_question() -> None:
    """空白问题应在进入模型前由请求模型拒绝。"""
    with TestClient(app) as client:
        response = client.post("/api/v1/chat/query", json={"question": "   "})

    assert response.status_code == 422
