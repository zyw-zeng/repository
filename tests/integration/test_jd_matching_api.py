"""验证 JD 岗位匹配报告查询接口和 OpenAPI 契约。"""

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.main import app
from app.storage.database import get_db_session
from app.storage.models import JdAnalysis


def test_get_persisted_jd_analysis(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """已完成报告应能在刷新后通过 ID 恢复。"""
    with session_factory() as session:
        analysis = JdAnalysis(
            request_id="jd-test-request",
            status="completed",
            jd_text="岗位描述" * 20,
            company_name="示例公司",
            job_title="AI Agent 工程师",
            requirements_json=[],
            matches_json=[],
            score=80.0,
            completeness=75.0,
            feasibility=72.0,
            duration_ms=1200,
        )
        session.add(analysis)
        session.commit()
        analysis_id = analysis.id

    def override_session() -> Generator[Session, None, None]:
        """向接口提供隔离数据库会话。"""
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/jd-analyses/{analysis_id}")
            openapi = client.get("/openapi.json")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["job_title"] == "AI Agent 工程师"
    assert response.json()["score"] == 80.0
    assert response.json()["feasibility"] == 72.0
    assert "/api/v1/jd-analyses/stream" in openapi.json()["paths"]
    assert "/api/v1/jd-analyses/runs/{request_id}/cancel" in openapi.json()["paths"]
