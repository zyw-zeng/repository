"""定义公开简历信息和 Agent 下载资源的数据结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ResumeResource(BaseModel):
    """向访客公开的当前简历信息，不包含服务器真实路径。"""

    type: Literal["resume"] = "resume"
    title: str
    description: str
    filename: str
    version: str
    updated_at: datetime
    size_bytes: int
    media_type: Literal["application/pdf"] = "application/pdf"
    download_url: str
    preview_url: str
