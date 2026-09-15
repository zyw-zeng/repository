"""读取本人确认过的结构化档案，并提供确定性事实召回。"""

import json
from pathlib import Path

from app.knowledge.types import SearchResult


class CandidateProfileService:
    """把结构化年限和技能事实转换为可核验的高可信证据。"""

    def __init__(self, path: Path):
        self.path = path

    def get_version(self) -> int | None:
        """读取当前档案版本；文件异常时返回空值而不是伪造版本。"""
        payload = self._load()
        if payload is None:
            return None
        try:
            return int(payload.get("version", 1))
        except (TypeError, ValueError):
            return None

    def _load(self) -> dict | None:
        """集中处理档案文件不存在、损坏或结构错误的情况。"""
        if not self.path.exists():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def search(self, query: str, *, limit: int = 3) -> list[SearchResult]:
        """仅在查询命中明确别名时返回档案事实，避免语义猜测。"""
        payload = self._load()
        if payload is None:
            return []
        normalized = query.lower()
        results: list[SearchResult] = []
        version = int(payload.get("version", 1))
        for fact in payload.get("facts", []):
            aliases = [str(alias) for alias in fact.get("aliases", [])]
            matched = [alias for alias in aliases if alias.lower() in normalized]
            if not matched:
                continue
            fact_id = str(fact.get("id", len(results)))
            results.append(
                SearchResult(
                    chunk_id=f"profile:{fact_id}",
                    document_id="candidate-profile",
                    filename=str(fact.get("source", "结构化个人档案")),
                    content=str(fact.get("evidence", "")),
                    score=min(1.0, 0.9 + len(matched) * 0.02),
                    page_number=None,
                    heading="本人确认的结构化档案",
                    index_version=version,
                )
            )
        return results[:limit]
