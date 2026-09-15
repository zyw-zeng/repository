"""实现 Markdown 文档加载与标题层级提取。"""

import re
from pathlib import Path

from app.knowledge.loaders.text import _read_supported_encoding
from app.knowledge.types import LoadedBlock, LoadedDocument

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def load_markdown(path: Path) -> LoadedDocument:
    """按 Markdown 标题拆成结构块，并保留标题与字符偏移。"""
    content = _read_supported_encoding(path)
    blocks: list[LoadedBlock] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    block_start = 0
    offset = 0

    def flush_block(end_offset: int) -> None:
        """把当前标题下累积的正文保存为一个加载块。"""
        text = "".join(current_lines).strip()
        if text:
            blocks.append(
                LoadedBlock(
                    text=text,
                    heading=current_heading,
                    start_offset=block_start,
                    end_offset=end_offset,
                )
            )

    for line in content.splitlines(keepends=True):
        match = HEADING_PATTERN.match(line.rstrip("\r\n"))
        if match:
            flush_block(offset)
            current_lines.clear()
            current_heading = match.group(2).strip()
            block_start = offset + len(line)
        else:
            current_lines.append(line)
        offset += len(line)

    flush_block(len(content))
    return LoadedDocument(source_path=path, file_type="markdown", blocks=blocks)
