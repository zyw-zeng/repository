"""组合 Chroma 候选召回和 SQLite 活动版本校验。"""

from sqlalchemy.orm import Session

from app.knowledge.indexer import VectorIndexer
from app.knowledge.types import SearchFilters, SearchResult
from app.storage.repositories.documents import DocumentRepository


class KnowledgeRetriever:
    """只返回数据库中处于活动版本且状态正常的权威切片。"""

    def __init__(self, session: Session, indexer: VectorIndexer):
        """绑定数据库会话和向量索引适配器。"""
        self.documents = DocumentRepository(session)
        self.indexer = indexer

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        fetch_k: int = 20,
        min_score: float = 0,
        filters: SearchFilters | None = None,
    ) -> list[SearchResult]:
        """召回候选，并完成元数据过滤、活动版本校验和正文去重。"""
        active_filters = filters or SearchFilters()
        where = self._build_chroma_filter(active_filters)
        candidates = self.indexer.query_ids(
            query,
            fetch_k=max(fetch_k, limit),
            where=where,
        )
        distances = {chunk_id: distance for chunk_id, distance in candidates}
        chunks = self.documents.get_active_chunks_by_ids(
            [item[0] for item in candidates],
            document_ids=active_filters.document_ids,
            filenames=active_filters.filenames,
        )

        results = []
        seen_content_hashes: set[str] = set()
        for chunk in chunks:
            distance = distances.get(chunk.id, 1.0)
            score = max(0.0, 1.0 - distance)
            if score < min_score or chunk.content_hash in seen_content_hashes:
                continue
            seen_content_hashes.add(chunk.content_hash)
            results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    filename=chunk.document.filename,
                    content=chunk.content,
                    score=score,
                    page_number=chunk.page_number,
                    heading=chunk.heading,
                    index_version=chunk.index_version,
                )
            )
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def _build_chroma_filter(filters: SearchFilters) -> dict | None:
        """把受支持的过滤条件转换为 Chroma 的 where 表达式。"""
        clauses: list[dict] = []
        if filters.document_ids:
            clauses.append({"document_id": {"$in": filters.document_ids}})
        if filters.filenames:
            clauses.append({"filename": {"$in": filters.filenames}})
        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}
