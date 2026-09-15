"""实现文档入库任务的持久化和中断恢复查询。"""

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.storage.models import IngestionJob, utc_now

RUNNING_STATUSES = ("parsing", "chunking", "embedding", "deleting")


class IngestionJobRepository:
    """封装任务状态 SQL，事务提交由服务层或 Worker 控制。"""

    def __init__(self, session: Session):
        """绑定一次工作单元使用的数据库会话。"""
        self.session = session

    def add(self, job: IngestionJob) -> IngestionJob:
        """新增任务并立即生成 ID。"""
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: str) -> IngestionJob | None:
        """按照任务 ID 查询任务。"""
        return self.session.get(IngestionJob, job_id)

    def list_recent(
        self,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[IngestionJob]:
        """按创建时间倒序读取持久化任务，可按状态筛选。"""
        statement = select(IngestionJob)
        if status:
            statement = statement.where(IngestionJob.status == status)
        statement = statement.order_by(IngestionJob.created_at.desc()).offset(offset).limit(limit)
        return list(self.session.scalars(statement))

    def get_active_for_document(self, document_id: str) -> IngestionJob | None:
        """查询同一文档尚未结束的任务，避免并发修改索引。"""
        statement = (
            select(IngestionJob)
            .where(
                IngestionJob.document_id == document_id,
                IngestionJob.status.in_(
                    ("pending", "parsing", "chunking", "embedding", "deleting")
                ),
            )
            .order_by(IngestionJob.created_at.desc())
        )
        return self.session.scalar(statement)

    def list_runnable(self, *, max_attempts: int, limit: int = 20) -> list[IngestionJob]:
        """读取等待执行或仍可有限重试的失败任务。"""
        statement = (
            select(IngestionJob)
            .where(
                or_(
                    IngestionJob.status == "pending",
                    (IngestionJob.status == "failed") & (IngestionJob.attempts < max_attempts),
                )
            )
            .order_by(IngestionJob.created_at)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def mark_running(self, job: IngestionJob, status: str, progress: float) -> None:
        """更新已经被当前 Worker 领取的任务步骤。"""
        job.status = status
        job.progress = progress
        job.error_message = None
        self.session.flush()

    def claim(self, job_id: str, *, max_attempts: int, initial_status: str) -> bool:
        """使用条件更新原子领取任务，防止两个 Worker 重复执行。"""
        result = self.session.execute(
            update(IngestionJob)
            .where(
                IngestionJob.id == job_id,
                IngestionJob.status.in_(("pending", "failed")),
                IngestionJob.attempts < max_attempts,
            )
            .values(
                status=initial_status,
                progress=0.05,
                attempts=IngestionJob.attempts + 1,
                started_at=utc_now(),
                finished_at=None,
                error_message=None,
            )
        )
        return (result.rowcount or 0) == 1

    def mark_finished(self, job: IngestionJob, status: str = "completed") -> None:
        """把任务标记为完成。"""
        job.status = status
        job.progress = 1.0
        job.finished_at = utc_now()
        job.error_message = None
        self.session.flush()

    def mark_failed(self, job: IngestionJob, message: str) -> None:
        """记录经过清理后的失败原因，避免把完整堆栈暴露给用户。"""
        job.status = "failed"
        job.error_message = message[:2000]
        job.finished_at = utc_now()
        self.session.flush()

    def recover_interrupted(self) -> int:
        """把进程中断时遗留的运行中任务重新放回等待队列。"""
        result = self.session.execute(
            update(IngestionJob)
            .where(IngestionJob.status.in_(RUNNING_STATUSES))
            .values(status="pending", progress=0.0, started_at=None)
        )
        return result.rowcount or 0
