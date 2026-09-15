"""定义 Career Agent 独立 LangGraph 状态。"""

import operator
from typing import Annotated, Any, TypedDict


class CareerAgentState(TypedDict, total=False):
    """保存工具计划、执行位置、回答和硬性运行预算。"""

    question: str
    analysis_id: str
    job_title: str
    profile_version: int | None
    context_stale: bool
    selected_tools: list[str]
    next_tool_index: int
    sections: Annotated[list[dict[str, Any]], operator.add]
    evidence: Annotated[list[dict[str, Any]], operator.add]
    answer: str
    answer_mode: str
    grounded: bool
    citations: list[dict[str, Any]]
    resources: list[dict[str, Any]]
    step_count: int
    max_steps: int
    deadline: float
    degraded: bool
    error: str | None
    timings: dict[str, int]
    steps: Annotated[list[dict[str, Any]], operator.add]
