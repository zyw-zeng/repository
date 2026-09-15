"""实现 JD 解析、证据检索、匹配判断和确定性评分节点。"""

import json
from collections.abc import Callable
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.jd_matching.atomic import atomize_requirements
from app.jd_matching.evidence import evidence_source_quality, evidence_source_type
from app.jd_matching.scoring import awarded_score, calculate_scores
from app.jd_matching.state import JdMatchingState
from app.knowledge.retriever import KnowledgeRetriever


class ParsedRequirement(BaseModel):
    """模型输出的一项去重后岗位要求。"""

    requirement: str
    category: str
    importance: Literal["required", "preferred"]
    weight: int = Field(ge=1, le=10)
    keywords: list[str] = Field(default_factory=list)
    requirement_type: Literal[
        "profile_fact",
        "technical_skill",
        "engineering_capability",
        "project_experience",
        "bonus_experience",
    ] = "technical_skill"


class ParsedJd(BaseModel):
    """模型输出的 JD 结构化结果。"""

    company_name: str | None = None
    job_title: str | None = None
    # 模型偶尔可能多返回项目，由节点统一截断，避免整个结构化响应因此校验失败。
    requirements: list[ParsedRequirement]


class RequirementAssessment(BaseModel):
    """模型基于候选证据给出的受约束结论。"""

    requirement_id: str
    level: Literal[
        "strong_match", "partial_match", "missing", "unverified", "conflict"
    ]
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


class AssessmentBatch(BaseModel):
    """一次模型调用返回的全部逐项判断。"""

    assessments: list[RequirementAssessment]


EventPublisher = Callable[[str, dict[str, Any]], None]
CancellationChecker = Callable[[], bool]


