"""文本清理、结构化切分和稳定向量 ID 的单元测试。"""

from pathlib import Path

import pytest

from app.knowledge.cleaner import clean_text
from app.knowledge.indexer import build_vector_id
from app.knowledge.splitter import split_document
from app.knowledge.types import LoadedBlock, LoadedDocument


def test_clean_text_preserves_paragraphs() -> None:
    """清理空白时应保留有意义的段落边界。"""
    assert clean_text("第一段  \r\n\r\n\r\n第二段") == "第一段\n\n第二段"


def test_split_document_preserves_metadata() -> None:
    """切片应继承标题、页码和自定义元数据。"""
    document = LoadedDocument(
        source_path=Path("sample.txt"),
        file_type="txt",
        blocks=[
            LoadedBlock(
                text="第一段内容。第二段内容。第三段内容。",
                page_number=2,
                heading="章节",
                metadata={"language": "zh"},
            )
        ],
    )

    chunks = split_document(document, chunk_size=12, chunk_overlap=2)

    assert len(chunks) >= 2
    assert all(chunk.page_number == 2 for chunk in chunks)
    assert all(chunk.heading == "章节" for chunk in chunks)
    assert all(chunk.metadata["language"] == "zh" for chunk in chunks)


def test_invalid_overlap_is_rejected() -> None:
    """重叠长度不能达到或超过单个切片大小。"""
    document = LoadedDocument(
        source_path=Path("sample.txt"),
        file_type="txt",
        blocks=[LoadedBlock(text="有效正文")],
    )
    with pytest.raises(ValueError, match="chunk_overlap"):
        split_document(document, chunk_size=10, chunk_overlap=10)


def test_vector_id_is_stable_and_versioned() -> None:
    """相同输入生成相同 ID，不同索引版本生成不同 ID。"""
    first = build_vector_id(
        document_id="doc", index_version=1, chunk_index=0, content_hash="hash"
    )
    repeated = build_vector_id(
        document_id="doc", index_version=1, chunk_index=0, content_hash="hash"
    )
    next_version = build_vector_id(
        document_id="doc", index_version=2, chunk_index=0, content_hash="hash"
    )

    assert first == repeated
    assert first != next_version
