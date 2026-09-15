"""评估不同知识来源作为岗位匹配证据的可靠程度。"""

from app.knowledge.types import SearchResult


def evidence_source_quality(result: SearchResult | dict) -> float:
    """按来源和内容给出确定性质量系数，规划内容不能证明已完成经验。"""
    if isinstance(result, dict):
        document_id = str(result.get("document_id", ""))
        filename = str(result.get("filename", ""))
        content = str(result.get("quote", ""))
    else:
        document_id = result.document_id
        filename = result.filename
        content = result.content
    lowered_filename = filename.lower()
    if document_id == "candidate-profile":
        return 1.0
    if "development_plan" in lowered_filename or "开发计划" in filename:
        if any(word in content for word in ("计划", "待实现", "下一阶段", "将实现")):
            return 0.2
        return 0.5
    if lowered_filename.endswith(".pdf") or "简历" in filename:
        return 0.95
    if "readme" in lowered_filename or "项目" in filename:
        return 0.85
    return 0.75


def evidence_source_type(result: SearchResult | dict) -> str:
    """为界面和判断模型标记结构化事实、简历、项目或普通文档。"""
    if isinstance(result, dict):
        document_id = str(result.get("document_id", ""))
        filename = str(result.get("filename", ""))
    else:
        document_id = result.document_id
        filename = result.filename
    if document_id == "candidate-profile":
        return "profile"
    lowered = filename.lower()
    if lowered.endswith(".pdf") or "简历" in filename:
        return "resume"
    if "development_plan" in lowered or "开发计划" in filename:
        return "plan"
    if "readme" in lowered or "项目" in filename:
        return "project"
    return "document"
