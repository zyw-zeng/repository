"""验证 CosyVoice 接口校验、取消语义和 Swagger 声明。"""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.storage.database import get_db_session


def test_tts_returns_clear_error_without_api_key(test_settings, session_factory) -> None:
    """未配置 DashScope 时不能先返回 200 再在音频流中失败。"""
    def override_session():
        """为接口提供带新音色表的隔离数据库会话。"""
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db_session] = override_session
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tts/stream",
                headers={"X-Request-ID": "tts-request-1"},
                json={"text": "请朗读这段回答。", "speech_rate": 1},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "tts_not_configured"


def test_tts_cancel_is_idempotent() -> None:
    """任务已结束或不存在时，停止操作仍应安全成功。"""
    with TestClient(app) as client:
        response = client.post("/api/v1/tts/runs/not-active/cancel")

    assert response.status_code == 202
    assert response.json()["status"] == "cancellation_requested"


def test_admin_can_update_character_voice(
    test_settings,
    session_factory,
    admin_headers,
) -> None:
    """管理员保存后，公开端应立即读取到角色的新音色和自动朗读策略。"""
    def override_session():
        """为读写请求复用同一个隔离数据库。"""
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db_session] = override_session
    try:
        with TestClient(app) as client:
            denied = client.put(
                "/api/v1/tts/profiles/nova",
                json={
                    "model": "cosyvoice-v3-flash",
                    "voice": "longxiaochun_v3",
                    "enabled": True,
                    "auto_speak": True,
                },
            )
            updated = client.put(
                "/api/v1/tts/profiles/nova",
                headers=admin_headers,
                json={
                    "model": "cosyvoice-v3-flash",
                    "voice": "longxiaochun_v3",
                    "enabled": True,
                    "auto_speak": True,
                },
            )
            public = client.get("/api/v1/tts/profiles/nova")
    finally:
        app.dependency_overrides.clear()

    assert denied.status_code == 401
    assert updated.status_code == 200
    assert updated.json()["voice"] == "longxiaochun_v3"
    assert public.json()["auto_speak"] is True


def test_openapi_contains_tts_stream() -> None:
    """Swagger 应公开朗读和取消接口。"""
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert "/api/v1/tts/stream" in schema["paths"]
    assert schema["paths"]["/api/v1/tts/stream"]["post"]["summary"] == (
        "流式合成回答语音"
    )
