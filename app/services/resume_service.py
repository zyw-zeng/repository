"""提供固定公开简历的查询、预览和下载能力。"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.schemas.resume import ResumeResource


class ResumeService:
    """隔离简历文件系统路径，避免接口接受任意文件参数。"""

    def __init__(self, settings: Settings | None = None):
        """绑定应用配置中的唯一公开简历。"""
        self.settings = settings or get_settings()

    def get_file(self) -> tuple[Path, ResumeResource, str]:
        """返回经过校验的 PDF、公开信息和轻量缓存标识。"""
        path = self.settings.resume_file_path.resolve()
        if path.suffix.lower() != ".pdf":
            raise AppError(
                "公开简历必须是 PDF 文件",
                status_code=503,
                code="resume_invalid_format",
            )
        if not path.is_file():
            raise AppError(
                "简历暂时不可下载，请稍后再试",
                status_code=404,
                code="resume_not_found",
            )
        stat = path.stat()
        metadata = self._read_metadata()
        resource = ResumeResource(
            title=str(metadata.get("title") or self.settings.resume_title),
            description="包含 AI Agent、RAG、全栈开发与代表项目经历",
            filename=path.name,
            version=str(metadata.get("version") or self.settings.resume_version),
            updated_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            size_bytes=stat.st_size,
            download_url="/api/v1/resume/download",
            preview_url="/api/v1/resume/preview",
        )
        etag = f'"resume-{stat.st_mtime_ns:x}-{stat.st_size:x}"'
        return path, resource, etag

    def get_public_info(self) -> ResumeResource:
        """读取访客和 Agent 可以安全展示的简历元数据。"""
        return self.get_file()[1]

    def replace(self, content: bytes, *, title: str, version: str) -> ResumeResource:
        """校验并原子替换当前 PDF，同时保存可编辑展示信息。"""
        if not content.startswith(b"%PDF-"):
            raise AppError("上传内容不是有效的 PDF", status_code=422, code="resume_invalid_pdf")
        if len(content) > self.settings.resume_max_upload_bytes:
            raise AppError("简历文件超过大小限制", status_code=413, code="resume_too_large")
        normalized_title = title.strip()
        normalized_version = version.strip()
        if not normalized_title or not normalized_version:
            raise AppError(
                "简历标题和版本不能为空",
                status_code=422,
                code="resume_metadata_invalid",
            )

        target = self.settings.resume_file_path.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".uploading.pdf")
        backup = target.with_suffix(".backup.pdf")
        metadata_path = self._metadata_path()
        metadata_temporary = metadata_path.with_suffix(".uploading.json")
        metadata_backup = metadata_path.with_suffix(".backup.json")
        try:
            temporary.write_bytes(content)
            metadata_temporary.write_text(
                json.dumps(
                    {"title": normalized_title, "version": normalized_version},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            # 先备份当前线上文件；PDF 与元数据任一步切换失败时都恢复旧版本。
            backup.unlink(missing_ok=True)
            metadata_backup.unlink(missing_ok=True)
            if target.exists():
                os.replace(target, backup)
            if metadata_path.exists():
                os.replace(metadata_path, metadata_backup)
            os.replace(temporary, target)
            os.replace(metadata_temporary, metadata_path)
        except OSError:
            target.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)
            if backup.exists():
                os.replace(backup, target)
            if metadata_backup.exists():
                os.replace(metadata_backup, metadata_path)
            raise AppError(
                "简历发布失败，原版本已恢复",
                status_code=500,
                code="resume_replace_failed",
            ) from None
        finally:
            temporary.unlink(missing_ok=True)
            metadata_temporary.unlink(missing_ok=True)
            backup.unlink(missing_ok=True)
            metadata_backup.unlink(missing_ok=True)
        return self.get_public_info()

    def _metadata_path(self) -> Path:
        """把简历展示信息保存在 PDF 同目录，便于部署时一起迁移。"""
        return self.settings.resume_file_path.resolve().with_suffix(".json")

    def _read_metadata(self) -> dict[str, str]:
        """元数据损坏时安全退回环境变量，不影响公开简历下载。"""
        path = self._metadata_path()
        if not path.is_file():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
