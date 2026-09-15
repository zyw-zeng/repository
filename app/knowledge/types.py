"""文档加载、切分和检索过程中使用的内部数据结构。"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class LoadedBlock:
    """从原始文件中提取的结构化文本块。"""

    text: str
    page_number: int | None = None
    heading: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LoadedDocument:
    """加载完成但尚未切分的文档。"""

    source_path: Path
    file_type: str
    blocks: list[LoadedBlock]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChunkDraft:
    """尚未写入数据库和向量库的文档切片。"""

    chunk_index: int
    content: str
    content_hash: str
    page_number: int | None
    heading: str | None
    token_count: int
    start_offset: int | None
    end_offset: int | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchResult:
    """向量检索返回的权威切片和相似度信息。"""

    chunk_id: str
    document_id: str
    filename: str
    content: str
    score: float
    page_number: int | None
    heading: str | None
    index_version: int


@dataclass(slots=True)
class SearchFilters:
    """限制检索范围的文档元数据过滤条件。"""

    document_ids: list[str] = field(default_factory=list)
    filenames: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ContextItem:
    """发送给模型的编号证据及其权威切片标识。"""

    reference_number: int
    result: SearchResult


@dataclass(slots=True)
class CitationRecord:
    """经过活动版本复核后允许返回给调用方的引用。"""

    reference_number: int
    chunk_id: str
    document_id: str
    filename: str
    quote: str
    page_number: int | None
    heading: str | None
    index_version: int


@dataclass(slots=True)
class RagAnswer:
    """一次可靠 RAG 调用的内部结果。"""

    answer: str
    answer_mode: str
    grounded: bool
    rewritten_query: str
    citations: list[CitationRecord] = field(default_factory=list)
    retrieved_count: int = 0
    timings: dict[str, int] = field(default_factory=dict)
    # 只有检索确实可能改善结果时才允许 LangGraph 再次检索。
    retry_allowed: bool = True
