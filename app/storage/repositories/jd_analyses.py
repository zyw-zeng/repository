"""提供 JD 岗位匹配记录的持久化访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import JdAnalysis


class JdAnalysisRepository:
    """封装 JD 分析的创建、查询和更新。"""

    def __init__(self, session: Session):
        self.session = session

    def add(self, analysis: JdAnalysis) -> JdAnalysis:
        """新增分析并立即加入当前工作单元。"""
        self.session.add(analysis)
        self.session.flush()
        return analysis

    def get(self, analysis_id: str) -> JdAnalysis | None:
        """按公开 ID 查找分析。"""
        return self.session.get(JdAnalysis, analysis_id)

    def get_by_request_id(self, request_id: str) -> JdAnalysis | None:
        """按幂等请求 ID 查找分析。"""
        return self.session.scalar(
            select(JdAnalysis).where(JdAnalysis.request_id == request_id)
        )
