"""可靠 RAG 问答接口的请求和响应模型。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HistoryMessage(BaseModel):
    """用于查询改写的有限对话历史。"""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class KnowledgeFilters(BaseModel):
    """限制知识检索范围的可选元数据。"""

    document_ids: list[str] = Field(default_factory=list, max_length=50)
    filenames: list[str] = Field(default_factory=list, max_length=50)


class ChatRequest(BaseModel):
    """单次知识问答或闲聊请求。"""

    question: str = Field(min_length=1, max_length=4000, description="用户当前问题。")
    mode: Literal["knowledge_base", "casual"] = Field(
        default="knowledge_base",
        description="知识库模式强制检索；闲聊模式不生成知识库引用。",
    )
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)
    filters: KnowledgeFilters = Field(default_factory=KnowledgeFilters)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        """拒绝只包含空白字符的问题。"""
        normalized = value.strip()
        if not normalized:
            raise ValueError("问题不能为空")
        return normalized


class CitationResponse(BaseModel):
    """可核查到权威切片正文的单条引用。"""

    model_config = ConfigDict(from_attributes=True)

    reference_number: int
    chunk_id: str
    document_id: str
    filename: str
    quote: str
    page_number: int | None
    heading: str | None
    index_version: int


class ChatResponse(BaseModel):
    """问答结果、回答模式、依据状态和引用列表。"""

    answer: str
    answer_mode: Literal["knowledge_base", "casual"]
    grounded: bool
    rewritten_query: str
    citations: list[CitationResponse]
    retrieved_count: int
    request_id: str
