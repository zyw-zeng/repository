"""推荐问题公开接口的数据结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SuggestionResponse(BaseModel):
    """前端可直接展示的推荐问题集合。"""

    suggestions: list[str] = Field(max_length=3)
    source: Literal["cache", "generated", "fallback", "stored"]
    generated_at: datetime | None = None
