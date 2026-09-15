"""提供 LangGraph Agent 的会话、管理和流式消息接口。"""

import json
import logging
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from dataclasses import asdict
from queue import Empty, Full, Queue
from threading import Event, Lock
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import sessionmaker

from app.agent.runtime import AgentCancelledError, bind_agent_runtime
from app.api.dependencies import AdminAuthorization, AppSettings, DatabaseSession
from app.core.exceptions import AppError
from app.core.middleware import request_id_context
from app.knowledge.types import SearchFilters
from app.schemas.agent import (
    AgentCancellationResponse,
    AgentExecutionResponse,
    AgentMessageRequest,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
)
from app.schemas.errors import ErrorResponse
from app.services.agent_service import AgentService
from app.services.suggestion_service import SuggestionService

router = APIRouter(prefix="/api/v1/conversations", tags=["Agent"])
logger = logging.getLogger(__name__)

# 长时间没有字节传输时，开发代理或网关可能主动断开 SSE；心跳必须短于常见的 30 秒空闲限制。
SSE_HEARTBEAT_INTERVAL_SECONDS = 10.0

# 单进程 MVP 使用请求 ID 定位正在运行的任务；独立 Worker 部署后可替换为共享取消存储。
_active_run_lock = Lock()
_active_runs: dict[str, tuple[str, Event]] = {}


def _register_active_run(conversation_id: str, request_id: str) -> Event:
    """登记运行并返回可由取消接口设置的线程安全事件。"""
    with _active_run_lock:
        existing = _active_runs.get(request_id)
        if existing is not None:
            raise AppError("该请求正在执行", status_code=409, code="duplicate_request")
        cancellation = Event()
        _active_runs[request_id] = (conversation_id, cancellation)
        return cancellation


def _release_active_run(request_id: str, cancellation: Event) -> None:
    """只清理仍指向本次运行的登记，避免误删后续同名状态。"""
    with _active_run_lock:
        existing = _active_runs.get(request_id)
        if existing is not None and existing[1] is cancellation:
            _active_runs.pop(request_id, None)


def _cancel_active_run(conversation_id: str, request_id: str) -> bool:
    """设置匹配会话的取消信号，不允许跨会话停止其他运行。"""
    with _active_run_lock:
        existing = _active_runs.get(request_id)
        if existing is None or existing[0] != conversation_id:
            return False
        existing[1].set()
        return True


