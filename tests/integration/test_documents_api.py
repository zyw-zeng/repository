"""文档管理 HTTP 接口的集成测试。"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

import app.api.routes.documents as document_routes
import app.services.document_service as document_service_module
from app.core.config import Settings, get_settings
from app.main import app
from app.storage.database import get_db_session


def test_upload_list_detail_and_duplicate(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    admin_headers: dict[str, str],
) -> None:
    """上传接口应返回任务，列表和详情可查询，重复文件返回 409。"""

    def override_session() -> Generator[Session, None, None]:
        """让接口使用测试数据库，而不是项目运行数据库。"""
        with session_factory() as session:
            yield session

    # HTTP 测试只验证任务创建，完整 Worker 行为由 ingestion_flow 测试覆盖。
    monkeypatch.setattr(document_service_module, "get_settings", lambda: test_settings)
    monkeypatch.setattr(document_routes, "run_job_with_retries", lambda _: None)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        with TestClient(app) as client:
            upload = client.post(
                "/api/v1/documents",
                headers=admin_headers,
                files={"file": ("notes.txt", "中文 English 文档", "text/plain")},
            )
            assert upload.status_code == 202
            payload = upload.json()
            document_id = payload["document"]["id"]
            assert payload["job"]["status"] == "pending"
            assert payload["document"]["visibility"] == "private"

            visible = client.patch(
                f"/api/v1/documents/{document_id}/visibility",
                headers=admin_headers,
                json={"visibility": "public"},
            )
            assert visible.status_code == 200
            assert visible.json()["visibility"] == "public"

            listing = client.get("/api/v1/documents", headers=admin_headers)
            assert listing.status_code == 200
            assert listing.json()["items"][0]["id"] == document_id

            detail = client.get(f"/api/v1/documents/{document_id}", headers=admin_headers)
            assert detail.status_code == 200
            assert detail.json()["filename"] == "notes.txt"

            duplicate = client.post(
                "/api/v1/documents",
                headers=admin_headers,
                files={"file": ("copy.txt", "中文 English 文档", "text/plain")},
            )
            assert duplicate.status_code == 409
            assert duplicate.json()["error"]["code"] == "duplicate_document"
    finally:
        app.dependency_overrides.clear()


def test_upload_rejects_empty_and_unsupported_files(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    admin_headers: dict[str, str],
) -> None:
    """上传入口应在落盘前拒绝空文件和非白名单格式。"""

    def override_session() -> Generator[Session, None, None]:
        """为一次请求提供隔离数据库会话。"""
        with session_factory() as session:
            yield session

    monkeypatch.setattr(document_service_module, "get_settings", lambda: test_settings)
    monkeypatch.setattr(document_routes, "run_job_with_retries", lambda _: None)
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        with TestClient(app) as client:
            empty = client.post(
                "/api/v1/documents",
                headers=admin_headers,
                files={"file": ("empty.txt", b"", "text/plain")},
            )
            unsupported = client.post(
                "/api/v1/documents",
                headers=admin_headers,
                files={"file": ("script.exe", b"binary", "application/octet-stream")},
            )

        assert empty.status_code == 400
        assert empty.json()["error"]["code"] == "empty_file"
        assert unsupported.status_code == 400
        assert unsupported.json()["error"]["code"] == "unsupported_file"
    finally:
        app.dependency_overrides.clear()
