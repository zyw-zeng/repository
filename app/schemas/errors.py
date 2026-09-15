"""统一业务错误响应的 OpenAPI 数据结构。"""

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """稳定错误代码和可直接展示的中文消息。"""

    code: str = Field(description="供程序判断错误类型的稳定代码。", examples=["document_not_found"])
    message: str = Field(description="适合向用户展示的错误消息。", examples=["文档不存在"])


class ErrorResponse(BaseModel):
    """所有业务异常采用的统一外层结构。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {"code": "document_not_found", "message": "文档不存在"}
            }
        }
    )

    error: ErrorDetail
