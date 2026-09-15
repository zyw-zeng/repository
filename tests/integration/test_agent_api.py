"""Agent 会话 HTTP 接口的集成测试。"""

import time
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy.orm import Session, sessionmaker

import app.api.routes.agent as agent_routes
from app.core.config import Settings, get_settings
from app.main import app
from app.services.agent_service import AgentService
from app.storage.database import get_db_session
from app.storage.models import Conversation, JdAnalysis
from tests.unit.test_agent_graph import StubAgentToolService


def test_empty_suggestions_have_safe_fallback(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """小模型未配置时，首页推荐接口仍应返回三个可用问题。"""

    def override_session() -> Generator[Session, None, None]:
        """为推荐接口提供隔离数据库。"""
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/suggestions")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
    assert len(response.json()["suggestions"]) == 3


def test_create_send_and_read_agent_conversation(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    admin_headers: dict[str, str],
) -> None:
    """完整 HTTP 流程应保存会话消息并返回工具执行步骤。"""

    class TestAgentService(AgentService):
        """为 API 测试注入确定性分类模型和工具。"""

        def __init__(self, session: Session, _settings: Settings | None = None):
            """使用测试配置初始化 Agent 服务。"""
            super().__init__(
                session,
                test_settings,
                model=FakeListChatModel(responses=["list_documents"]),
                tool_service=StubAgentToolService(),
            )

    def override_session() -> Generator[Session, None, None]:
        """让三个接口共享同一个测试数据库。"""
        with session_factory() as session:
            yield session

    monkeypatch.setattr(agent_routes, "AgentService", TestAgentService)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/conversations", json={"title": "Agent 测试"})
            conversation_id = created.json()["id"]
            executed = client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                headers={"X-Request-ID": "agent-api-request-1"},
                json={"question": "知识库里有哪些文档？"},
            )
            loaded = client.get(f"/api/v1/conversations/{conversation_id}")
            streaming = client.post(
                f"/api/v1/conversations/{conversation_id}/messages/stream",
                headers={"X-Request-ID": "agent-api-request-2"},
                json={"question": "再次列出文档"},
            )
            listing = client.get("/api/v1/conversations", headers=admin_headers)
            deleted = client.delete(
                f"/api/v1/conversations/{conversation_id}",
                headers=admin_headers,
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert executed.status_code == 200
    assert executed.json()["degraded"] is False
    assert executed.json()["timings"]["total_ms"] >= 0
    assert executed.json()["steps"][1]["tool"] == "list_documents"
    assert loaded.status_code == 200
    assert [message["role"] for message in loaded.json()["messages"]] == [
        "user",
        "assistant",
    ]
    assert streaming.status_code == 200
    assert streaming.headers["content-type"].startswith("text/event-stream")
    assert "event: run_started" in streaming.text
    assert "event: agent_step" in streaming.text
    assert "event: timing" in streaming.text
    assert "event: answer_final" in streaming.text
    assert "event: citations" in streaming.text
    assert "event: followup_suggestions" in streaming.text
    assert "event: completed" in streaming.text
    assert '"timings":{' in streaming.text
    assert streaming.text.index("event: agent_step") < streaming.text.index("event: answer_final")
    assert streaming.text.index("event: answer_final") < streaming.text.index(
        "event: followup_suggestions"
    )
    assert listing.status_code == 200
    assert listing.json()["items"][0]["id"] == conversation_id
    assert deleted.status_code == 204


def test_agent_stream_sends_heartbeat_during_slow_run(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """长时间 Agent 调用应持续发送心跳，避免代理按空闲超时断开。"""

    class SlowAgentService(AgentService):
        """使用短暂等待模拟真实模型的长耗时调用。"""

        def __init__(self, session: Session, _settings: Settings | None = None):
            """注入确定性模型和工具服务。"""
            super().__init__(
                session,
                test_settings,
                model=FakeListChatModel(responses=["list_documents"]),
                tool_service=StubAgentToolService(),
            )

        def run(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            """等待超过测试心跳周期后执行正常 Agent。"""
            time.sleep(0.03)
            return super().run(*args, **kwargs)

    def override_session() -> Generator[Session, None, None]:
        """为流式接口提供测试数据库会话。"""
        with session_factory() as session:
            yield session

    monkeypatch.setattr(agent_routes, "AgentService", SlowAgentService)
    monkeypatch.setattr(agent_routes, "SSE_HEARTBEAT_INTERVAL_SECONDS", 0.005)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/conversations", json={"title": "心跳测试"})
            response = client.post(
                f"/api/v1/conversations/{created.json()['id']}/messages/stream",
                headers={"X-Request-ID": "agent-heartbeat-request"},
                json={"question": "列出文档"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "event: heartbeat" in response.text
    assert "event: completed" in response.text


def test_agent_stream_converts_unexpected_exception_to_error_event(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """响应头发出后的异常应通过 SSE error 结束，不能直接截断连接。"""

    class BrokenAgentService(AgentService):
        """模拟无法被业务层捕获的流式执行异常。"""

        def run(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            """抛出确定性异常供路由边界处理。"""
            raise RuntimeError("测试异常")

    def override_session() -> Generator[Session, None, None]:
        """为流式接口提供测试数据库会话。"""
        with session_factory() as session:
            yield session

    monkeypatch.setattr(agent_routes, "AgentService", BrokenAgentService)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/conversations", json={"title": "异常测试"})
            response = client.post(
                f"/api/v1/conversations/{created.json()['id']}/messages/stream",
                headers={"X-Request-ID": "agent-error-event-request"},
                json={"question": "触发异常"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "agent_stream_failed" in response.text


def test_cancel_endpoint_sets_matching_active_run(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """取消接口只能停止属于指定会话且仍在活动中的运行。"""

    def override_session() -> Generator[Session, None, None]:
        """让会话创建和取消请求共享测试数据库。"""
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    cancellation = None
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/conversations", json={"title": "取消接口测试"})
            conversation_id = created.json()["id"]
            cancellation = agent_routes._register_active_run(
                conversation_id,
                "cancel-api-request",
            )
            response = client.post(
                f"/api/v1/conversations/{conversation_id}/runs/cancel-api-request/cancel"
            )
    finally:
        if cancellation is not None:
            agent_routes._release_active_run("cancel-api-request", cancellation)
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert cancellation is not None and cancellation.is_set()


def test_career_followup_stream_uses_bound_jd_context(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """绑定岗位后的追问应通过现有 SSE 输出 Career Agent 全部关键事件。"""
    profile_path = tmp_path / "candidate_profile.json"
    profile_path.write_text('{"version": 4, "facts": []}', encoding="utf-8")
    test_settings.candidate_profile_path = profile_path
    with session_factory() as session:
        analysis = JdAnalysis(
            request_id="career-stream-analysis",
            status="completed",
            jd_text="岗位描述" * 20,
            job_title="前端 Agent 工程师",
            score=62,
            completeness=70,
            verified_fit=80,
            feasibility=58,
            matches_json=[],
        )
        session.add(analysis)
        session.flush()
        conversation = Conversation(
            title="岗位咨询",
            active_jd_analysis_id=analysis.id,
            candidate_profile_version=4,
        )
        session.add(conversation)
        session.commit()
        conversation_id = conversation.id

    def override_session() -> Generator[Session, None, None]:
        """让 SSE 工作线程读取同一个隔离测试数据库。"""
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/conversations/{conversation_id}/messages/stream",
                headers={"X-Request-ID": "career-stream-request"},
                json={"question": "我应该采用什么投递策略？"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "event: career_context" in response.text
    assert "event: career_tool_result" in response.text
    assert "event: answer_delta" in response.text
    assert "event: answer_final" in response.text
    assert '"answer_mode":"career_advisor"' in response.text
    assert "event: completed" in response.text
