"""实现 PDF 文档加载与页码信息提取。"""

from pathlib import Path

import pymupdf

from app.knowledge.types import LoadedBlock, LoadedDocument


def load_pdf(path: Path) -> LoadedDocument:
    """逐页提取 PDF 正文；扫描件在 MVP 中会被视为无正文。"""
    blocks: list[LoadedBlock] = []
    with pymupdf.open(path) as pdf:
        for page_index, page in enumerate(pdf):
            text = page.get_text("text")
            if text.strip():
                blocks.append(
                    LoadedBlock(
                        text=text,
                        page_number=page_index + 1,
                        start_offset=0,
                        end_offset=len(text),
                    )
                )

    return LoadedDocument(source_path=path, file_type="pdf", blocks=blocks)
