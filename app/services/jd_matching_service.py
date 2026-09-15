"""协调 JD LangGraph、可靠检索、确定性评分和结果持久化。"""

import time
from collections.abc import Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.jd_matching.atomic import identify_requirement_type
from app.jd_matching.evidence import evidence_source_quality, evidence_source_type
from app.jd_matching.graph import build_jd_matching_graph
from app.jd_matching.nodes import JdMatchingNodes
from app.jd_matching.profile import CandidateProfileService
from app.jd_matching.retrieval import HybridJdRetriever
from app.jd_matching.scoring import calculate_scores
from app.knowledge.indexer import VectorIndexer
from app.knowledge.retriever import KnowledgeRetriever
from app.llm.factory import create_jd_model
from app.schemas.jd_matching import JdAnalysisResponse
from app.storage.models import JdAnalysis, Message, utc_now
from app.storage.repositories.conversations import ConversationRepository
from app.storage.repositories.documents import DocumentRepository
from app.storage.repositories.jd_analyses import JdAnalysisRepository


class JdMatchingService:
    """提供独立于普通问答的岗位匹配用例。"""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        parser_model: BaseChatModel | None = None,
        evaluator_model: BaseChatModel | None = None,
        retriever: KnowledgeRetriever | None = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.parser_model = parser_model
        self.evaluator_model = evaluator_model
        self.retriever = retriever
        self.analyses = JdAnalysisRepository(session)
        self.conversations = ConversationRepository(session)

    def get(self, analysis_id: str) -> JdAnalysisResponse:
        """读取已保存报告，不存在时返回统一 404。"""
        analysis = self.analyses.get(analysis_id)
        if analysis is None:
            raise AppError("JD 分析不存在", status_code=404, code="jd_analysis_not_found")
        return self._to_response(analysis)

    def run(
        self,
        jd_text: str,
        request_id: str,
        *,
        conversation_id: str | None = None,
        publish: Callable[[str, dict[str, Any]], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> JdAnalysisResponse:
        """执行一次有界 JD 工作流，并保存成功或失败状态。"""
        if self.analyses.get_by_request_id(request_id) is not None:
            raise AppError("该 JD 请求已经执行", status_code=409, code="duplicate_request")
        conversation = None
        if conversation_id:
            conversation = self.conversations.get(conversation_id)
            if conversation is None:
                raise AppError("会话不存在", status_code=404, code="conversation_not_found")
        analysis = self.analyses.add(
            JdAnalysis(
                request_id=request_id,
                conversation_id=conversation_id,
                status="running",
                jd_text=jd_text,
            )
        )
        self.session.commit()
        started = time.perf_counter()
        try:
            # JD 结构化结果使用独立输出预算，避免继承普通回答的 1200 Token 上限。
            parser_model = self.parser_model or create_jd_model(self.settings)
            evaluator_model = self.evaluator_model or create_jd_model(self.settings)
            if self.retriever is not None:
                retriever = self.retriever
            else:
                vector_retriever = KnowledgeRetriever(
                    self.session, VectorIndexer(self.settings)
                )
                retriever = HybridJdRetriever(
                    vector_retriever,
                    DocumentRepository(self.session),
                    CandidateProfileService(self.settings.candidate_profile_path),
                )
            nodes = JdMatchingNodes(
                parser_model,
                evaluator_model,
                retriever,
                publish=publish,
                is_cancelled=is_cancelled,
                top_k=3,
                fetch_k=max(self.settings.rag_fetch_k, 20),
                min_score=max(0.25, self.settings.rag_min_score - 0.05),
                evaluation_batch_size=self.settings.jd_evaluation_batch_size,
                evidence_quote_chars=self.settings.jd_evidence_quote_chars,
            )
            state = build_jd_matching_graph(nodes).invoke(
                {"jd_text": jd_text}, config={"recursion_limit": 8}
            )
            analysis.status = "completed"
            analysis.company_name = state.get("company_name")
            analysis.job_title = state.get("job_title")
            analysis.requirements_json = state.get("requirements", [])
            analysis.matches_json = state.get("matches", [])
            analysis.score = state.get("score", 0.0)
            analysis.completeness = state.get("completeness", 0.0)
            analysis.verified_fit = state.get("verified_fit", 0.0)
            analysis.feasibility = state.get("feasibility", 0.0)
            analysis.duration_ms = int((time.perf_counter() - started) * 1000)
            if conversation is not None:
                profile = CandidateProfileService(self.settings.candidate_profile_path)
                conversation.active_jd_analysis_id = analysis.id
                conversation.candidate_profile_version = profile.get_version()
                conversation.career_context_updated_at = utc_now()
                self._persist_chat_messages(analysis, conversation)
            self.session.commit()
            return self._to_response(analysis)
        except InterruptedError:
            self.session.rollback()
            analysis = self.analyses.get(analysis.id)
            if analysis is None:
                raise
            analysis.status = "cancelled"
            analysis.error_message = "jd_analysis_cancelled"
            analysis.duration_ms = int((time.perf_counter() - started) * 1000)
            self.session.commit()
            return self._to_response(analysis)
        except Exception as exc:
            self.session.rollback()
            analysis = self.analyses.get(analysis.id)
            if analysis is not None:
                analysis.status = "failed"
                analysis.error_message = f"{type(exc).__name__}: {exc}"
                analysis.duration_ms = int((time.perf_counter() - started) * 1000)
                self.session.commit()
            raise

    def _persist_chat_messages(self, analysis: JdAnalysis, conversation) -> None:
        """把报告作为轻量引用写入聊天记录，完整结果仍以分析表为准。"""
        title = analysis.job_title or "目标岗位"
        user_summary = f"岗位匹配：已提交 {title} 的岗位描述。"
        assistant_summary = (
            f"已完成 {title} 的证据化岗位匹配：岗位匹配度 "
            f"{analysis.score or 0:.1f}%，求职可行度 {analysis.feasibility or 0:.1f}%。"
        )
        self.conversations.add_message(
            Message(conversation_id=conversation.id, role="user", content=user_summary)
        )
        self.conversations.add_message(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_summary,
                artifacts_json=[{"type": "jd_analysis", "analysis_id": analysis.id}],
            )
        )
        if conversation.title == "新会话":
            conversation.title = f"JD 匹配 · {title}"[:255]

    @staticmethod
    def _to_response(analysis: JdAnalysis) -> JdAnalysisResponse:
        """将 JSON 持久化字段转换为稳定接口模型。"""
        requirements = []
        for item in analysis.requirements_json or []:
            requirements.append(
                {
                    **item,
                    "requirement_type": item.get("requirement_type")
                    or identify_requirement_type(str(item.get("requirement", ""))),
                }
            )
        matches = []
        for item in analysis.matches_json or []:
            evidence = [
                {
                    **source,
                    "source_type": source.get("source_type")
                    or evidence_source_type(source),
                    "source_quality": source.get("source_quality")
                    if source.get("source_quality") is not None
                    else evidence_source_quality(source),
                }
                for source in item.get("evidence", [])
            ]
            matches.append(
                {
                    **item,
                    "requirement_type": item.get("requirement_type")
                    or identify_requirement_type(str(item.get("requirement", ""))),
                    "evidence": evidence,
                }
            )
        verified_fit = analysis.verified_fit
        if verified_fit is None and analysis.score is not None and analysis.completeness:
            verified_fit = round(analysis.score / analysis.completeness * 100, 1)
        feasibility = analysis.feasibility
        if feasibility is None and matches:
            feasibility = calculate_scores(matches)[3]
        return JdAnalysisResponse(
            id=analysis.id,
            request_id=analysis.request_id,
            status=analysis.status,
            company_name=analysis.company_name,
            job_title=analysis.job_title,
            score=analysis.score,
            completeness=analysis.completeness,
            verified_fit=verified_fit,
            feasibility=feasibility,
            requirements=requirements,
            matches=matches,
            duration_ms=analysis.duration_ms,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )
