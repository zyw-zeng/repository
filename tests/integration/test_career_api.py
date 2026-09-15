"""验证求职材料预览和带引用报告下载接口。"""

import json
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.main import app
from app.storage.database import get_db_session
from app.storage.models import Conversation, JdAnalysis


def test_preview_and_download_grounded_career_materials(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """材料接口应返回四类内容，下载报告应保留引用编号。"""
    profile_path = tmp_path / "candidate_profile.json"
    profile_path.write_text(
        json.dumps({"version": 5, "facts": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    test_settings.candidate_profile_path = profile_path
    with session_factory() as session:
        analysis = JdAnalysis(
            request_id="career-material-api-analysis",
            status="completed",
            jd_text="AI Agent 岗位描述" * 10,
            company_name="示例科技",
            job_title="AI Agent 工程师",
            score=82,
            completeness=88,
            verified_fit=90,
            feasibility=79,
            matches_json=[
                {
                    "requirement_id": "req-1",
                    "requirement": "具备 LangGraph 项目经验",
                    "category": "必备项",
                    "requirement_type": "project_experience",
                    "importance": "required",
                    "weight": 10,
                    "level": "strong_match",
                    "reason": "已有可核验的 AI Agent 项目。",
                    "awarded_score": 10,
                    "max_score": 10,
                    "evidence": [
                        {
                            "chunk_id": "profile:agent-project",
                            "document_id": "candidate-profile",
                            "filename": "结构化个人档案",
                            "quote": "完成了 LangGraph 求职顾问 Agent。",
                            "page_number": None,
                            "heading": "本人确认的项目",
                            "index_version": 5,
                        }
                    ],
                }
            ],
        )
        session.add(analysis)
        session.flush()
        conversation = Conversation(
            title="求职材料测试",
            active_jd_analysis_id=analysis.id,
            candidate_profile_version=5,
        )
        session.add(conversation)
        session.commit()
        conversation_id = conversation.id

    def override_session() -> Generator[Session, None, None]:
        """向接口提供共享的隔离数据库。"""
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        with TestClient(app) as client:
            preview = client.get(
                f"/api/v1/career/conversations/{conversation_id}/materials"
            )
            download = client.get(
                f"/api/v1/career/conversations/{conversation_id}/report"
            )
    finally:
        app.dependency_overrides.clear()

    assert preview.status_code == 200
    assert len(preview.json()["sections"]) == 4
    assert preview.json()["sections"][0]["evidence"][0]["reference_number"] == 1
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("text/markdown")
    assert "attachment;" in download.headers["content-disposition"]
    assert "## 引用资料" in download.content.decode("utf-8")
