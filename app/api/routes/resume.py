"""提供公开简历信息、浏览器预览和附件下载接口。"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.api.dependencies import AdminAuthorization
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.schemas.resume import ResumeResource
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/api/v1/resume", tags=["个人简历"])


def _file_response(settings: Settings, disposition: Literal["inline", "attachment"]):
    """构造带缓存标识和 UTF-8 文件名的受控 PDF 响应。"""
    path, resource, etag = ResumeService(settings).get_file()
    return FileResponse(
        path,
        media_type=resource.media_type,
        filename=resource.filename,
        content_disposition_type=disposition,
        headers={
            "Cache-Control": "public, max-age=300, must-revalidate",
            "ETag": etag,
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("", response_model=ResumeResource, summary="读取公开简历信息")
def get_resume_info(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ResumeResource:
    """返回简历名称、版本、大小以及稳定的预览和下载地址。"""
    return ResumeService(settings).get_public_info()


@router.get("/download", summary="下载当前公开简历")
def download_resume(
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    """以附件形式返回当前简历，由浏览器保存为 PDF。"""
    return _file_response(settings, "attachment")


@router.get("/preview", summary="在线预览当前公开简历")
def preview_resume(
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    """以内联形式返回当前简历，交给浏览器 PDF 阅读器显示。"""
    return _file_response(settings, "inline")


@router.put("", response_model=ResumeResource, summary="管理员替换公开简历")
async def replace_resume(
    _: AdminAuthorization,
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(description="新的 PDF 简历。")],
    title: Annotated[str, Form(min_length=2, max_length=120)],
    version: Annotated[str, Form(min_length=1, max_length=30)],
) -> ResumeResource:
    """校验上传内容后原子替换，失败时保留原有公开版本。"""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise AppError("只允许上传 PDF 简历", status_code=422, code="resume_invalid_format")
    content = await file.read(settings.resume_max_upload_bytes + 1)
    return ResumeService(settings).replace(content, title=title, version=version)
