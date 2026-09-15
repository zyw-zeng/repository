"""定义文档、会话、消息和 Agent 运行记录的 ORM 实体。"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.database import Base


def new_id() -> str:
    """生成适合作为公开资源标识的 UUID 字符串。"""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """返回带 UTC 时区的当前时间，统一数据库时间语义。"""
    return datetime.now(UTC)


class DocumentRecord(Base):
    """原始文档及其处理状态。"""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    filename: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    file_type: Mapped[str] = mapped_column(String(20))
    storage_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    active_index_version: Mapped[int] = mapped_column(Integer, default=0)
    # 新上传文档默认私有，避免公开部署后未经确认就进入访客检索。
    visibility: Mapped[str] = mapped_column(String(20), default="private", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    # 删除文档时同步删除它在关系数据库中的所有切片记录。
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["IngestionJob"]] = relationship(back_populates="document")


class DocumentChunk(Base):
    """文档切片的定位信息及其向量索引标识。"""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    index_version: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    vector_id: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    document: Mapped[DocumentRecord] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "index_version",
            "chunk_index",
            name="uq_document_chunk_version_index",
        ),
    )


class IngestionJob(Base):
    """记录可恢复的文档索引、重建和删除任务。"""

    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    operation: Mapped[str] = mapped_column(String(20))
    target_index_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    progress: Mapped[float] = mapped_column(Float, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    document: Mapped[DocumentRecord | None] = relationship(back_populates="jobs")


class Conversation(Base):
    """一组连续的用户与 AI 对话。"""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(255), default="新会话")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    # 保存当前求职对话绑定的 JD 与档案版本，后续追问不需要重新粘贴岗位描述。
    active_jd_analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("jd_analyses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    candidate_profile_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    career_context_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 会话删除后，其历史消息不再具有独立保留意义。
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    """会话中的单条消息以及可追踪的引用信息。"""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 保存回答完成后生成的推荐追问，刷新会话时无需再次调用模型。
    suggestions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 保存简历等结构化资源，使会话恢复后仍能渲染对应操作卡片。
    resources_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 保存 JD 报告等聊天内结构化工具卡片引用。
    artifacts_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class SuggestionCache(Base):
    """缓存由公开文档版本生成的空状态推荐问题。"""

    __tablename__ = "suggestion_caches"

    cache_key: Mapped[str] = mapped_column(String(80), primary_key=True)
    suggestions_json: Mapped[list] = mapped_column(JSON)
    source_signature: Mapped[str] = mapped_column(String(64), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AgentRun(Base):
    """记录一次 Agent 执行的状态、工具调用和耗时。"""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    request_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    tool_calls_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class JdAnalysis(Base):
    """保存一次 JD 岗位匹配的输入、结构化结果和可审计评分。"""

    __tablename__ = "jd_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    request_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    jd_text: Mapped[str] = mapped_column(Text)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requirements_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    matches_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness: Mapped[float | None] = mapped_column(Float, nullable=True)
    verified_fit: Mapped[float | None] = mapped_column(Float, nullable=True)
    feasibility: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class TtsVoiceProfile(Base):
    """保存每个精灵角色使用的 CosyVoice 音色及自动朗读策略。"""

    __tablename__ = "tts_voice_profiles"

    character_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100), default="cosyvoice-v3-flash")
    voice: Mapped[str] = mapped_column(String(120), default="longanyang")
    enabled: Mapped[bool] = mapped_column(default=True)
    auto_speak: Mapped[bool] = mapped_column(default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
