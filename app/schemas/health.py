"""健康检查接口的响应结构。"""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """应用存活检查响应。"""

    status: Literal["ok"]
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """应用依赖就绪检查响应。"""

    status: Literal["ready"]
    database: Literal["ok"]
    document_store: Literal["ok"]
    vector_store: Literal["ok"]
