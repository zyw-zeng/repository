"""使用确定性规则计算岗位匹配分数和信息完整度。"""

from typing import Any

MATCH_COEFFICIENTS = {
    "strong_match": 1.0,
    "partial_match": 0.55,
    "missing": 0.0,
    "unverified": 0.0,
    "conflict": 0.0,
}


def calculate_scores(matches: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    """计算岗位匹配、证据完整度、已证实强度和求职可行度。"""
    total_weight = sum(float(item["weight"]) for item in matches)
    if total_weight <= 0:
        return 0.0, 0.0, 0.0, 0.0
    earned = sum(float(item["awarded_score"]) for item in matches)
    evidenced = sum(float(item["weight"]) for item in matches if item.get("evidence"))
    conservative = round(earned / total_weight * 100, 1)
    completeness = round(evidenced / total_weight * 100, 1)
    verified_fit = round(earned / evidenced * 100, 1) if evidenced > 0 else 0.0
    required = [item for item in matches if item.get("importance") == "required"]
    required_weight = sum(float(item["weight"]) for item in required)
    required_earned = sum(float(item["awarded_score"]) for item in required)
    required_fit = required_earned / required_weight * 100 if required_weight else conservative
    # 求职可行度强调必备项，同时按证据覆盖率施加置信折扣，避免少量命中显示虚高。
    confidence_factor = 0.75 + completeness / 400
    feasibility = round(
        min(100.0, (conservative * 0.6 + required_fit * 0.4) * confidence_factor),
        1,
    )
    return conservative, completeness, verified_fit, feasibility


def awarded_score(weight: int, level: str, source_quality: float = 1.0) -> float:
    """结合固定匹配系数和来源质量计算单项稳定分数。"""
    bounded_quality = min(1.0, max(0.0, source_quality))
    return round(weight * MATCH_COEFFICIENTS.get(level, 0.0) * bounded_quality, 2)
