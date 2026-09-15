"""LangGraph Agent 会话和执行接口的数据结构。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.chat import CitationResponse, KnowledgeFilters
from app.schemas.resume import ResumeResource


class CreateConversationRequest(BaseModel):
    """创建会话时可选的显示标题。"""

    title: str = Field(default="新会话", max_length=255)


class AgentMessageRequest(BaseModel):
    """发送给 Agent 的问题和知识库过滤范围。"""

    question: str = Field(min_length=1, max_length=4000)
    filters: KnowledgeFilters = Field(default_factory=KnowledgeFilters)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        """拒绝只包含空白字符的问题。"""
        normalized = value.strip()
        if not normalized:
            raise ValueError("问题不能为空")
        return normalized


class MessageResponse(BaseModel):
    """持久化的单条会话消息。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    citations_json: list[dict[str, Any]] | None
    suggestions_json: list[str] | None
    resources_json: list[ResumeResource] | None
    artifacts_json: list[dict[str, Any]] | None
    created_at: datetime


class ConversationResponse(BaseModel):
    """会话元数据及其最近消息。"""

    id: str
    title: str
    active_jd_analysis_id: str | None = None
    candidate_profile_version: int | None = None
    career_context_updated_at: datetime | None = None
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime


class ConversationSummaryResponse(BaseModel):
    """会话列表中的轻量摘要，不重复返回全部消息。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    active_jd_analysis_id: str | None = None
    candidate_profile_version: int | None = None
    career_context_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """管理员可见的会话分页结果。"""

    items: list[ConversationSummaryResponse]
    offset: int
    limit: int


class AgentExecutionResponse(BaseModel):
    """Agent 回答、引用、运行状态和精简执行轨迹。"""

    run_id: str
    conversation_id: str
    request_id: str
    answer: str
    answer_mode: str
    grounded: bool
    degraded: bool
    citations: list[CitationResponse]
    steps: list[dict[str, Any]]
    duration_ms: int
    timings: dict[str, int] = Field(default_factory=dict)
    suggestions: list[str] = Field(default_factory=list)
    resources: list[ResumeResource] = Field(default_factory=list)
    cancelled: bool = False


class AgentCancellationResponse(BaseModel):
    """服务端已接收指定 Agent 运行的取消请求。"""

    request_id: str
    status: str = "cancellation_requested"
