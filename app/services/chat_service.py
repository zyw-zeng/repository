"""协调查询改写、检索、流式回答和权威引用读取。"""

import time
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.agent.runtime import emit_agent_event, raise_if_agent_cancelled
from app.core.config import Settings, get_settings
from app.knowledge.context import assemble_context
from app.knowledge.indexer import VectorIndexer
from app.knowledge.rag import (
    PROFILE_INTRO_RETRIEVAL_QUERY,
    REFUSAL_ANSWER,
    GroundedAnswerGenerator,
    QueryRewriter,
    is_profile_introduction_request,
    message_delta_text,
)
from app.knowledge.retriever import KnowledgeRetriever
from app.knowledge.types import CitationRecord, RagAnswer, SearchFilters
from app.llm.factory import create_chat_model, create_router_model
from app.storage.repositories.documents import DocumentRepository


class ChatService:
    """提供不依赖 Agent 自主循环的可靠 RAG 问答能力。"""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        model: BaseChatModel | None = None,
        rewrite_model: BaseChatModel | None = None,
        retriever: KnowledgeRetriever | None = None,
    ):
        """组装模型和检索依赖，并允许测试注入确定性替身。"""
        self.session = session
        self.settings = settings or get_settings()
        self.model = model or create_chat_model(self.settings)
        # 测试只注入 model 时沿用同一替身；生产环境用快速模型完成查询改写。
        self.rewrite_model = rewrite_model or model or create_router_model(self.settings)
        self.retriever = retriever or KnowledgeRetriever(
            session,
            VectorIndexer(self.settings),
        )
        self.documents = DocumentRepository(session)

    def ask(
        self,
        question: str,
        *,
        mode: str = "knowledge_base",
        history: Sequence[tuple[str, str]] = (),
        filters: SearchFilters | None = None,
    ) -> RagAnswer:
        """按指定模式回答；知识库模式任何情况下都必须先执行检索。"""
        if mode == "casual":
            return self._answer_casual(question, history)
        return self._answer_from_knowledge(question, history, filters or SearchFilters())

    def _answer_casual(
        self,
        question: str,
        history: Sequence[tuple[str, str]],
    ) -> RagAnswer:
        """处理调用方明确标记的闲聊，不伪造知识库引用。"""
        recent_history = history[-self.settings.rag_max_history_messages :]
        history_text = "\n".join(f"{role}: {content}" for role, content in recent_history)
        messages = [
            SystemMessage(
                content=(
                    "你是友好的‘ZYW 的 AI 小助理’，帮助访客了解 ZYW 和他的项目。"
                    "当前是闲聊模式，请简洁回答，不要编造个人资料。"
                )
            ),
            HumanMessage(content=f"对话历史：\n{history_text}\n\n用户：{question}"),
        ]
        generation_started = time.perf_counter()
        answer_parts: list[str] = []
        for chunk in self.model.stream(messages):
            raise_if_agent_cancelled()
            delta = message_delta_text(chunk)
            if delta:
                answer_parts.append(delta)
                emit_agent_event("answer_delta", {"delta": delta})
        timings = {"generation_ms": self._finish_timing("generation", generation_started)}
        return RagAnswer(
            answer="".join(answer_parts).strip(),
            answer_mode="casual",
            grounded=False,
            rewritten_query=question.strip(),
            timings=timings,
        )

    def _answer_from_knowledge(
        self,
        question: str,
        history: Sequence[tuple[str, str]],
        filters: SearchFilters,
    ) -> RagAnswer:
        """执行检索后直接流式回答，并从 SQLite 读取匹配的权威引用。"""
        timings: dict[str, int] = {}
        profile_introduction = is_profile_introduction_request(question)
        rewrite_started = time.perf_counter()
        if profile_introduction:
            # 宽泛介绍需要同时召回概述、经历、能力和项目，不能只检索“介绍一下”。
            rewritten_query = PROFILE_INTRO_RETRIEVAL_QUERY
        else:
            rewritten_query = QueryRewriter(
                self.rewrite_model,
                max_history_messages=self.settings.rag_max_history_messages,
            ).rewrite(question, history)
        timings["rewrite_ms"] = self._finish_timing("rewrite", rewrite_started)
        retrieval_started = time.perf_counter()
        results = self.retriever.search(
            rewritten_query,
            # 个人介绍比单点问答需要更完整的信息覆盖，但不改变其他问答的成本。
            limit=(
                max(self.settings.rag_top_k, 8)
                if profile_introduction
                else self.settings.rag_top_k
            ),
            fetch_k=max(self.settings.rag_fetch_k, 32)
            if profile_introduction
            else self.settings.rag_fetch_k,
            min_score=self.settings.rag_min_score,
            filters=filters,
        )
        timings["retrieval_ms"] = self._finish_timing("retrieval", retrieval_started)
        if not results:
            return self._refusal(rewritten_query, timings=timings)

        context_started = time.perf_counter()
        context, items = assemble_context(
            results,
            max_chars=self.settings.rag_max_context_chars,
        )
        timings["context_ms"] = self._finish_timing("context", context_started)
        generator = GroundedAnswerGenerator(self.model)
        # 追问必须使用改写后的独立问题生成答案，避免代词丢失上下文。
        generation_started = time.perf_counter()
        answer, references = generator.generate(
            question.strip() if profile_introduction else rewritten_query,
            context,
            profile_introduction=profile_introduction,
        )
        timings["generation_ms"] = self._finish_timing("generation", generation_started)
        if answer == REFUSAL_ANSWER:
            return self._refusal(
                rewritten_query,
                retrieved_count=len(results),
                timings=timings,
            )

        # 只展示上下文内存在的编号；无效编号不会触发第二次模型调用或撤回回答。
        valid_reference_numbers = {item.reference_number for item in items}
        references = [number for number in references if number in valid_reference_numbers]
        referenced_items = [item for item in items if item.reference_number in references]
        verified_chunks = self.documents.get_verified_active_chunks(
            [item.result.chunk_id for item in referenced_items]
        )
        chunks_by_id = {chunk.id: chunk for chunk in verified_chunks}

        citations = []
        for item in referenced_items:
            chunk = chunks_by_id.get(item.result.chunk_id)
            if chunk is None:
                continue
            # 返回正文只取 SQLite 权威记录，不使用 Chroma 或提示词中的文本副本。
            citations.append(
                CitationRecord(
                    reference_number=item.reference_number,
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    filename=chunk.document.filename,
                    quote=chunk.content,
                    page_number=chunk.page_number,
                    heading=chunk.heading,
                    index_version=chunk.index_version,
                )
            )
        return RagAnswer(
            answer=answer,
            answer_mode="knowledge_base",
            grounded=bool(citations),
            rewritten_query=rewritten_query,
            citations=citations,
            retrieved_count=len(results),
            timings=timings,
            # 已经生成正式回答时不再重复相同检索。
            retry_allowed=False,
        )

    @staticmethod
    def _refusal(
        rewritten_query: str,
        *,
        retrieved_count: int = 0,
        timings: dict[str, int] | None = None,
        retry_allowed: bool = True,
    ) -> RagAnswer:
        """构造统一、可测试的无依据拒答结果。"""
        return RagAnswer(
            answer=REFUSAL_ANSWER,
            answer_mode="knowledge_base",
            grounded=False,
            rewritten_query=rewritten_query,
            retrieved_count=retrieved_count,
            timings=timings or {},
            retry_allowed=retry_allowed,
        )

    @staticmethod
    def _finish_timing(stage: str, started_at: float) -> int:
        """记录阶段耗时并立即推送 SSE，便于前端定位慢点。"""
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        emit_agent_event(
            "timing",
            {"stage": stage, "duration_ms": duration_ms},
        )
        return duration_ms
