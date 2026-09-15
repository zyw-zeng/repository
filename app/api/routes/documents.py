"""文档上传、查询、重建索引和删除接口。"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Path, Query, UploadFile, status

from app.api.dependencies import DatabaseSession, require_admin
from app.core.config import get_settings
from app.schemas.documents import (
    DocumentAcceptedResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentVisibilityRequest,
)
from app.schemas.errors import ErrorResponse
from app.services.document_service import DocumentService
from app.workers.ingestion import run_job_with_retries

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["文档管理"],
    dependencies=[Depends(require_admin)],
)


@router.post(
    "",
    response_model=DocumentAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="上传文档并创建索引任务",
    description=(
        "支持 PDF、Markdown、TXT 和 DOCX。上传成功后返回文档与任务，"
        "客户端应使用任务 ID 查询进度。"
    ),
    response_description="已保存的文档和等待执行的后台任务。",
    responses={
        400: {"model": ErrorResponse, "description": "文件为空、格式不支持或文件名不合法。"},
        409: {"model": ErrorResponse, "description": "相同内容的文档已经存在。"},
        413: {"model": ErrorResponse, "description": "文件超过配置的大小限制。"},
    },
)
async def upload_document(
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
    file: Annotated[
        UploadFile,
        File(description="需要导入的 PDF、Markdown、TXT 或 DOCX 文件。"),
    ],
) -> DocumentAcceptedResponse:
    """接收文件并创建持久化索引任务，实际解析在后台执行。"""
    # 最多只多读一个字节用于判断超限，避免超大请求完整进入应用内存。
    content = await file.read(get_settings().max_upload_bytes + 1)
    document, job = DocumentService(session).upload(file.filename or "", content)
    background_tasks.add_task(run_job_with_retries, job.id)
    return DocumentAcceptedResponse(document=document, job=job)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="分页获取文档列表",
    response_description="文档列表及本次分页参数。",
)
def list_documents(
    session: DatabaseSession,
    offset: int = Query(default=0, ge=0, description="从第几条文档开始读取。"),
    limit: int = Query(default=50, ge=1, le=100, description="本次最多返回多少条文档。"),
) -> DocumentListResponse:
    """分页返回已上传文档及其处理状态。"""
    documents = DocumentService(session).list_documents(offset=offset, limit=limit)
    return DocumentListResponse(items=documents, offset=offset, limit=limit)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="获取文档详情",
    responses={404: {"model": ErrorResponse, "description": "文档不存在。"}},
)
def get_document(
    document_id: Annotated[str, Path(description="上传文档时返回的文档 ID。")],
    session: DatabaseSession,
) -> DocumentResponse:
    """返回指定文档的状态和活动索引版本。"""
    return DocumentResponse.model_validate(DocumentService(session).get_document(document_id))


@router.patch(
    "/{document_id}/visibility",
    response_model=DocumentResponse,
    summary="修改文档公开范围",
    description="只有 public 文档会进入访客知识问答和 Agent 工具结果。",
    responses={404: {"model": ErrorResponse, "description": "文档不存在。"}},
)
def update_document_visibility(
    document_id: Annotated[str, Path(description="需要修改公开范围的文档 ID。")],
    request: DocumentVisibilityRequest,
    session: DatabaseSession,
) -> DocumentResponse:
    """由管理员明确决定文档是否允许访客检索。"""
    document = DocumentService(session).set_visibility(document_id, request.visibility)
    return DocumentResponse.model_validate(document)


@router.post(
    "/{document_id}/reindex",
    response_model=DocumentAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建文档重新索引任务",
    description="新索引全部成功前继续使用旧活动版本，避免重建失败影响查询。",
    responses={
        404: {"model": ErrorResponse, "description": "文档不存在。"},
        409: {"model": ErrorResponse, "description": "已有任务执行中或原始文件丢失。"},
    },
)
def reindex_document(
    document_id: Annotated[str, Path(description="需要重新索引的文档 ID。")],
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
) -> DocumentAcceptedResponse:
    """创建双版本重建任务，成功切换前继续使用旧索引。"""
    document, job = DocumentService(session).request_reindex(document_id)
    background_tasks.add_task(run_job_with_retries, job.id)
    return DocumentAcceptedResponse(document=document, job=job)


@router.delete(
    "/{document_id}",
    response_model=DocumentAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建文档删除任务",
    description="后台依次删除向量、原始文件和数据库记录，操作可以在中断后恢复。",
    responses={
        404: {"model": ErrorResponse, "description": "文档不存在。"},
        409: {"model": ErrorResponse, "description": "该文档已有任务正在执行。"},
    },
)
def delete_document(
    document_id: Annotated[str, Path(description="需要删除的文档 ID。")],
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
) -> DocumentAcceptedResponse:
    """创建可恢复的文档删除任务。"""
    document, job = DocumentService(session).request_delete(document_id)
    background_tasks.add_task(run_job_with_retries, job.id)
    return DocumentAcceptedResponse(document=document, job=job)
