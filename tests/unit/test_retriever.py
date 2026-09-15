"""向量候选过滤、活动版本校验和去重测试。"""

from sqlalchemy.orm import Session, sessionmaker

from app.knowledge.retriever import KnowledgeRetriever
from app.knowledge.types import SearchFilters
from app.storage.models import DocumentChunk, DocumentRecord


class StubIndexer:
    """记录过滤参数并返回固定候选的向量索引替身。"""

    def __init__(self, candidates: list[tuple[str, float]]):
        """保存固定候选。"""
        self.candidates = candidates
        self.where: dict | None = None

    def query_ids(
        self,
        query: str,
        *,
        fetch_k: int = 20,
        where: dict | None = None,
    ) -> list[tuple[str, float]]:
        """返回固定候选并记录 Chroma 过滤表达式。"""
        assert query
        assert fetch_k >= 1
        self.where = where
        return self.candidates


def add_chunk(
    session: Session,
    document: DocumentRecord,
    *,
    chunk_id: str,
    version: int,
    content: str,
    content_hash: str,
    chunk_index: int = 0,
) -> None:
    """向测试数据库加入一个文档切片。"""
    session.add(
        DocumentChunk(
            id=chunk_id,
            document_id=document.id,
            index_version=version,
            chunk_index=chunk_index,
            content=content,
            content_hash=content_hash,
            token_count=len(content),
            vector_id=chunk_id,
        )
    )


def test_retriever_filters_versions_metadata_scores_and_duplicates(
    session_factory: sessionmaker[Session],
) -> None:
    """检索结果只能来自匹配元数据的活动版本，并去除重复正文。"""
    with session_factory() as session:
        selected = DocumentRecord(
            id="doc-selected",
            filename="可靠RAG.md",
            file_hash="a" * 64,
            file_type="md",
            storage_path="selected.md",
            status="ready",
            visibility="public",
            active_index_version=2,
        )
        other = DocumentRecord(
            id="doc-other",
            filename="其他.md",
            file_hash="b" * 64,
            file_type="md",
            storage_path="other.md",
            status="ready",
            visibility="public",
            active_index_version=1,
        )
        session.add_all([selected, other])
        session.flush()
        add_chunk(
            session,
            selected,
            chunk_id="active-1",
            version=2,
            content="可靠正文",
            content_hash="same",
            chunk_index=0,
        )
        add_chunk(
            session,
            selected,
            chunk_id="active-duplicate",
            version=2,
            content="可靠正文",
            content_hash="same",
            chunk_index=1,
        )
        add_chunk(
            session,
            selected,
            chunk_id="stale",
            version=1,
            content="过期正文",
            content_hash="stale",
        )
        add_chunk(
            session,
            other,
            chunk_id="other",
            version=1,
            content="其他正文",
            content_hash="other",
        )
        session.commit()

        indexer = StubIndexer(
            [("active-1", 0.1), ("active-duplicate", 0.2), ("stale", 0.1), ("other", 0.1)]
        )
        results = KnowledgeRetriever(session, indexer).search(
            "可靠 RAG",
            min_score=0.5,
            filters=SearchFilters(
                document_ids=["doc-selected"],
                filenames=["可靠RAG.md"],
            ),
        )

    assert [result.chunk_id for result in results] == ["active-1"]
    assert indexer.where == {
        "$and": [
            {"document_id": {"$in": ["doc-selected"]}},
            {"filename": {"$in": ["可靠RAG.md"]}},
        ]
    }


def test_retriever_excludes_private_documents(
    session_factory: sessionmaker[Session],
) -> None:
    """即使 Chroma 返回私有切片 ID，SQLite 安全边界也必须将其剔除。"""
    with session_factory() as session:
        document = DocumentRecord(
            id="doc-private",
            filename="私密资料.md",
            file_hash="p" * 64,
            file_type="md",
            storage_path="private.md",
            status="ready",
            visibility="private",
            active_index_version=1,
        )
        session.add(document)
        session.flush()
        add_chunk(
            session,
            document,
            chunk_id="private-chunk",
            version=1,
            content="不允许访客读取的内容",
            content_hash="private-content",
        )
        session.commit()

        results = KnowledgeRetriever(
            session,
            StubIndexer([("private-chunk", 0.05)]),
        ).search("私密资料", min_score=0.5)

    assert results == []
