"""提供文档处理任务查询和中断恢复能力。"""

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.storage.models import IngestionJob
from app.storage.repositories.ingestion_jobs import IngestionJobRepository


class IngestionService:
    """向 API 和启动流程暴露任务状态操作。"""

    def __init__(self, session: Session):
        """绑定数据库工作单元。"""
        self.session = session
        self.jobs = IngestionJobRepository(session)

    def get_job(self, job_id: str) -> IngestionJob:
        """读取任务，不存在时返回统一的 404 业务错误。"""
        job = self.jobs.get(job_id)
        if job is None:
            raise AppError("处理任务不存在", status_code=404, code="job_not_found")
        return job

    def list_jobs(
        self,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[IngestionJob]:
        """返回管理端可查看的持久化任务历史。"""
        return self.jobs.list_recent(status=status, offset=offset, limit=limit)

    def recover_interrupted_jobs(self) -> int:
        """把进程中断的任务重新放回等待队列并提交状态。"""
        recovered = self.jobs.recover_interrupted()
        self.session.commit()
        return recovered
