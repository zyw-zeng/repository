"""定义 LangGraph 各节点共享的 Agent 状态。"""

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    """保存一次有界 Agent 执行所需的全部可序列化状态。"""

    request_id: str
    conversation_id: str
    question: str
    current_query: str
    history: list[tuple[str, str]]
    document_ids: list[str]
    filenames: list[str]
    intent: str
    selected_tool: str
    answer: str
    answer_mode: str
    grounded: bool
    citations: list[dict[str, Any]]
    resources: list[dict[str, Any]]
    retrieved_count: int
    retrieval_attempts: int
    retry_allowed: bool
    step_count: int
    max_steps: int
    max_retrieval_attempts: int
    deadline: float
    degraded: bool
    error: str | None
    # 每个阶段只写入自己的键，节点返回时会与已有字典显式合并。
    timings: dict[str, int]
    # reducer 使每个节点只需返回本步骤，LangGraph 会按顺序累积完整轨迹。
    steps: Annotated[list[dict[str, Any]], operator.add]
