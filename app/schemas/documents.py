"""文档管理接口的请求和响应结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """对外展示的文档状态和活动索引信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    status: str
    size_bytes: int
    chunk_count: int
    active_index_version: int
    visibility: Literal["public", "private"]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """分页文档列表。"""

    items: list[DocumentResponse]
    offset: int
    limit: int


class JobResponse(BaseModel):
    """文档处理任务的当前状态。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str | None
    operation: str
    target_index_version: int
    status: str
    progress: float = Field(ge=0, le=1)
    attempts: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class JobListResponse(BaseModel):
    """管理端任务中心使用的分页任务列表。"""

    items: list[JobResponse]
    offset: int
    limit: int


class DocumentAcceptedResponse(BaseModel):
    """文档操作成功进入后台队列后的响应。"""

    document: DocumentResponse
    job: JobResponse


class DocumentVisibilityRequest(BaseModel):
    """修改文档访客可见范围的请求。"""

    visibility: Literal["public", "private"] = Field(description="文档公开范围。")
