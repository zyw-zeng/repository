"""实现候选证据的上下文组装和长度控制。"""

from app.knowledge.types import ContextItem, SearchResult


def assemble_context(
    results: list[SearchResult],
    *,
    max_chars: int,
) -> tuple[str, list[ContextItem]]:
    """按相关性顺序组装编号证据，不在片段中间截断正文。"""
    blocks: list[str] = []
    items: list[ContextItem] = []
    used_chars = 0
    for result in results:
        reference_number = len(items) + 1
        location_parts = [f"文件：{result.filename}"]
        if result.page_number is not None:
            location_parts.append(f"页码：{result.page_number}")
        if result.heading:
            location_parts.append(f"章节：{result.heading}")
        block = (
            f"[{reference_number}] {'；'.join(location_parts)}\n"
            f"切片 ID：{result.chunk_id}\n"
            f"正文：{result.content}"
        )
        additional_chars = len(block) + (2 if blocks else 0)
        if blocks and used_chars + additional_chars > max_chars:
            break
        # 至少保留第一条完整证据，避免较长切片导致上下文意外为空。
        blocks.append(block)
        items.append(ContextItem(reference_number=reference_number, result=result))
        used_chars += additional_chars
    return "\n\n".join(blocks), items