def _server_sent_event(event: str, data: object) -> str:
    """把结构化数据编码为浏览器可消费的 SSE 事件。"""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建 Agent 会话",
)
def create_conversation(
    request: CreateConversationRequest,
    session: DatabaseSession,
) -> ConversationResponse:
    """创建可持久化消息和运行轨迹的会话。"""
    service = AgentService(session)
    conversation = service.create_conversation(request.title)
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        active_jd_analysis_id=conversation.active_jd_analysis_id,
        candidate_profile_version=conversation.candidate_profile_version,
        career_context_updated_at=conversation.career_context_updated_at,
        messages=[],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="分页列出会话",
    description="全局会话可能包含访客历史，因此只向管理员开放。",
)
def list_conversations(
    _: AdminAuthorization,
    session: DatabaseSession,
    offset: int = Query(default=0, ge=0, description="从第几条会话开始读取。"),
    limit: int = Query(default=50, ge=1, le=100, description="最多返回多少条会话。"),
) -> ConversationListResponse:
    """按最近活跃时间分页返回会话摘要。"""
    conversations = AgentService(session).list_conversations(offset=offset, limit=limit)
    return ConversationListResponse(items=conversations, offset=offset, limit=limit)


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="读取 Agent 会话",
    responses={404: {"model": ErrorResponse, "description": "会话不存在。"}},
)
def get_conversation(
    conversation_id: Annotated[str, Path(description="会话 ID。")],
    session: DatabaseSession,
) -> ConversationResponse:
    """返回会话元数据和最近 50 条消息。"""
    service = AgentService(session)
    conversation = service.get_conversation(conversation_id)
    messages = service.get_messages(conversation_id, limit=50)
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        active_jd_analysis_id=conversation.active_jd_analysis_id,
        candidate_profile_version=conversation.candidate_profile_version,
        career_context_updated_at=conversation.career_context_updated_at,
        messages=messages,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除会话",
    responses={404: {"model": ErrorResponse, "description": "会话不存在。"}},
)
def delete_conversation(
    conversation_id: Annotated[str, Path(description="需要删除的会话 ID。")],
    _: AdminAuthorization,
    session: DatabaseSession,
) -> Response:
    """管理员删除会话、历史消息和关联展示数据。"""
    AgentService(session).delete_conversation(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{conversation_id}/messages",
    response_model=AgentExecutionResponse,
    summary="发送消息并运行 LangGraph Agent",
    description=(
        "Agent 识别意图后只能调用白名单工具。知识检索无依据时允许有限改写重试，"
        "达到步骤、时间或递归上限后返回 degraded=true。"
    ),
    responses={
        404: {"model": ErrorResponse, "description": "会话不存在。"},
        409: {"model": ErrorResponse, "description": "相同请求 ID 已执行。"},
    },
)
def send_agent_message(
    conversation_id: Annotated[str, Path(description="会话 ID。")],
    request: AgentMessageRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> AgentExecutionResponse:
    """执行 Agent 并返回引用和精简节点轨迹。"""
    service = AgentService(session, settings)
    result = service.run(
        conversation_id,
        request.question,
        request_id_context.get(),
        filters=SearchFilters(
            document_ids=request.filters.document_ids,
            filenames=request.filters.filenames,
        ),
    )
    if not result.cancelled:
        recommendation = SuggestionService(session, service.settings).generate_for_answer(
            conversation_id,
            answer_mode=result.answer_mode,
            citations=result.citations,
        )
        result.suggestions = recommendation.suggestions
    return AgentExecutionResponse(**asdict(result))


@router.post(
    "/{conversation_id}/messages/stream",
    summary="流式发送消息并运行 Agent",
    description=(
        "使用 Server-Sent Events 返回运行开始、Agent 步骤、正式回答片段、引用和完成事件。"
        "模型输出不经过额外核验模型等待。"
    ),
    responses={404: {"model": ErrorResponse, "description": "会话不存在。"}},
)
def stream_agent_message(
    conversation_id: Annotated[str, Path(description="会话 ID。")],
    request: AgentMessageRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> StreamingResponse:
    """执行 Agent，并以稳定 SSE 协议输出经过验证的结果。"""
    request_id = request_id_context.get()
    filters = SearchFilters(
        document_ids=request.filters.document_ids,
        filenames=request.filters.filenames,
    )
    service = AgentService(session, settings)
    # 流式响应开始后无法再改 HTTP 状态码，因此在发送首个事件前完成 404/409 校验。
    service.validate_run_request(conversation_id, request_id)
    cancellation = _register_active_run(conversation_id, request_id)
    # SSE 工作线程必须使用自己的 SQLAlchemy Session，不能跨线程复用请求会话。
    worker_session_factory = sessionmaker(
        bind=session.get_bind(),
        autoflush=False,
        expire_on_commit=False,
    )

    def generate_events() -> Iterator[str]:
        """并行消费实时 Agent 事件，并在空闲期间发送心跳。"""
        yield _server_sent_event(
            "run_started",
            {"conversation_id": conversation_id, "request_id": request_id},
        )
        # 有界队列让网络较慢时对模型流施加背压，避免草稿 Token 无限占用内存。
        event_queue: Queue[tuple[str, object]] = Queue(maxsize=256)
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="agent-sse")
        context = copy_context()

        def publish_event(event: str, data: object) -> None:
            """在慢客户端产生背压，并在断开后解除可能阻塞的生产者。"""
            while not cancellation.is_set():
                try:
                    event_queue.put((event, data), timeout=0.2)
                    return
                except Full:
                    continue
            raise AgentCancelledError("客户端已经停止接收事件")

        def execute_agent():
            """在独立数据库会话中运行 Agent，并绑定事件与取消上下文。"""
            try:
                with worker_session_factory() as worker_session:
                    worker_service = AgentService(worker_session, settings)
                    with bind_agent_runtime(
                        publish_event,
                        cancellation.is_set,
                    ):
                        return worker_service.run(
                            conversation_id,
                            request.question,
                            request_id,
                            filters=filters,
                        )
            finally:
                _release_active_run(request_id, cancellation)

        future = executor.submit(context.run, execute_agent)
        next_heartbeat_at = time.monotonic() + SSE_HEARTBEAT_INTERVAL_SECONDS
        try:
            while True:
                try:
                    event_name, event_data = event_queue.get(
                        timeout=0 if future.done() else min(0.2, SSE_HEARTBEAT_INTERVAL_SECONDS)
                    )
                    yield _server_sent_event(event_name, event_data)
                except Empty:
                    if future.done():
                        break
                    if time.monotonic() >= next_heartbeat_at:
                        yield _server_sent_event("heartbeat", {"request_id": request_id})
                        next_heartbeat_at = time.monotonic() + SSE_HEARTBEAT_INTERVAL_SECONDS

            result = future.result(timeout=0)
            if result.cancelled:
                yield _server_sent_event(
                    "cancelled",
                    {"request_id": request_id, "run_id": result.run_id},
                )
                return
            # 最终文本只用于校正流式传输拼接，不代表额外模型核验。
            yield _server_sent_event("answer_final", {"answer": result.answer})
            yield _server_sent_event("citations", result.citations)
            if result.resources:
                yield _server_sent_event("resources", result.resources)

            # 主回答已经发送后再生成推荐问题；独立会话保证推荐失败不回滚回答。
            def generate_suggestions() -> tuple[list[str], str]:
                """在独立工作单元中生成并保存当前回答的后续问题。"""
                if cancellation.is_set():
                    return [], "fallback"
                with worker_session_factory() as suggestion_session:
                    recommendation = SuggestionService(
                        suggestion_session,
                        service.settings,
                    ).generate_for_answer(
                        conversation_id,
                        answer_mode=result.answer_mode,
                        citations=result.citations,
                    )
                    return recommendation.suggestions, recommendation.source

            suggestion_future = executor.submit(generate_suggestions)
            try:
                suggestions, suggestion_source = suggestion_future.result(
                    timeout=service.settings.suggestion_timeout_seconds + 1,
                )
            except TimeoutError:
                logger.info(
                    "推荐问题生成超时，主回答保持完成",
                    extra={"request_id": request_id},
                )
                suggestions, suggestion_source = [], "fallback"
            if suggestions:
                yield _server_sent_event(
                    "followup_suggestions",
                    {"suggestions": suggestions, "source": suggestion_source},
                )
            yield _server_sent_event(
                "completed",
                {
                    "run_id": result.run_id,
                    "conversation_id": result.conversation_id,
                    "request_id": result.request_id,
                    "answer_mode": result.answer_mode,
                    "grounded": result.grounded,
                    "degraded": result.degraded,
                    "duration_ms": result.duration_ms,
                    "timings": result.timings,
                },
            )
        except Exception:
            # HTTP 头已经发送，无法再改状态码；使用稳定 SSE 错误事件结束响应。
            logger.exception("Agent SSE 流在完成前异常", extra={"request_id": request_id})
            yield _server_sent_event(
                "error",
                {
                    "code": "agent_stream_failed",
                    "message": "Agent 流式回答暂时失败，请重试。",
                    "request_id": request_id,
                },
            )
        finally:
            # 客户端断开时触发服务端取消；工作线程拥有独立会话，因此无需阻塞等待。
            cancellation.set()
            executor.shutdown(wait=False, cancel_futures=True)

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{conversation_id}/runs/{request_id}/cancel",
    response_model=AgentCancellationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="停止正在执行的 Agent 运行",
    responses={404: {"model": ErrorResponse, "description": "会话或活动运行不存在。"}},
)
def cancel_agent_run(
    conversation_id: Annotated[str, Path(description="运行所属的会话 ID。")],
    request_id: Annotated[str, Path(description="流式请求使用的 X-Request-ID。")],
    session: DatabaseSession,
) -> AgentCancellationResponse:
    """通知模型流和后续 LangGraph 节点尽快停止执行。"""
    AgentService(session).get_conversation(conversation_id)
    if not _cancel_active_run(conversation_id, request_id):
        raise AppError("运行不存在或已经结束", status_code=404, code="agent_run_not_active")
    return AgentCancellationResponse(request_id=request_id)
