"""实现能够保留文档结构信息的文本切分。"""

import hashlib

from app.knowledge.cleaner import clean_text
from app.knowledge.types import ChunkDraft, LoadedDocument


def _choose_breakpoint(text: str, start: int, preferred_end: int) -> int:
    """在目标长度附近优先选择段落或中文句末作为切分点。"""
    if preferred_end >= len(text):
        return len(text)

    minimum_end = start + max(1, (preferred_end - start) // 2)
    for separator in ("\n\n", "\n", "。", "！", "？", "；", ". "):
        position = text.rfind(separator, minimum_end, preferred_end)
        if position >= minimum_end:
            return position + len(separator)
    return preferred_end


def _split_block(text: str, chunk_size: int, chunk_overlap: int) -> list[tuple[str, int, int]]:
    """将一个文本块切分为带块内字符偏移的片段。"""
    pieces: list[tuple[str, int, int]] = []
    start = 0
    while start < len(text):
        end = _choose_breakpoint(text, start, min(start + chunk_size, len(text)))
        raw_piece = text[start:end]
        leading_spaces = len(raw_piece) - len(raw_piece.lstrip())
        trailing_end = end - (len(raw_piece) - len(raw_piece.rstrip()))
        content = raw_piece.strip()
        if content:
            pieces.append((content, start + leading_spaces, trailing_end))

        if end >= len(text):
            break
        # 重叠区域帮助保留切分边界附近的上下文，同时保证游标一定向前移动。
        start = max(start + 1, end - chunk_overlap)
    return pieces


def split_document(
    document: LoadedDocument,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[ChunkDraft]:
    """按文档块切分文本，并保留页码、标题和原文偏移。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须大于等于 0 且小于 chunk_size")

    drafts: list[ChunkDraft] = []
    for block in document.blocks:
        cleaned = clean_text(block.text)
        if not cleaned:
            continue

        for content, local_start, local_end in _split_block(cleaned, chunk_size, chunk_overlap):
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            base_offset = block.start_offset or 0
            drafts.append(
                ChunkDraft(
                    chunk_index=len(drafts),
                    content=content,
                    content_hash=content_hash,
                    page_number=block.page_number,
                    heading=block.heading,
                    token_count=max(1, len(content) // 2),
                    start_offset=base_offset + local_start,
                    end_offset=base_offset + local_end,
                    metadata=dict(block.metadata),
                )
            )

    if not drafts:
        raise ValueError("文档中没有可用于索引的有效文本")
    return drafts
