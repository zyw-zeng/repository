"""根据文件扩展名选择经过白名单限制的文档加载器。"""

from pathlib import Path

from app.knowledge.loaders.docx import load_docx
from app.knowledge.loaders.markdown import load_markdown
from app.knowledge.loaders.pdf import load_pdf
from app.knowledge.loaders.text import load_text
from app.knowledge.types import LoadedDocument

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt", ".docx"}


class DocumentLoadError(ValueError):
    """表示文件格式损坏、编码错误或没有可用正文。"""


def load_document(path: Path) -> LoadedDocument:
    """验证扩展名后调用对应加载器。"""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise DocumentLoadError(f"不支持的文件格式: {suffix or '无扩展名'}")

    try:
        if suffix == ".pdf":
            document = load_pdf(path)
        elif suffix == ".docx":
            document = load_docx(path)
        elif suffix in {".md", ".markdown"}:
            document = load_markdown(path)
        else:
            document = load_text(path)
    except DocumentLoadError:
        raise
    except Exception as exc:
        raise DocumentLoadError(f"文档解析失败: {path.name}") from exc

    if not document.blocks or not any(block.text.strip() for block in document.blocks):
        raise DocumentLoadError("文档中没有可用于索引的正文")
    return document


__all__ = ["DocumentLoadError", "SUPPORTED_EXTENSIONS", "load_document"]
