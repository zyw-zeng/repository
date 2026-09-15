"""验证文档上传、索引重建、检索和删除的完整数据一致性流程。"""

from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings
from sqlalchemy.orm import Session, sessionmaker

import app.workers.ingestion as ingestion_worker
from app.core.config import Settings
from app.core.exceptions import AppError
from app.knowledge.indexer import VectorIndexer
from app.knowledge.retriever import KnowledgeRetriever
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.storage.models import DocumentRecord, IngestionJob


class FakeEmbeddings(Embeddings):
    """不访问网络的确定性向量模型，用于验证 Chroma 集成。"""

    @staticmethod
    def _vector(text: str) -> list[float]:
        """从文本长度和字符值生成固定三维向量。"""
        return [float(len(text) or 1), float(sum(map(ord, text)) % 997 or 1), 1.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量生成测试向量。"""
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """生成查询测试向量。"""
        return self._vector(text)


def test_duplicate_upload_is_rejected(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """相同文件内容重复上传时应返回明确冲突。"""
    with session_factory() as session:
        service = DocumentService(session, test_settings)
        service.upload("notes.txt", "中文和 English 内容".encode())

        with pytest.raises(AppError) as error:
            service.upload("copy.txt", "中文和 English 内容".encode())

    assert error.value.status_code == 409
    assert error.value.code == "duplicate_document"


def test_index_reindex_retrieve_and_delete(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """新版本成功前保留旧版本，切换后清理旧版本，最终可完整删除。"""
    monkeypatch.setattr(ingestion_worker, "SessionLocal", session_factory)
    indexer = VectorIndexer(test_settings, embeddings=FakeEmbeddings())

    with session_factory() as session:
        document, first_job = DocumentService(session, test_settings).upload(
            "knowledge.txt",
            "第一版个人知识库内容。\n包含中文与 English。".encode(),
        )
        document_id = document.id
        source_path = Path(document.storage_path)
        first_job_id = first_job.id

    ingestion_worker.run_job_with_retries(
        first_job_id,
        settings=test_settings,
        indexer=indexer,
    )

    with session_factory() as session:
        document = session.get(DocumentRecord, document_id)
        first_job = session.get(IngestionJob, first_job_id)
        assert document is not None
        assert first_job is not None
        assert document.status == "ready"
        assert document.active_index_version == 1
        assert document.chunk_count > 0
        assert first_job.status == "completed"

        DocumentService(session, test_settings).set_visibility(document_id, "public")
        results = KnowledgeRetriever(session, indexer).search("个人知识库", limit=3)
        assert results
        assert results[0].index_version == 1

        source_path.write_text("第二版内容。\n新增可检索信息：双版本索引。", encoding="utf-8")
        _, reindex_job = DocumentService(session, test_settings).request_reindex(document_id)
        reindex_job_id = reindex_job.id

    ingestion_worker.run_job_with_retries(
        reindex_job_id,
        settings=test_settings,
        indexer=indexer,
    )

    with session_factory() as session:
        document = session.get(DocumentRecord, document_id)
        assert document is not None
        assert document.active_index_version == 2
        assert {chunk.index_version for chunk in document.chunks} == {2}
        assert any("第二版" in chunk.content for chunk in document.chunks)
        _, delete_job = DocumentService(session, test_settings).request_delete(document_id)
        delete_job_id = delete_job.id

    ingestion_worker.run_job_with_retries(
        delete_job_id,
        settings=test_settings,
        indexer=indexer,
    )

    with session_factory() as session:
        assert session.get(DocumentRecord, document_id) is None
        delete_job = session.get(IngestionJob, delete_job_id)
        assert delete_job is not None
        assert delete_job.status == "completed"
        assert delete_job.document_id is None
    assert not source_path.exists()


def test_corrupted_document_stops_at_retry_limit(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """损坏文件处理失败后应清理半成品，并在有限次数后停止重试。"""
    monkeypatch.setattr(ingestion_worker, "SessionLocal", session_factory)
    indexer = VectorIndexer(test_settings, embeddings=FakeEmbeddings())
    with session_factory() as session:
        document, job = DocumentService(session, test_settings).upload(
            "broken.pdf", b"not-a-real-pdf"
        )
        document_id = document.id
        job_id = job.id

    ingestion_worker.run_job_with_retries(job_id, settings=test_settings, indexer=indexer)

    with session_factory() as session:
        document = session.get(DocumentRecord, document_id)
        job = session.get(IngestionJob, job_id)
        assert document is not None
        assert job is not None
        assert document.status == "failed"
        assert document.chunks == []
        assert job.status == "failed"
        assert job.attempts == test_settings.ingestion_max_attempts
        assert job.error_message


def test_interrupted_job_returns_to_pending(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """程序中断遗留的运行中任务应在启动恢复时回到等待状态。"""
    with session_factory() as session:
        _, job = DocumentService(session, test_settings).upload("resume.txt", b"resume content")
        job.status = "embedding"
        job.progress = 0.6
        job.attempts = 1
        session.commit()

        recovered = IngestionService(session).recover_interrupted_jobs()
        session.refresh(job)

        assert recovered == 1
        assert job.status == "pending"
        assert job.progress == 0
        assert job.attempts == 1
