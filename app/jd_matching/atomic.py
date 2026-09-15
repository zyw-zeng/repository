"""把模型提取的复合岗位要求规范化为独立可评价的原子要求。"""

import re
from typing import Any

RequirementType = str

_PROFILE_PATTERNS = ("学历", "专业", "年经验", "年以上", "年龄", "工作年限")
_TECH_PATTERNS = (
    "python",
    "java",
    "javascript",
    "typescript",
    "vue",
    "react",
    "echarts",
    "langgraph",
    "langchain",
    "websocket",
    "sse",
)


def _split_top_level(text: str) -> list[str]:
    """只在括号之外拆分要求，避免把技术说明列表误当成多个岗位要求。"""
    pairs = {"(": ")", "（": "）", "[": "]", "【": "】"}
    closing = set(pairs.values())
    stack: list[str] = []
    segments: list[str] = []
    current: list[str] = []
    for character in text:
        if character in pairs:
            stack.append(pairs[character])
        elif character in closing and stack and character == stack[-1]:
            stack.pop()
        if character in "，、；;" and not stack:
            segment = "".join(current).strip()
            if segment:
                segments.append(segment)
            current = []
        else:
            current.append(character)
    tail = "".join(current).strip()
    if tail:
        segments.append(tail)
    return segments


def identify_requirement_type(text: str) -> RequirementType:
    """根据可解释规则识别要求应使用的证据工具类型。"""
    normalized = text.lower()
    if any(pattern in normalized for pattern in _PROFILE_PATTERNS):
        return "profile_fact"
    if any(pattern in normalized for pattern in _TECH_PATTERNS):
        return "technical_skill"
    if any(pattern in text for pattern in ("项目经验", "开发背景", "产品开发", "平台集成")):
        return "project_experience"
    if any(pattern in text for pattern in ("工程化", "安全", "架构", "性能", "能力")):
        return "engineering_capability"
    return "bonus_experience"


def atomize_requirements(
    requirements: list[dict[str, Any]], *, max_items: int = 24
) -> list[dict[str, Any]]:
    """按语义分隔符拆分复合要求，并重新生成稳定的顺序 ID。"""
    atomic: list[dict[str, Any]] = []
    seen: set[str] = set()
    for requirement in requirements:
        text = str(requirement["requirement"]).strip(" ，,；;")
        segments = _split_top_level(text)
        # 单字或过短片段通常只是上一项的补语，不进行机械拆分。
        if len(segments) < 2 or any(len(segment) < 4 for segment in segments):
            segments = [text]
        for segment in segments:
            normalized = re.sub(r"\s+", "", segment).lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            supplied_keywords = requirement.get("keywords", [])
            keywords = [
                keyword
                for keyword in supplied_keywords
                if str(keyword).lower() in segment.lower()
            ]
            atomic.append(
                {
                    **requirement,
                    "requirement": segment,
                    "keywords": keywords or [segment],
                    "requirement_type": identify_requirement_type(segment),
                }
            )
            if len(atomic) >= max_items:
                break
        if len(atomic) >= max_items:
            break
    return [{**item, "id": f"req-{index}"} for index, item in enumerate(atomic, start=1)]
