"""验证 Career Agent 的会话上下文、工具白名单和有界工作流。"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.career_agent.router import select_career_tools
from app.career_agent.tools import CareerToolbox
from app.core.config import Settings
from app.services.agent_service import AgentService
from app.services.career_advice_service import CareerAdviceService
from app.storage.models import AgentRun, Conversation, JdAnalysis, Message


def _prepare_context(
    session: Session,
    settings: Settings,
    profile_path: Path,
    *,
    bound_version: int = 3,
    current_version: int = 3,
) -> Conversation:
    """创建带强匹配、部分匹配和明确缺口的岗位上下文。"""
    profile_path.write_text(
        json.dumps({"version": current_version, "facts": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    settings.candidate_profile_path = profile_path
    analysis = JdAnalysis(
        request_id=f"career-analysis-{bound_version}-{current_version}",
        status="completed",
        jd_text="AI Agent 岗位描述" * 10,
        job_title="AI Agent 工程师",
        score=68,
        completeness=75,
        verified_fit=90,
        feasibility=64,
        matches_json=[
            {
                "requirement_id": "req-1",
                "requirement": "具备 LangGraph 项目经验",
                "category": "必备项",
                "requirement_type": "project_experience",
                "importance": "required",
                "weight": 10,
                "level": "strong_match",
                "reason": "已有完整 AI Agent 项目。",
                "awarded_score": 10,
                "max_score": 10,
                "evidence": [
                    {
                        "chunk_id": "profile:agent-rag",
                        "document_id": "candidate-profile",
                        "filename": "结构化个人档案",
                        "quote": "已完成 LangGraph 与 RAG 项目。",
                        "page_number": None,
                        "heading": "本人确认的结构化档案",
                        "index_version": bound_version,
                    }
                ],
            },
            {
                "requirement_id": "req-2",
                "requirement": "具备 Kubernetes 生产经验",
                "category": "必备项",
                "requirement_type": "technical_skill",
                "importance": "required",
                "weight": 8,
                "level": "unverified",
                "reason": "暂无资料。",
                "awarded_score": 0,
                "max_score": 8,
                "evidence": [],
            },
        ],
    )
    session.add(analysis)
    session.flush()
    conversation = Conversation(
        title="JD 匹配 · AI Agent 工程师",
        active_jd_analysis_id=analysis.id,
        candidate_profile_version=bound_version,
    )
    session.add(conversation)
    session.commit()
    return conversation


def test_career_router_selects_only_explicit_whitelist_tools() -> None:
    """一个问题可以选择多个顾问工具，非求职问题不应误进入 Career Agent。"""
    assert select_career_tools("分析一下我的优势、风险和能力缺口") == [
        "analyze_advantages",
        "analyze_risks",
        "analyze_gaps",
    ]
    assert select_career_tools("今天天气怎么样") == []
    assert select_career_tools("生成自我介绍和面试问题，再给我一份提升计划") == [
        "generate_self_introductions",
        "prepare_interview_questions",
        "build_capability_plan",
    ]


def test_career_toolbox_rejects_unknown_tool(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """Career Agent 不能借机调用通用知识库或系统工具。"""
    with session_factory() as session:
        conversation = _prepare_context(
            session, test_settings, tmp_path / "profile.json"
        )
        toolbox = CareerToolbox(CareerAdviceService(session, test_settings, conversation))
        try:
            toolbox.invoke("search_knowledge")
        except ValueError as exc:
            assert "不允许调用求职顾问工具" in str(exc)
        else:
            raise AssertionError("Career Agent 执行了白名单外工具")


def test_agent_uses_bound_job_for_multi_turn_career_question(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """绑定 JD 后的优势和风险追问应走独立 Career Agent 并保存结果。"""
    with session_factory() as session:
        conversation = _prepare_context(
            session, test_settings, tmp_path / "profile.json"
        )
        result = AgentService(session, test_settings).run(
            conversation.id,
            "这个岗位我的优势和风险分别是什么？",
            "career-followup-request",
        )
        messages = list(
            session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at)
            )
        )
        run = session.scalar(
            select(AgentRun).where(AgentRun.request_id == "career-followup-request")
        )

    assert result.answer_mode == "career_advisor"
    assert "岗位优势" in result.answer
    assert "应聘风险" in result.answer
    assert result.grounded is True
    assert [step["node"] for step in result.steps] == [
        "career_plan",
        "career_tool",
        "career_tool",
        "career_compose",
    ]
    assert [message.role for message in messages] == ["user", "assistant"]
    assert run is not None and run.status == "completed"


def test_changed_profile_version_forces_reanalysis(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """个人档案升级后不能继续使用旧 JD 报告给出求职判断。"""
    with session_factory() as session:
        conversation = _prepare_context(
            session,
            test_settings,
            tmp_path / "profile.json",
            bound_version=2,
            current_version=3,
        )
        result = AgentService(session, test_settings).run(
            conversation.id,
            "我应该怎么投递这个岗位？",
            "career-stale-request",
        )

    assert result.answer_mode == "career_advisor"
    assert result.degraded is True
    assert "重新提交该 JD" in result.answer
    assert result.citations == []


def test_career_materials_are_grounded_and_exportable(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """自我介绍、项目亮点与导出报告必须沿用已验证证据。"""
    with session_factory() as session:
        conversation = _prepare_context(
            session, test_settings, tmp_path / "profile.json"
        )
        service = CareerAdviceService(session, test_settings, conversation)
        materials = service.build_material_bundle()
        report = service.render_material_report()

    assert len(materials["sections"]) == 4
    assert "30 秒版" in materials["sections"][0]["content"]
    assert "LangGraph" in materials["sections"][1]["content"]
    assert materials["sections"][0]["evidence"][0]["chunk_id"] == "profile:agent-rag"
    assert "## 引用资料" in report
    assert "[1] **结构化个人档案**" in report


def test_agent_generates_job_specific_introduction(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """材料类追问应进入 Career Agent 并持久化带引用回答。"""
    with session_factory() as session:
        conversation = _prepare_context(
            session, test_settings, tmp_path / "profile.json"
        )
        result = AgentService(session, test_settings).run(
            conversation.id,
            "为这个岗位生成30秒、1分钟和文字版自我介绍",
            "career-material-introduction",
        )

    assert result.answer_mode == "career_advisor"
    assert "30 秒版" in result.answer
    assert "1 分钟版" in result.answer
    assert result.grounded is True


def test_career_step_limit_prevents_tool_execution(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """预算只够规划和收尾时，工作流不得越界调用分析工具。"""
    test_settings.career_agent_max_steps = 2
    with session_factory() as session:
        conversation = _prepare_context(
            session, test_settings, tmp_path / "profile.json"
        )
        result = AgentService(session, test_settings).run(
            conversation.id,
            "分析优势、风险、缺口和投递策略",
            "career-limit-request",
        )

    assert len(result.steps) == 2
    assert result.degraded is True
    assert all(step["node"] != "career_tool" for step in result.steps)
