"""管理文档上传、查询、重建索引和删除等生命周期操作。"""

import hashlib
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.knowledge.loaders import SUPPORTED_EXTENSIONS
from app.storage.models import DocumentRecord, IngestionJob, new_id
from app.storage.repositories.documents import DocumentRepository
from app.storage.repositories.ingestion_jobs import IngestionJobRepository


class DocumentService:
    """协调受控文件存储和数据库记录，不直接操作向量库。"""

    def __init__(self, session: Session, settings: Settings | None = None):
        """绑定数据库工作单元和应用配置。"""
        self.session = session
        self.settings = settings or get_settings()
        self.documents = DocumentRepository(session)
        self.jobs = IngestionJobRepository(session)

    def upload(self, filename: str, content: bytes) -> tuple[DocumentRecord, IngestionJob]:
        """校验并保存原始文件，同时创建持久化索引任务。"""
        # 同时处理浏览器可能上传的 Unix 或 Windows 风格路径。
        safe_filename = Path(filename.replace("\\", "/")).name.strip()
        suffix = Path(safe_filename).suffix.lower()
        if not safe_filename or suffix not in SUPPORTED_EXTENSIONS:
            raise AppError("仅支持 PDF、Markdown、TXT 和 DOCX 文件", code="unsupported_file")
        if len(safe_filename) > self.settings.max_filename_length:
            raise AppError("文件名过长", code="filename_too_long")
        if not content:
            raise AppError("不能上传空文件", code="empty_file")
        if len(content) > self.settings.max_upload_bytes:
            raise AppError(
                f"文件不能超过 {self.settings.max_upload_bytes // 1024 // 1024} MB",
                status_code=413,
                code="file_too_large",
            )

        file_hash = hashlib.sha256(content).hexdigest()
        duplicate = self.documents.get_by_hash(file_hash)
        if duplicate is not None:
            raise AppError(
                f"相同文件已存在，文档 ID: {duplicate.id}",
                status_code=409,
                code="duplicate_document",
            )

        document_id = new_id()
        destination = self.settings.documents_path.resolve() / f"{document_id}{suffix}"
        temporary = destination.with_suffix(f"{suffix}.uploading")
        self.settings.documents_path.mkdir(parents=True, exist_ok=True)

        try:
            # 先写临时文件，再原子替换，避免中断后留下看似完整的半文件。
            temporary.write_bytes(content)
            temporary.replace(destination)
            document = self.documents.add(
                DocumentRecord(
                    id=document_id,
                    filename=safe_filename,
                    file_hash=file_hash,
                    file_type=suffix.lstrip("."),
                    storage_path=str(destination),
                    status="pending",
                    size_bytes=len(content),
                    visibility="private",
                )
            )
            job = self.jobs.add(
                IngestionJob(
                    document_id=document.id,
                    operation="index",
                    target_index_version=1,
                    status="pending",
                )
            )
            self.session.commit()
            return document, job
        except IntegrityError as exc:
            self.session.rollback()
            temporary.unlink(missing_ok=True)
            destination.unlink(missing_ok=True)
            raise AppError(
                "相同文件已被其他请求上传",
                status_code=409,
                code="duplicate_document",
            ) from exc
        except Exception:
            self.session.rollback()
            # 数据库写入失败时删除本次刚保存的文件，不影响任何既有文档。
            temporary.unlink(missing_ok=True)
            destination.unlink(missing_ok=True)
            raise

    def list_documents(self, *, offset: int = 0, limit: int = 50) -> list[DocumentRecord]:
        """分页读取文档，限制单次返回数量。"""
        return self.documents.list(offset=max(0, offset), limit=min(max(1, limit), 100))

    def get_document(self, document_id: str) -> DocumentRecord:
        """读取文档，不存在时返回统一的 404 业务错误。"""
        document = self.documents.get(document_id)
        if document is None:
            raise AppError("文档不存在", status_code=404, code="document_not_found")
        return document

    def set_visibility(self, document_id: str, visibility: str) -> DocumentRecord:
        """切换文档公开范围；向量无需重建，检索会在 SQLite 再次校验。"""
        if visibility not in {"public", "private"}:
            raise AppError("文档公开范围无效", code="invalid_visibility")
        document = self.get_document(document_id)
        document.visibility = visibility
        self.session.commit()
        return document

    def request_reindex(self, document_id: str) -> tuple[DocumentRecord, IngestionJob]:
        """为文档创建下一版本索引任务，旧活动版本继续提供查询。"""
        document = self.get_document(document_id)
        if self.jobs.get_active_for_document(document.id) is not None:
            raise AppError("该文档已有任务正在执行", status_code=409, code="job_in_progress")
        if not Path(document.storage_path).is_file():
            raise AppError("原始文件不存在，无法重新索引", status_code=409, code="source_missing")

        job = self.jobs.add(
            IngestionJob(
                document_id=document.id,
                operation="reindex",
                target_index_version=max(1, document.active_index_version + 1),
                status="pending",
            )
        )
        self.session.commit()
        return document, job

    def request_delete(self, document_id: str) -> tuple[DocumentRecord, IngestionJob]:
        """把文档标记为删除中，并创建可恢复的删除任务。"""
        document = self.get_document(document_id)
        if self.jobs.get_active_for_document(document.id) is not None:
            raise AppError("该文档已有任务正在执行", status_code=409, code="job_in_progress")

        document.status = "deleting"
        job = self.jobs.add(
            IngestionJob(
                document_id=document.id,
                operation="delete",
                target_index_version=document.active_index_version,
                status="pending",
            )
        )
        self.session.commit()
        return document, job
