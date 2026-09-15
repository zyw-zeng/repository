"""Swagger 和 OpenAPI 配置的集成测试。"""

from fastapi.testclient import TestClient

from app.main import app


def test_root_redirects_to_swagger() -> None:
    """根地址应引导使用者进入唯一维护的 Swagger 文档。"""
    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_swagger_enabled_and_redoc_disabled() -> None:
    """项目应只启用 Swagger，不额外暴露 ReDoc。"""
    with TestClient(app) as client:
        swagger_response = client.get("/docs")
        redoc_response = client.get("/redoc")

    assert swagger_response.status_code == 200
    assert "swagger-ui" in swagger_response.text.lower()
    assert redoc_response.status_code == 404


def test_openapi_contains_chinese_groups_and_operation_details() -> None:
    """OpenAPI 应包含中文分组、操作说明和统一错误模型。"""
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert schema["info"]["description"].strip().startswith("ZYW 的 AI 小助理后端 API")
    assert {tag["name"] for tag in schema["tags"]} >= {
        "系统",
        "认证",
        "文档管理",
        "文档任务",
    }

    upload_operation = schema["paths"]["/api/v1/documents"]["post"]
    assert upload_operation["summary"] == "上传文档并创建索引任务"
    assert upload_operation["responses"]["409"]["description"] == "相同内容的文档已经存在。"
    assert "ErrorResponse" in schema["components"]["schemas"]
