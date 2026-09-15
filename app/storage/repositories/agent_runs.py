"""实现 Agent 运行记录的持久化操作。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import AgentRun


class AgentRunRepository:
    """保存一次 Agent 执行的状态、步骤和失败原因。"""

    def __init__(self, session: Session):
        """绑定数据库会话。"""
        self.session = session

    def add(self, run: AgentRun) -> AgentRun:
        """新增运行记录并立即生成 ID。"""
        self.session.add(run)
        self.session.flush()
        return run

    def get(self, run_id: str) -> AgentRun | None:
        """按 ID 读取运行记录。"""
        return self.session.get(AgentRun, run_id)

    def get_by_request_id(self, request_id: str) -> AgentRun | None:
        """按请求 ID 查找运行记录，用于阻止重复执行。"""
        return self.session.scalar(select(AgentRun).where(AgentRun.request_id == request_id))

    def finish(
        self,
        run: AgentRun,
        *,
        status: str,
        tool_calls: list[dict],
        duration_ms: int,
        error_message: str | None = None,
    ) -> None:
        """记录最终状态；错误文本限制长度，避免数据库被异常堆栈占满。"""
        run.status = status
        run.tool_calls_json = tool_calls
        run.duration_ms = duration_ms
        run.error_message = error_message[:2000] if error_message else None
        self.session.flush()
