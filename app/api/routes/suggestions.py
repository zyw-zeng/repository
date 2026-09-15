"""提供不依赖具体会话的首页动态推荐问题。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import DatabaseSession
from app.core.config import Settings, get_settings
from app.schemas.suggestions import SuggestionResponse
from app.services.suggestion_service import SuggestionService

router = APIRouter(prefix="/api/v1/suggestions", tags=["推荐问题"])


@router.get(
    "",
    response_model=SuggestionResponse,
    summary="读取首页动态推荐问题",
    description="根据当前公开知识库主题生成并缓存，文档版本变化后自动使用新缓存。",
)
def get_empty_suggestions(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SuggestionResponse:
    """返回空状态推荐，生成失败时返回与公开主题相关的规则候选。"""
    result = SuggestionService(session, settings).get_empty_suggestions()
    return SuggestionResponse(suggestions=result.suggestions, source=result.source)
