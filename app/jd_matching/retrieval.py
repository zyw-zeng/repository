"""组合结构化档案、SQLite 关键词和 Chroma 向量召回。"""

import re

from app.jd_matching.evidence import evidence_source_quality
from app.jd_matching.profile import CandidateProfileService
from app.knowledge.retriever import KnowledgeRetriever
from app.knowledge.types import SearchFilters, SearchResult
from app.storage.repositories.documents import DocumentRepository

_DOMAIN_TERMS = (
    "前端开发经验",
    "后端开发经验",
    "计算机相关专业",
    "大专",
    "本科",
    "学历",
    "流式输出",
    "智能对话",
    "工具调用",
    "知识库",
    "浏览器插件",
    "数据可视化",
    "安全漏洞",
    "合规审查",
    "小程序",
    "扫码分享",
    "项目经验",
)


class HybridJdRetriever:
    """针对技术关键词和个人事实优化的 JD 混合检索器。"""

    def __init__(
        self,
        vector_retriever: KnowledgeRetriever,
        documents: DocumentRepository,
        profile: CandidateProfileService,
    ):
        self.vector_retriever = vector_retriever
        self.documents = documents
        self.profile = profile

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        fetch_k: int = 20,
        min_score: float = 0,
        filters: SearchFilters | None = None,
    ) -> list[SearchResult]:
        """合并三路结果，并按相关度和证据来源质量重新排序去重。"""
        terms = self._extract_terms(query)
        merged: dict[str, SearchResult] = {}
        for result in self.profile.search(query, limit=limit):
            merged[result.chunk_id] = result
        for chunk in self.documents.search_active_chunks_by_terms(
            terms, limit=max(fetch_k, limit), public_only=True
        ):
            content_lower = chunk.content.lower()
            hit_count = sum(term.lower() in content_lower for term in terms)
            lexical_score = min(0.96, 0.72 + hit_count * 0.05)
            merged[chunk.id] = SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=chunk.document.filename,
                content=chunk.content,
                score=lexical_score,
                page_number=chunk.page_number,
                heading=chunk.heading,
                index_version=chunk.index_version,
            )
        for result in self.vector_retriever.search(
            query,
            limit=max(limit, 5),
            fetch_k=fetch_k,
            min_score=min_score,
            filters=filters,
        ):
            existing = merged.get(result.chunk_id)
            if existing is None or result.score > existing.score:
                merged[result.chunk_id] = result

        # 未来规划类文本质量过低，不允许占用有限候选名额。
        candidates = [item for item in merged.values() if evidence_source_quality(item) >= 0.35]
        candidates.sort(
            key=lambda item: (item.score * 0.75 + evidence_source_quality(item) * 0.25),
            reverse=True,
        )
        return candidates[:limit]

    @staticmethod
    def _extract_terms(query: str) -> list[str]:
        """提取英文技术名词和中文短语，过滤无法提供区分度的词。"""
        english = re.findall(r"[A-Za-z][A-Za-z0-9.+#-]{1,30}", query)
        known_terms = [term for term in _DOMAIN_TERMS if term.lower() in query.lower()]
        clauses = re.split(r"[\s，、；;：:（）()]+", query)
        stop_words = {"熟悉", "具备", "能力", "经验", "相关", "使用", "深入理解", "要求"}
        chinese = []
        for clause in clauses:
            normalized = re.sub(
                r"^(?:熟悉|熟练使用|掌握|具备|有|了解|能够|负责)", "", clause
            ).strip()
            if 2 <= len(normalized) <= 12 and normalized not in stop_words:
                chinese.append(normalized)
        return list(
            dict.fromkeys(
                term
                for term in [*english, *known_terms, *chinese]
                if term.lower() not in stop_words
            )
        )[:12]
