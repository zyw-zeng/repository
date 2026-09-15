"""为每个 HTTP 请求生成请求 ID，并记录建立响应所需时间。"""

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ContextVar 可以在异步请求之间隔离请求 ID，避免并发串号。
request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """接受客户端请求 ID，未提供时自动生成 UUID。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """绑定请求 ID，并输出适合定位慢接口的结构化耗时日志。"""
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            # 对 SSE 而言这里只表示建立流式响应的时间，完整运行耗时仍以 completed 事件为准。
            response.headers["X-Dispatch-Time-Ms"] = str(duration_ms)
            response.headers["Server-Timing"] = f"dispatch;dur={duration_ms}"
            logger.info(
                "HTTP 响应已建立 method=%s path=%s status=%s dispatch_ms=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "HTTP 请求异常 method=%s path=%s dispatch_ms=%s",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        finally:
            # 无论业务是否抛出异常，都恢复上下文，防止影响后续请求。
            request_id_context.reset(token)
