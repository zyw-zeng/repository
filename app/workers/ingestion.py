"""执行可恢复、可有限重试的文档索引与删除任务。"""

import logging
from pathlib import Path

from app.core.config import Settings, get_settings
from app.knowledge.indexer import VectorIndexer
from app.knowledge.loaders import load_document
from app.knowledge.splitter import split_document
from app.storage.database import SessionLocal
from app.storage.repositories.documents import DocumentRepository
from app.storage.repositories.ingestion_jobs import IngestionJobRepository

logger = logging.getLogger(__name__)


def _process_index_job(
    job_id: str,
    *,
    settings: Settings,
    indexer: VectorIndexer | None,
) -> None:
    """解析文档并构建新版本，全部成功后再切换活动版本。"""
    current_indexer = indexer
    document_id: str | None = None
    target_version = 0

    with SessionLocal() as session:
        documents = DocumentRepository(session)
        jobs = IngestionJobRepository(session)
        job = jobs.get(job_id)
        if job is None or job.status == "completed":
            return
        if not jobs.claim(
            job_id,
            max_attempts=settings.ingestion_max_attempts,
            initial_status="parsing",
        ):
            session.rollback()
            return
        session.commit()
        job = jobs.get(job_id)
        if job is None:
            return
        document = job.document
        if document is None:
            jobs.mark_failed(job, "任务关联的文档不存在")
            session.commit()
            return

        document_id = document.id
        target_version = job.target_index_version
        try:
            jobs.mark_running(job, "parsing", 0.1)
            if document.active_index_version == 0:
                document.status = "processing"
            session.commit()

            loaded = load_document(Path(document.storage_path))
            jobs.mark_running(job, "chunking", 0.35)
            session.commit()

            chunks = split_document(
                loaded,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )

            # 重试前清理相同目标版本，upsert 和数据库写入均保持幂等。
            documents.delete_chunks_for_version(document.id, target_version)
            session.commit()

            jobs.mark_running(job, "embedding", 0.6)
            session.commit()
            current_indexer = current_indexer or VectorIndexer(settings)
            current_indexer.delete_document_version(document.id, target_version)
            vector_ids = current_indexer.upsert_chunks(
                document_id=document.id,
                filename=document.filename,
                index_version=target_version,
                chunks=chunks,
            )

            # 向量全部成功后，在同一个数据库事务中保存正文并切换活动版本。
            documents.add_chunks(
                document_id=document.id,
                index_version=target_version,
                chunks=chunks,
                vector_ids=vector_ids,
            )
            document.active_index_version = target_version
            document.chunk_count = len(chunks)
            document.status = "ready"
            document.error_message = None
            jobs.mark_finished(job)
            session.commit()

            # 旧版本即使暂时清理失败也不会被检索，因此不回滚已成功的新版本。
            inactive_chunks = documents.get_inactive_chunks(document.id, target_version)
            try:
                current_indexer.delete_vectors([chunk.vector_id for chunk in inactive_chunks])
                documents.delete_inactive_chunks(document.id, target_version)
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("清理文档 %s 的历史索引失败，将保留为不可检索数据", document.id)
        except Exception as exc:
            session.rollback()
            logger.exception("文档索引任务 %s 执行失败", job_id)

            # 新版本尚未激活时可以安全清理，不影响已有活动版本。
            if current_indexer is not None and document_id is not None:
                try:
                    current_indexer.delete_document_version(document_id, target_version)
                except Exception:
                    logger.exception("清理失败任务 %s 的残缺向量失败", job_id)

            job = jobs.get(job_id)
            if job is None:
                return
            documents.delete_chunks_for_version(document_id, target_version)
            document = documents.get(document_id)
            if document is not None:
                if document.active_index_version == 0:
                    document.status = "failed"
                document.error_message = str(exc)[:2000]
            jobs.mark_failed(job, str(exc) or "文档处理失败")
            session.commit()


def _process_delete_job(
    job_id: str,
    *,
    settings: Settings,
    indexer: VectorIndexer | None,
) -> None:
    """按向量、文件、数据库顺序幂等删除文档。"""
    with SessionLocal() as session:
        documents = DocumentRepository(session)
        jobs = IngestionJobRepository(session)
        job = jobs.get(job_id)
        if job is None or job.status == "completed":
            return
        if not jobs.claim(
            job_id,
            max_attempts=settings.ingestion_max_attempts,
            initial_status="deleting",
        ):
            session.rollback()
            return
        session.commit()
        job = jobs.get(job_id)
        if job is None:
            return
        document = job.document
        if document is None:
            jobs.mark_finished(job)
            session.commit()
            return

        try:
            jobs.mark_running(job, "deleting", 0.2)
            document.status = "deleting"
            session.commit()

            current_indexer = indexer or VectorIndexer(settings)
            chunks = documents.get_all_chunks(document.id)
            current_indexer.delete_vectors([chunk.vector_id for chunk in chunks])
            job.progress = 0.6
            session.commit()

            Path(document.storage_path).unlink(missing_ok=True)
            job.document = None
            documents.delete(document)
            jobs.mark_finished(job)
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.exception("文档删除任务 %s 执行失败", job_id)
            job = jobs.get(job_id)
            if job is not None:
                jobs.mark_failed(job, str(exc) or "文档删除失败")
                session.commit()


def run_ingestion_job(
    job_id: str,
    *,
    settings: Settings | None = None,
    indexer: VectorIndexer | None = None,
) -> None:
    """读取任务类型并执行一次处理尝试。"""
    resolved_settings = settings or get_settings()
    with SessionLocal() as session:
        job = IngestionJobRepository(session).get(job_id)
        if job is None or job.status == "completed":
            return
        operation = job.operation

    if operation == "delete":
        _process_delete_job(job_id, settings=resolved_settings, indexer=indexer)
    else:
        _process_index_job(job_id, settings=resolved_settings, indexer=indexer)


def run_job_with_retries(
    job_id: str,
    *,
    settings: Settings | None = None,
    indexer: VectorIndexer | None = None,
) -> None:
    """对瞬时失败进行有限重试，达到上限后保留失败状态。"""
    resolved_settings = settings or get_settings()
    while True:
        with SessionLocal() as session:
            job = IngestionJobRepository(session).get(job_id)
            if job is None or job.status == "completed":
                return
            # 运行中状态说明任务已被其他 Worker 原子领取，当前调用直接退出。
            if job.status not in {"pending", "failed"}:
                return
            if job.attempts >= resolved_settings.ingestion_max_attempts:
                return
        run_ingestion_job(job_id, settings=resolved_settings, indexer=indexer)


def recover_and_run_pending_jobs(settings: Settings | None = None) -> int:
    """恢复中断任务，并同步处理当前所有可运行任务。"""
    resolved_settings = settings or get_settings()
    with SessionLocal() as session:
        jobs = IngestionJobRepository(session)
        jobs.recover_interrupted()
        session.commit()
        candidates = jobs.list_runnable(
            max_attempts=resolved_settings.ingestion_max_attempts,
            limit=100,
        )
        # 没有模型密钥时仍可恢复删除任务，但暂不消耗索引任务的重试次数。
        job_ids = [
            job.id
            for job in candidates
            if job.operation == "delete" or bool(resolved_settings.dashscope_api_key)
        ]

    for job_id in job_ids:
        run_job_with_retries(job_id, settings=resolved_settings)
    return len(job_ids)
