"""验证公开简历信息、预览和下载接口。"""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_resume_info_preview_and_download(test_settings, tmp_path) -> None:
    """三个公开接口应指向同一个固定 PDF，并使用正确处置方式。"""
    resume_path = tmp_path / "曾有为-AI-Agent应用开发.pdf"
    resume_content = b"%PDF-1.7\n% resume test\n"
    resume_path.write_bytes(resume_content)
    settings = test_settings.model_copy(
        update={
            "resume_file_path": resume_path,
            "resume_title": "曾有为｜AI Agent 应用开发",
            "resume_version": "2026.09",
        }
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            info = client.get("/api/v1/resume")
            download = client.get("/api/v1/resume/download")
            preview = client.get("/api/v1/resume/preview")
    finally:
        app.dependency_overrides.clear()

    assert info.status_code == 200
    assert info.json()["type"] == "resume"
    assert info.json()["download_url"] == "/api/v1/resume/download"
    assert info.json()["size_bytes"] == len(resume_content)
    assert download.content == resume_content
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.headers["etag"].startswith('"resume-')
    assert preview.headers["content-disposition"].startswith("inline;")


def test_resume_missing_returns_stable_error(test_settings, tmp_path) -> None:
    """配置文件不存在时应返回可读 404，而不是泄露真实路径。"""
    settings = test_settings.model_copy(
        update={"resume_file_path": tmp_path / "missing.pdf"}
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/resume")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resume_not_found"
    assert str(tmp_path) not in response.text


def test_admin_can_replace_resume_atomically(
    test_settings,
    admin_headers,
    tmp_path,
) -> None:
    """只有管理员能发布新 PDF，标题和版本应立即反映到公开接口。"""
    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"%PDF-1.7\nold\n")
    settings = test_settings.model_copy(update={"resume_file_path": resume_path})
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            denied = client.put(
                "/api/v1/resume",
                files={"file": ("new.pdf", b"%PDF-1.7\nnew\n", "application/pdf")},
                data={"title": "新版简历", "version": "2026.10"},
            )
            updated = client.put(
                "/api/v1/resume",
                headers=admin_headers,
                files={"file": ("new.pdf", b"%PDF-1.7\nnew\n", "application/pdf")},
                data={"title": "新版简历", "version": "2026.10"},
            )
            public = client.get("/api/v1/resume")
    finally:
        app.dependency_overrides.clear()

    assert denied.status_code == 401
    assert updated.status_code == 200
    assert public.json()["title"] == "新版简历"
    assert public.json()["version"] == "2026.10"
    assert resume_path.read_bytes() == b"%PDF-1.7\nnew\n"


def test_invalid_resume_does_not_replace_current_file(
    test_settings,
    admin_headers,
    tmp_path,
) -> None:
    """伪造 PDF 被拒绝时必须保留当前线上文件。"""
    resume_path = tmp_path / "resume.pdf"
    original = b"%PDF-1.7\noriginal\n"
    resume_path.write_bytes(original)
    settings = test_settings.model_copy(update={"resume_file_path": resume_path})
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.put(
                "/api/v1/resume",
                headers=admin_headers,
                files={"file": ("fake.pdf", b"not-a-pdf", "application/pdf")},
                data={"title": "错误文件", "version": "bad"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "resume_invalid_pdf"
    assert resume_path.read_bytes() == original
