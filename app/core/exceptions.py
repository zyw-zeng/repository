"""定义应用异常以及统一的 HTTP 错误响应格式。"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """可安全返回给 API 调用方的业务异常。"""

    def __init__(self, message: str, *, status_code: int = 400, code: str = "app_error"):
        """保存公开错误消息、HTTP 状态码和稳定错误代码。"""
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def register_exception_handlers(app: FastAPI) -> None:
    """将业务异常转换为稳定的 JSON 错误结构。"""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        """隐藏内部堆栈，只返回错误代码和可读消息。"""
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
