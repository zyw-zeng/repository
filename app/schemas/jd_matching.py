"""定义 JD 岗位匹配接口的输入、过程和报告结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JdAnalysisRequest(BaseModel):
    """访客粘贴的岗位描述。"""

    jd_text: str = Field(min_length=30, max_length=30000)
    conversation_id: str | None = Field(default=None, max_length=36)

    @field_validator("jd_text")
    @classmethod
    def normalize_jd_text(cls, value: str) -> str:
        """清理首尾空白并拒绝缺少实际内容的 JD。"""
        normalized = value.strip()
        if len(normalized) < 30:
            raise ValueError("JD 内容至少需要 30 个字符")
        return normalized


class JdRequirement(BaseModel):
    """从 JD 中提取的一项可验证要求。"""

    id: str
    requirement: str
    category: str
    importance: Literal["required", "preferred"]
    weight: int = Field(ge=1, le=10)
    keywords: list[str] = Field(default_factory=list)
    requirement_type: str


class JdEvidence(BaseModel):
    """来自公开知识库且通过活动版本校验的证据。"""

    chunk_id: str
    document_id: str
    filename: str
    quote: str
    page_number: int | None = None
    heading: str | None = None
    index_version: int
    score: float
    source_type: str
    source_quality: float


class JdRequirementMatch(BaseModel):
    """单项岗位要求的匹配结论。"""

    requirement_id: str
    requirement: str
    category: str
    requirement_type: str
    importance: Literal["required", "preferred"]
    weight: int
    level: Literal[
        "strong_match", "partial_match", "missing", "unverified", "conflict"
    ]
    reason: str
    awarded_score: float
    max_score: float
    evidence: list[JdEvidence] = Field(default_factory=list)


class JdAnalysisResponse(BaseModel):
    """完整且可持久化的岗位匹配报告。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    status: str
    company_name: str | None
    job_title: str | None
    score: float | None
    completeness: float | None
    verified_fit: float | None
    feasibility: float | None
    requirements: list[JdRequirement] = Field(default_factory=list)
    matches: list[JdRequirementMatch] = Field(default_factory=list)
    duration_ms: int | None
    created_at: datetime
    updated_at: datetime


class JdCancellationResponse(BaseModel):
    """服务端接受取消请求后的响应。"""

    request_id: str
    status: str = "cancellation_requested"
