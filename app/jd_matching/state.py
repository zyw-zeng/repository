"""定义 JD 岗位匹配 LangGraph 的共享状态。"""

from typing import Any, TypedDict


class JdMatchingState(TypedDict, total=False):
    """在解析、检索、判断和评分节点之间传递的数据。"""

    jd_text: str
    company_name: str | None
    job_title: str | None
    requirements: list[dict[str, Any]]
    evidence_by_requirement: dict[str, list[dict[str, Any]]]
    assessments: list[dict[str, Any]]
    matches: list[dict[str, Any]]
    score: float
    completeness: float
    verified_fit: float
    feasibility: float
