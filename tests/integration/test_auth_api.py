"""管理端认证和权限边界的集成测试。"""

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def test_admin_login_and_me(test_settings: Settings) -> None:
    """正确密码应签发令牌，错误密码和匿名访问应被拒绝。"""
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        with TestClient(app) as client:
            anonymous = client.get("/api/v1/auth/me")
            invalid = client.post("/api/v1/auth/login", json={"password": "wrong"})
            login = client.post(
                "/api/v1/auth/login",
                json={"password": test_settings.admin_password},
            )
            authenticated = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {login.json()['access_token']}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert anonymous.status_code == 401
    assert invalid.status_code == 401
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert authenticated.status_code == 200
    assert authenticated.json() == {"role": "admin"}


def test_document_management_requires_admin() -> None:
    """文档管理接口不能因前端隐藏按钮而允许匿名调用。"""
    with TestClient(app) as client:
        response = client.get("/api/v1/documents")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "admin_auth_required"
