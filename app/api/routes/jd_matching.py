"""提供 JD 岗位匹配的普通、SSE、查询和取消接口。"""

import json
import logging
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue
from threading import Event, Lock
from typing import Annotated

from fastapi import APIRouter, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import DatabaseSession
from app.core.exceptions import AppError
from app.core.middleware import request_id_context
from app.schemas.jd_matching import (
    JdAnalysisRequest,
    JdAnalysisResponse,
    JdCancellationResponse,
)
from app.services.jd_matching_service import JdMatchingService

router = APIRouter(prefix="/api/v1/jd-analyses", tags=["岗位匹配"])
logger = logging.getLogger(__name__)
_active_lock = Lock()
_active_runs: dict[str, Event] = {}


def _sse(event: str, data: object) -> str:
    """编码一个不会被 Nginx 缓冲的 SSE 事件。"""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("", response_model=JdAnalysisResponse, summary="分析粘贴的岗位 JD")
def analyze_jd(request: JdAnalysisRequest, session: DatabaseSession) -> JdAnalysisResponse:
    """同步执行岗位匹配，适合 Swagger 调试和非流式客户端。"""
    return JdMatchingService(session).run(
        request.jd_text,
        request_id_context.get(),
        conversation_id=request.conversation_id,
    )


@router.get("/{analysis_id}", response_model=JdAnalysisResponse, summary="读取岗位匹配报告")
def get_jd_analysis(
    analysis_id: Annotated[str, Path(description="JD 分析 ID。")],
    session: DatabaseSession,
) -> JdAnalysisResponse:
    """返回刷新页面后仍可恢复的结构化报告。"""
    return JdMatchingService(session).get(analysis_id)


@router.post("/stream", summary="流式分析粘贴的岗位 JD")
def stream_jd_analysis(
    request: JdAnalysisRequest,
    session: DatabaseSession,
) -> StreamingResponse:
    """持续发送解析、逐项检索、评价和最终报告事件。"""
    request_id = request_id_context.get()
    with _active_lock:
        if request_id in _active_runs:
            raise AppError("该 JD 请求正在执行", status_code=409, code="duplicate_request")
        cancellation = Event()
        _active_runs[request_id] = cancellation
    worker_factory = sessionmaker(
        bind=session.get_bind(), autoflush=False, expire_on_commit=False
    )

    def generate() -> Iterator[str]:
        """把工作线程事件转发到浏览器，并在空闲时发送心跳。"""
        yield _sse("analysis_started", {"request_id": request_id})
        events: Queue[tuple[str, object]] = Queue(maxsize=256)
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="jd-matching")

        def execute() -> JdAnalysisResponse:
            """使用线程独立数据库会话运行 LangGraph。"""
            try:
                with worker_factory() as worker_session:
                    return JdMatchingService(worker_session).run(
                        request.jd_text,
                        request_id,
                        conversation_id=request.conversation_id,
                        publish=lambda event, data: events.put((event, data)),
                        is_cancelled=cancellation.is_set,
                    )
            finally:
                with _active_lock:
                    _active_runs.pop(request_id, None)

        future = executor.submit(execute)
        heartbeat_at = time.monotonic() + 10
        try:
            while not future.done() or not events.empty():
                try:
                    event, data = events.get(timeout=0.2)
                    yield _sse(event, data)
                except Empty:
                    if time.monotonic() >= heartbeat_at:
                        yield _sse("heartbeat", {"request_id": request_id})
                        heartbeat_at = time.monotonic() + 10
            report = future.result()
            if report.status == "cancelled":
                yield _sse("cancelled", {"request_id": request_id, "analysis_id": report.id})
                return
            yield _sse("report_ready", report.model_dump(mode="json"))
            yield _sse(
                "completed",
                {
                    "request_id": request_id,
                    "analysis_id": report.id,
                    "duration_ms": report.duration_ms,
                },
            )
        except Exception:
            logger.exception("JD 岗位匹配流执行失败", extra={"request_id": request_id})
            yield _sse(
                "error",
                {"request_id": request_id, "message": "岗位匹配暂时失败，请稍后重试。"},
            )
        finally:
            cancellation.set()
            executor.shutdown(wait=False, cancel_futures=True)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/runs/{request_id}/cancel",
    response_model=JdCancellationResponse,
    summary="取消正在执行的岗位匹配",
)
def cancel_jd_analysis(
    request_id: Annotated[str, Path(description="前端提交的请求 ID。")],
) -> JdCancellationResponse:
    """向真实后端任务发送取消信号。"""
    with _active_lock:
        cancellation = _active_runs.get(request_id)
        if cancellation is None:
            raise AppError("JD 分析不在运行", status_code=404, code="jd_run_not_found")
        cancellation.set()
    return JdCancellationResponse(request_id=request_id)
