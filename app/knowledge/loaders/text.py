"""实现纯文本文档加载。"""

from pathlib import Path

from app.knowledge.types import LoadedBlock, LoadedDocument


def _read_supported_encoding(path: Path) -> str:
    """依次尝试常见中英文编码，并在全部失败后保留原始异常。"""
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return ""


def load_text(path: Path) -> LoadedDocument:
    """读取 UTF-8 或 GB18030 编码的纯文本文件。"""
    content = _read_supported_encoding(path)
    return LoadedDocument(
        source_path=path,
        file_type="txt",
        blocks=[LoadedBlock(text=content, start_offset=0, end_offset=len(content))],
    )
