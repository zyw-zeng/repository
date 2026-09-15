"""文档入库任务状态查询接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import DatabaseSession, require_admin
from app.schemas.documents import JobListResponse, JobResponse
from app.schemas.errors import ErrorResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(
    prefix="/api/v1/ingestion-jobs",
    tags=["文档任务"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=JobListResponse, summary="分页列出文档处理任务")
def list_ingestion_jobs(
    session: DatabaseSession,
    status: str | None = Query(default=None, max_length=30, description="可选任务状态。"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> JobListResponse:
    """返回刷新页面后仍可查看的任务历史和运行状态。"""
    items = IngestionService(session).list_jobs(status=status, offset=offset, limit=limit)
    return JobListResponse(items=items, offset=offset, limit=limit)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="查询文档处理任务",
    description="前端可定时调用此接口，直到状态变为 completed 或 failed。",
    responses={404: {"model": ErrorResponse, "description": "任务不存在。"}},
)
def get_ingestion_job(
    job_id: Annotated[str, Path(description="文档操作返回的任务 ID。")],
    session: DatabaseSession,
) -> JobResponse:
    """返回任务步骤、进度、尝试次数和失败原因。"""
    return JobResponse.model_validate(IngestionService(session).get_job(job_id))