class JdMatchingNodes:
    """持有模型、检索器和实时事件出口的 LangGraph 节点集合。"""

    def __init__(
        self,
        parser_model: BaseChatModel,
        evaluator_model: BaseChatModel,
        retriever: KnowledgeRetriever,
        *,
        publish: EventPublisher | None = None,
        is_cancelled: CancellationChecker | None = None,
        top_k: int = 3,
        fetch_k: int = 20,
        min_score: float = 0.3,
        evaluation_batch_size: int = 5,
        evidence_quote_chars: int = 350,
    ):
        self.parser_model = parser_model
        self.evaluator_model = evaluator_model
        self.retriever = retriever
        self.publish = publish or (lambda _event, _data: None)
        self.is_cancelled = is_cancelled or (lambda: False)
        self.top_k = top_k
        self.fetch_k = fetch_k
        self.min_score = min_score
        self.evaluation_batch_size = max(1, evaluation_batch_size)
        self.evidence_quote_chars = max(120, evidence_quote_chars)

    def _check_cancelled(self) -> None:
        """在昂贵步骤之间响应服务端取消信号。"""
        if self.is_cancelled():
            raise InterruptedError("JD 分析已取消")

    def parse_jd(self, state: JdMatchingState) -> dict[str, Any]:
        """把自由文本 JD 转成最多十五项可验证要求。"""
        self._check_cancelled()
        self.publish("agent_step", {"node": "parse_jd", "status": "running"})
        structured = self.parser_model.with_structured_output(ParsedJd)
        parsed = structured.invoke(
            [
                SystemMessage(
                    content=(
                        "你是岗位分析器。提取公司、岗位和可验证要求，合并同义重复项。"
                        "每项必须只包含一个可独立判断的事实或能力：例如‘3年以上前端经验，"
                        "计算机专业’必须拆成两项；‘Vue经验和TypeScript工程化’也必须拆分。"
                        "最多保留18项核心要求。必备项权重6-10，加分项权重1-5。"
                        "同时标记要求类型，不要补充原文不存在的要求。"
                    )
                ),
                HumanMessage(content=state["jd_text"]),
            ]
        )
        extracted = [item.model_dump() for item in parsed.requirements[:18]]
        # 模型未完全遵循原子化约束时，再由确定性规则拆分并重建顺序 ID。
        requirements = atomize_requirements(extracted)
        if not requirements:
            raise ValueError("没有从 JD 中提取到可评价要求")
        self.publish(
            "jd_parsed",
            {
                "company_name": parsed.company_name,
                "job_title": parsed.job_title,
                "requirements": requirements,
            },
        )
        return {
            "company_name": parsed.company_name,
            "job_title": parsed.job_title,
            "requirements": requirements,
        }

    def retrieve_evidence(self, state: JdMatchingState) -> dict[str, Any]:
        """为每项要求独立检索公开、活动版本的知识库证据。"""
        evidence_by_requirement: dict[str, list[dict[str, Any]]] = {}
        for requirement in state["requirements"]:
            self._check_cancelled()
            requirement_id = requirement["id"]
            self.publish(
                "requirement_started",
                {"requirement_id": requirement_id, "requirement": requirement["requirement"]},
            )
            query_parts = [requirement["requirement"], *requirement.get("keywords", [])]
            results = self.retriever.search(
                " ".join(dict.fromkeys(query_parts)),
                limit=self.top_k,
                fetch_k=self.fetch_k,
                min_score=self.min_score,
            )
            evidence = [
                {
                    "chunk_id": result.chunk_id,
                    "document_id": result.document_id,
                    "filename": result.filename,
                    # 判断模型只需要最相关正文，限制长度可显著降低批量输入体积。
                    "quote": result.content[: self.evidence_quote_chars],
                    "page_number": result.page_number,
                    "heading": result.heading,
                    "index_version": result.index_version,
                    "score": round(result.score, 4),
                    "source_type": evidence_source_type(result),
                    "source_quality": evidence_source_quality(result),
                }
                for result in results
            ]
            evidence_by_requirement[requirement_id] = evidence
            self.publish(
                "evidence_found",
                {"requirement_id": requirement_id, "count": len(evidence)},
            )
        return {"evidence_by_requirement": evidence_by_requirement}

    def evaluate_requirements(self, state: JdMatchingState) -> dict[str, Any]:
        """小批量判断证据，避免长结构化输出被模型 Token 上限截断。"""
        payload: list[dict[str, Any]] = []
        for requirement in state["requirements"]:
            payload.append(
                {
                    "requirement_id": requirement["id"],
                    "requirement": requirement["requirement"],
                    "evidence": [
                        {
                            "id": item["chunk_id"],
                            "content": item["quote"],
                            "source": item["filename"],
                            "source_type": item["source_type"],
                            "source_quality": item["source_quality"],
                        }
                        for item in state["evidence_by_requirement"].get(requirement["id"], [])
                    ],
                }
            )
        assessments: list[dict[str, Any]] = []
        batches = [
            payload[index : index + self.evaluation_batch_size]
            for index in range(0, len(payload), self.evaluation_batch_size)
        ]
        for batch_index, batch in enumerate(batches, start=1):
            self._check_cancelled()
            self.publish(
                "evaluation_batch_started",
                {"batch": batch_index, "total_batches": len(batches), "size": len(batch)},
            )
            try:
                # 每批重新建立结构化包装，避免客户端在失败后复用不完整状态。
                structured = self.evaluator_model.with_structured_output(AssessmentBatch)
                result = structured.invoke(
                    [
                        SystemMessage(
                            content=(
                                "你是严格的求职证据核验器。只能根据所给证据判断："
                                "strong_match 表示直接且充分，partial_match 表示相关但不完整，"
                                "missing 仅表示证据明确证明未达到要求，unverified 表示无足够依据，"
                                "conflict 仅用于不同证据之间明确矛盾。"
                                "不得把相近技术视为相同经验；只返回真实证据ID。"
                                "规划或低质量来源不能单独支持强匹配。"
                            )
                        ),
                        HumanMessage(content=json.dumps(batch, ensure_ascii=False)),
                    ]
                )
                batch_assessments = [item.model_dump() for item in result.assessments]
                allowed_ids = {item["requirement_id"] for item in batch}
                # 丢弃模型越界返回的其他批次要求，保证批次之间互不污染。
                assessments.extend(
                    item for item in batch_assessments if item["requirement_id"] in allowed_ids
                )
                self.publish(
                    "evaluation_batch_completed",
                    {"batch": batch_index, "total_batches": len(batches)},
                )
            except Exception as exc:
                # 单批长度或格式异常不能拖垮整份报告；缺失项会在评分节点安全降级。
                self.publish(
                    "evaluation_batch_failed",
                    {
                        "batch": batch_index,
                        "total_batches": len(batches),
                        "error_type": type(exc).__name__,
                    },
                )
                assessments.extend(
                    {
                        "requirement_id": item["requirement_id"],
                        "level": "unverified",
                        "reason": "本项证据判断暂时失败，已按暂无依据安全处理。",
                        "evidence_ids": [],
                    }
                    for item in batch
                )
        return {"assessments": assessments}

    def verify_and_score(self, state: JdMatchingState) -> dict[str, Any]:
        """过滤模型伪造的证据 ID，并由代码计算每项和总分。"""
        assessment_map = {item["requirement_id"]: item for item in state["assessments"]}
        matches: list[dict[str, Any]] = []
        for requirement in state["requirements"]:
            candidates = state["evidence_by_requirement"].get(requirement["id"], [])
            candidate_map = {item["chunk_id"]: item for item in candidates}
            assessment = assessment_map.get(requirement["id"], {})
            evidence = [
                candidate_map[evidence_id]
                for evidence_id in assessment.get("evidence_ids", [])
                if evidence_id in candidate_map
            ]
            level = assessment.get("level", "unverified")
            # 没有经过验证的引用时，不允许模型声称匹配或冲突。
            if not evidence:
                level = "unverified"
            reason = assessment.get("reason") or "知识库中暂无足够证据。"
            if level == "unverified" and not evidence:
                reason = "知识库中暂无足够证据，不能据此判断本人不具备该能力。"
            source_quality = max(
                (float(item.get("source_quality", 0.0)) for item in evidence),
                default=0.0,
            )
            # 规划文档或其他较弱来源只能证明相关性，不能单独形成强匹配。
            if level == "strong_match" and source_quality < 0.75:
                level = "partial_match"
                reason = f"{reason} 当前证据来源强度不足，已保守调整为部分匹配。"
            item = {
                "requirement_id": requirement["id"],
                "requirement": requirement["requirement"],
                "category": requirement["category"],
                "requirement_type": requirement["requirement_type"],
                "importance": requirement["importance"],
                "weight": requirement["weight"],
                "level": level,
                "reason": reason,
                "awarded_score": awarded_score(
                    requirement["weight"], level, source_quality
                ),
                "max_score": float(requirement["weight"]),
                "evidence": evidence,
            }
            matches.append(item)
            self.publish("requirement_evaluated", item)
        score, completeness, verified_fit, feasibility = calculate_scores(matches)
        self.publish(
            "score_calculated",
            {
                "score": score,
                "completeness": completeness,
                "verified_fit": verified_fit,
                "feasibility": feasibility,
            },
        )
        return {
            "matches": matches,
            "score": score,
            "completeness": completeness,
            "verified_fit": verified_fit,
            "feasibility": feasibility,
        }
