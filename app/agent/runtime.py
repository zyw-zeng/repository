"""在 Agent 工作线程与 SSE 响应之间传递实时事件和取消信号。"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

AgentEventSink = Callable[[str, object], None]
CancellationCheck = Callable[[], bool]

_event_sink: ContextVar[AgentEventSink | None] = ContextVar("agent_event_sink", default=None)
_cancellation_check: ContextVar[CancellationCheck | None] = ContextVar(
    "agent_cancellation_check",
    default=None,
)


class AgentCancelledError(Exception):
    """表示用户主动终止了一次 Agent 运行，不应降级为普通失败。"""


@contextmanager
def bind_agent_runtime(
    event_sink: AgentEventSink,
    cancellation_check: CancellationCheck,
) -> Iterator[None]:
    """为当前执行上下文绑定事件出口和取消状态读取器。"""
    event_token = _event_sink.set(event_sink)
    cancellation_token = _cancellation_check.set(cancellation_check)
    try:
        yield
    finally:
        _event_sink.reset(event_token)
        _cancellation_check.reset(cancellation_token)


def emit_agent_event(event: str, data: object) -> None:
    """存在 SSE 订阅者时立即发送事件，普通同步调用保持无副作用。"""
    sink = _event_sink.get()
    if sink is not None:
        sink(event, data)


def is_agent_cancelled() -> bool:
    """读取当前运行是否已经收到用户取消信号。"""
    check = _cancellation_check.get()
    return bool(check and check())


def raise_if_agent_cancelled() -> None:
    """在模型调用和节点边界主动终止已取消的运行。"""
    if is_agent_cancelled():
        raise AgentCancelledError("用户已停止生成")


def emit_agent_step(name: str, **details: Any) -> list[dict[str, Any]]:
    """同时生成持久化步骤并实时推送给 SSE 客户端。"""
    step = {"node": name, **details}
    emit_agent_event("agent_step", step)
    return [step]
