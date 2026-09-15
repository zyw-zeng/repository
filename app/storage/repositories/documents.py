"""实现文档和权威切片正文的持久化操作。"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.knowledge.types import ChunkDraft
from app.storage.models import DocumentChunk, DocumentRecord


class DocumentRepository:
    """封装文档相关 SQL，事务提交由服务层统一控制。"""

    def __init__(self, session: Session):
        """绑定一次工作单元使用的数据库会话。"""
        self.session = session

    def get(self, document_id: str) -> DocumentRecord | None:
        """按照文档 ID 查询单个文档。"""
        return self.session.get(DocumentRecord, document_id)

    def get_by_hash(self, file_hash: str) -> DocumentRecord | None:
        """按照文件哈希查找已经上传的相同内容。"""
        statement = select(DocumentRecord).where(DocumentRecord.file_hash == file_hash)
        return self.session.scalar(statement)

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        public_only: bool = False,
    ) -> list[DocumentRecord]:
        """按照创建时间倒序分页查询文档，可限制为访客公开范围。"""
        statement = select(DocumentRecord)
        if public_only:
            statement = statement.where(DocumentRecord.visibility == "public")
        statement = statement.order_by(DocumentRecord.created_at.desc()).offset(offset).limit(limit)
        return list(self.session.scalars(statement))

    def add(self, document: DocumentRecord) -> DocumentRecord:
        """新增文档并立即生成默认字段。"""
        self.session.add(document)
        self.session.flush()
        return document

    def add_chunks(
        self,
        *,
        document_id: str,
        index_version: int,
        chunks: Sequence[ChunkDraft],
        vector_ids: Sequence[str],
    ) -> list[DocumentChunk]:
        """批量保存某个索引版本的权威切片正文。"""
        records = [
            DocumentChunk(
                id=vector_id,
                document_id=document_id,
                index_version=index_version,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                heading=chunk.heading,
                content=chunk.content,
                content_hash=chunk.content_hash,
                token_count=chunk.token_count,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                metadata_json=chunk.metadata,
                vector_id=vector_id,
            )
            for chunk, vector_id in zip(chunks, vector_ids, strict=True)
        ]
        self.session.add_all(records)
        self.session.flush()
        return records

    def get_chunks_for_version(
        self, document_id: str, index_version: int
    ) -> list[DocumentChunk]:
        """读取指定文档版本的全部切片。"""
        statement = select(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.index_version == index_version,
        )
        return list(self.session.scalars(statement))

    def get_all_chunks(self, document_id: str) -> list[DocumentChunk]:
        """读取文档的所有索引版本，主要用于删除和旧版本清理。"""
        statement = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        return list(self.session.scalars(statement))

    def get_inactive_chunks(
        self, document_id: str, active_index_version: int
    ) -> list[DocumentChunk]:
        """读取不属于当前活动索引版本的历史切片。"""
        statement = select(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.index_version != active_index_version,
        )
        return list(self.session.scalars(statement))

    def get_active_chunks_by_ids(
        self,
        chunk_ids: Sequence[str],
        *,
        document_ids: Sequence[str] = (),
        filenames: Sequence[str] = (),
        public_only: bool = True,
    ) -> list[DocumentChunk]:
        """只返回属于文档当前活动版本的切片，过滤残缺或过期索引。"""
        if not chunk_ids:
            return []
        statement = (
            select(DocumentChunk)
            .join(DocumentRecord, DocumentRecord.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.id.in_(chunk_ids),
                DocumentRecord.status == "ready",
                DocumentChunk.index_version == DocumentRecord.active_index_version,
            )
        )
        # 访客问答的最终安全边界在 SQLite；不能信任可能过期的向量元数据。
        if public_only:
            statement = statement.where(DocumentRecord.visibility == "public")
        # 即使 Chroma 已过滤一次，SQLite 仍再次执行过滤，防止索引元数据过期。
        if document_ids:
            statement = statement.where(DocumentRecord.id.in_(document_ids))
        if filenames:
            statement = statement.where(DocumentRecord.filename.in_(filenames))
        records = list(self.session.scalars(statement))
        positions = {chunk_id: index for index, chunk_id in enumerate(chunk_ids)}
        return sorted(records, key=lambda record: positions.get(record.id, len(positions)))

    def get_verified_active_chunks(
        self,
        chunk_ids: Sequence[str],
        *,
        public_only: bool = True,
    ) -> list[DocumentChunk]:
        """按引用 ID 重读权威正文，并确保切片属于允许公开的活动版本。"""
        return self.get_active_chunks_by_ids(chunk_ids, public_only=public_only)

    def search_active_chunks_by_terms(
        self,
        terms: Sequence[str],
        *,
        limit: int = 10,
        public_only: bool = True,
    ) -> list[DocumentChunk]:
        """使用 SQLite 关键词补充技术名词召回，并保持活动版本和公开范围约束。"""
        normalized_terms = list(dict.fromkeys(term.strip() for term in terms if term.strip()))[:12]
        if not normalized_terms:
            return []
        clauses = [DocumentChunk.content.ilike(f"%{term}%") for term in normalized_terms]
        statement = (
            select(DocumentChunk)
            .join(DocumentRecord, DocumentRecord.id == DocumentChunk.document_id)
            .where(
                DocumentRecord.status == "ready",
                DocumentChunk.index_version == DocumentRecord.active_index_version,
                or_(*clauses),
            )
        )
        if public_only:
            statement = statement.where(DocumentRecord.visibility == "public")
        return list(self.session.scalars(statement.limit(max(1, limit))))

    def delete_chunks_for_version(self, document_id: str, index_version: int) -> None:
        """删除指定索引版本的关系数据库切片。"""
        self.session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.index_version == index_version,
            )
        )

    def delete_inactive_chunks(self, document_id: str, active_index_version: int) -> None:
        """删除切换完成后不再活动的历史切片。"""
        self.session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.index_version != active_index_version,
            )
        )

    def delete(self, document: DocumentRecord) -> None:
        """删除文档，数据库外键会级联删除其切片。"""
        self.session.delete(document)
