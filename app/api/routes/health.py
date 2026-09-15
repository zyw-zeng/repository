"""提供不产生模型费用的存活与就绪检查。"""

import os

import chromadb
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.config import get_settings
from app.schemas.health import HealthResponse, ReadinessResponse
from app.storage.database import engine

router = APIRouter(tags=["系统"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="检查应用是否存活",
    response_description="应用名称、版本和存活状态。",
)
def health() -> HealthResponse:
    """确认 Web 进程能够正常响应请求。"""
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, version=settings.app_version)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="检查本地依赖是否就绪",
    description="检查 SQLite、原始文档目录和 Chroma，不会调用远程模型或产生费用。",
    response_description="数据库、文档目录和向量库的就绪状态。",
)
def readiness() -> ReadinessResponse:
    """确认数据库、文档目录和 Chroma 可用，不调用远程模型。"""
    settings = get_settings()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        if not settings.documents_path.is_dir() or not os.access(settings.documents_path, os.W_OK):
            raise OSError("文档目录不可写")
        chromadb.PersistentClient(path=str(settings.chroma_path)).heartbeat()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="应用依赖尚未就绪",
        ) from exc

    return ReadinessResponse(
        status="ready",
        database="ok",
        document_store="ok",
        vector_store="ok",
    )
