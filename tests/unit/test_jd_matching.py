"""验证 JD 独立 LangGraph 的证据约束和确定性评分。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.jd_matching.graph import build_jd_matching_graph
from app.jd_matching.nodes import (
    AssessmentBatch,
    JdMatchingNodes,
    ParsedJd,
    ParsedRequirement,
    RequirementAssessment,
)
from app.knowledge.types import SearchResult
from app.services.jd_matching_service import JdMatchingService
from app.storage.models import Conversation, Message


class StructuredModelStub:
    """根据请求的结构化类型返回固定模型结果。"""

    def __init__(self, parsed: ParsedJd, assessments: AssessmentBatch):
        self.parsed = parsed
        self.assessments = assessments
        self.schema: type | None = None

    def with_structured_output(self, schema: type):
        """记录当前 LangChain 期望的输出结构。"""
        self.schema = schema
        return self

    def invoke(self, _messages: Any):
        """返回与当前结构相符的测试对象。"""
        return self.parsed if self.schema is ParsedJd else self.assessments


class RetrieverStub:
    """为 LangGraph 返回一条可验证的公开知识证据。"""

    def search(self, query: str, **_kwargs: Any) -> list[SearchResult]:
        """仅为 Python 要求返回证据，其他要求模拟无资料。"""
        if "Python" not in query:
            return []
        return [
            SearchResult(
                chunk_id="chunk-python",
                document_id="doc-resume",
                filename="简历.pdf",
                content="使用 Python 与 FastAPI 开发 AI Agent 后端。",
                score=0.88,
                page_number=1,
                heading="项目经历",
                index_version=2,
            )
        ]


class BrokenEvaluatorStub:
    """模拟结构化证据判断因输出截断而失败。"""

    def with_structured_output(self, _schema: type):
        """保持与 LangChain 模型包装接口一致。"""
        return self

    def invoke(self, _messages: Any):
        """抛出错误以验证单批安全降级。"""
        raise RuntimeError("structured output truncated")


def test_jd_graph_keeps_unverified_requirements_out_of_score() -> None:
    """无引用结论必须降为暂无依据，且不能获得模型自由给出的分数。"""
    parsed = ParsedJd(
        company_name="示例公司",
        job_title="AI Agent 工程师",
        requirements=[
            ParsedRequirement(
                requirement="熟练使用 Python",
                category="programming",
                importance="required",
                weight=10,
                keywords=["Python"],
            ),
            ParsedRequirement(
                requirement="拥有 Kubernetes 经验",
                category="devops",
                importance="preferred",
                weight=5,
                keywords=["Kubernetes"],
            ),
        ],
    )
    assessments = AssessmentBatch(
        assessments=[
            RequirementAssessment(
                requirement_id="req-1",
                level="strong_match",
                reason="项目中存在直接使用证据。",
                evidence_ids=["chunk-python", "invented-id"],
            ),
            RequirementAssessment(
                requirement_id="req-2",
                level="strong_match",
                reason="模型错误声称匹配。",
                evidence_ids=["invented-id"],
            ),
        ]
    )
    model = StructuredModelStub(parsed, assessments)
    events: list[tuple[str, dict[str, Any]]] = []
    nodes = JdMatchingNodes(
        model,  # type: ignore[arg-type]
        model,  # type: ignore[arg-type]
        RetrieverStub(),  # type: ignore[arg-type]
        publish=lambda event, data: events.append((event, data)),
    )

    result = build_jd_matching_graph(nodes).invoke({"jd_text": "x" * 100})

    assert result["score"] == 63.3
    assert result["completeness"] == 66.7
    assert result["verified_fit"] == 95.0
    assert result["feasibility"] == 69.7
    assert result["matches"][0]["evidence"][0]["chunk_id"] == "chunk-python"
    assert result["matches"][1]["level"] == "unverified"
    assert result["matches"][1]["awarded_score"] == 0
    assert any(event == "jd_parsed" for event, _ in events)
    assert sum(event == "requirement_evaluated" for event, _ in events) == 2


def test_jd_graph_degrades_failed_evaluation_batches() -> None:
    """证据判断批次失败时仍应生成零编造的完整报告。"""
    parsed = ParsedJd(
        job_title="前端工程师",
        requirements=[
            ParsedRequirement(
                requirement="熟练使用 Python",
                category="programming",
                importance="required",
                weight=10,
                keywords=["Python"],
            )
        ],
    )
    parser = StructuredModelStub(parsed, AssessmentBatch(assessments=[]))
    events: list[tuple[str, dict[str, Any]]] = []
    nodes = JdMatchingNodes(
        parser,  # type: ignore[arg-type]
        BrokenEvaluatorStub(),  # type: ignore[arg-type]
        RetrieverStub(),  # type: ignore[arg-type]
        publish=lambda event, data: events.append((event, data)),
        evaluation_batch_size=1,
    )

    result = build_jd_matching_graph(nodes).invoke({"jd_text": "x" * 100})

    assert result["score"] == 0
    assert result["matches"][0]["level"] == "unverified"
    assert any(event == "evaluation_batch_failed" for event, _ in events)


def test_verification_downgrades_weak_source_and_keeps_explicit_missing() -> None:
    """低质量来源不能强匹配，明确反证可以标记为未满足。"""
    parsed = ParsedJd(job_title="测试岗位", requirements=[])
    model = StructuredModelStub(parsed, AssessmentBatch(assessments=[]))
    nodes = JdMatchingNodes(
        model,  # type: ignore[arg-type]
        model,  # type: ignore[arg-type]
        RetrieverStub(),  # type: ignore[arg-type]
    )
    state = {
        "requirements": [
            {
                "id": "req-1",
                "requirement": "浏览器插件经验",
                "category": "加分项",
                "requirement_type": "project_experience",
                "importance": "preferred",
                "weight": 4,
            },
            {
                "id": "req-2",
                "requirement": "本科及以上学历",
                "category": "必备项",
                "requirement_type": "profile_fact",
                "importance": "required",
                "weight": 8,
            },
        ],
        "evidence_by_requirement": {
            "req-1": [
                {
                    "chunk_id": "plan-1",
                    "document_id": "doc-plan",
                    "filename": "DEVELOPMENT_PLAN.md",
                    "quote": "项目后续计划增加浏览器插件。",
                    "page_number": None,
                    "heading": "规划",
                    "index_version": 1,
                    "score": 0.8,
                    "source_type": "plan",
                    "source_quality": 0.2,
                }
            ],
            "req-2": [
                {
                    "chunk_id": "profile-education",
                    "document_id": "candidate-profile",
                    "filename": "结构化个人档案",
                    "quote": "本人确认的最高学历未达到本科。",
                    "page_number": None,
                    "heading": "学历",
                    "index_version": 1,
                    "score": 1.0,
                    "source_type": "profile",
                    "source_quality": 1.0,
                }
            ],
        },
        "assessments": [
            {
                "requirement_id": "req-1",
                "level": "strong_match",
                "reason": "规划中提到了该能力。",
                "evidence_ids": ["plan-1"],
            },
            {
                "requirement_id": "req-2",
                "level": "missing",
                "reason": "结构化档案明确显示未达到要求。",
                "evidence_ids": ["profile-education"],
            },
        ],
    }

    result = nodes.verify_and_score(state)  # type: ignore[arg-type]

    assert result["matches"][0]["level"] == "partial_match"
    assert result["matches"][1]["level"] == "missing"
    assert result["feasibility"] < result["score"]


def test_jd_service_persists_chat_artifact(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
    tmp_path,
) -> None:
    """绑定会话的 JD 分析完成后应写入可恢复的聊天工具卡片。"""
    profile_path = tmp_path / "candidate_profile.json"
    profile_path.write_text('{"version": 1, "facts": []}', encoding="utf-8")
    test_settings.candidate_profile_path = profile_path
    parsed = ParsedJd(
        job_title="AI Agent 工程师",
        requirements=[
            ParsedRequirement(
                requirement="熟练使用 Python",
                category="programming",
                importance="required",
                weight=10,
                keywords=["Python"],
            )
        ],
    )
    assessments = AssessmentBatch(
        assessments=[
            RequirementAssessment(
                requirement_id="req-1",
                level="strong_match",
                reason="存在直接项目证据。",
                evidence_ids=["chunk-python"],
            )
        ]
    )
    model = StructuredModelStub(parsed, assessments)
    with session_factory() as session:
        conversation = Conversation(title="新会话")
        session.add(conversation)
        session.commit()
        report = JdMatchingService(
            session,
            test_settings,
            parser_model=model,  # type: ignore[arg-type]
            evaluator_model=model,  # type: ignore[arg-type]
            retriever=RetrieverStub(),  # type: ignore[arg-type]
        ).run(
            "岗位要求：" + "Python Agent 开发经验" * 5,
            "jd-chat-request",
            conversation_id=conversation.id,
        )
        messages = list(
            session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at)
            )
        )

    assert report.status == "completed"
    assert conversation.active_jd_analysis_id == report.id
    assert conversation.candidate_profile_version == 1
    assert conversation.career_context_updated_at is not None
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[1].artifacts_json == [
        {"type": "jd_analysis", "analysis_id": report.id}
    ]
