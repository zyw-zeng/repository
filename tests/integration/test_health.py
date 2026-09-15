"""系统健康检查接口的集成测试。"""

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    """存活检查应返回服务信息和可追踪的请求 ID。"""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert float(response.headers["X-Dispatch-Time-Ms"]) >= 0
    assert response.headers["Server-Timing"].startswith("dispatch;dur=")
    assert response.json() == {
        "status": "ok",
        "service": "ZYW 的 AI 小助理",
        "version": "0.6.3",
    }


def test_readiness() -> None:
    """数据库可连接时，就绪检查应返回 ready。"""
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "document_store": "ok",
        "vector_store": "ok",
    }


def test_document_routes_are_registered() -> None:
    """阶段 2 的文档、重建、删除和任务查询接口应出现在 OpenAPI 中。"""
    with TestClient(app) as client:
        paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/documents" in paths
    assert "/api/v1/documents/{document_id}" in paths
    assert "/api/v1/documents/{document_id}/reindex" in paths
    assert "/api/v1/documents/{document_id}/visibility" in paths
    assert "/api/v1/ingestion-jobs/{job_id}" in paths
    assert "/api/v1/ingestion-jobs" in paths
    assert "/api/v1/chat/query" in paths
    assert "/api/v1/conversations" in paths
    assert "/api/v1/conversations/{conversation_id}/messages" in paths
    assert "/api/v1/conversations/{conversation_id}/messages/stream" in paths
    assert "/api/v1/suggestions" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/resume" in paths
    assert "/api/v1/resume/download" in paths
    assert "/api/v1/resume/preview" in paths
