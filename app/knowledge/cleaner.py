"""实现文本标准化和噪声清理规则。"""

import re
import unicodedata


def clean_text(text: str) -> str:
    """规范字符和空白，同时保留段落边界供结构化切分使用。"""
    normalized = unicodedata.normalize("NFKC", text).replace("\x00", "")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    # 压缩行内空白，但不删除换行所表达的段落结构。
    lines = [re.sub(r"[\t \u3000]+", " ", line).strip() for line in normalized.split("\n")]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()
