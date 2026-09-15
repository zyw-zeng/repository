"""校验模型配置并向业务层提供统一的模型创建入口。"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.llm.chat import build_chat_model
from app.llm.embeddings import build_embeddings


def _require_api_key(settings: Settings) -> str:
    """读取模型密钥；缺失时返回可识别的应用错误。"""
    if not settings.dashscope_api_key:
        raise AppError(
            "DASHSCOPE_API_KEY is not configured",
            status_code=503,
            code="model_not_configured",
        )
    return settings.dashscope_api_key


def create_chat_model(settings: Settings | None = None) -> ChatOpenAI:
    """创建主回答模型；保留旧入口以兼容现有调用方。"""
    resolved_settings = settings or get_settings()
    return build_chat_model(
        resolved_settings,
        _require_api_key(resolved_settings),
        model=resolved_settings.chat_model,
    )


def create_router_model(settings: Settings | None = None) -> ChatOpenAI:
    """创建用于意图识别和查询改写的低延迟模型。"""
    resolved_settings = settings or get_settings()
    return build_chat_model(
        resolved_settings,
        _require_api_key(resolved_settings),
        model=resolved_settings.router_model,
    )


def create_suggestion_model(settings: Settings | None = None) -> ChatOpenAI:
    """创建低成本推荐问题模型，并使用独立的短超时和输出上限。"""
    resolved_settings = settings or get_settings()
    return build_chat_model(
        resolved_settings,
        _require_api_key(resolved_settings),
        model=resolved_settings.suggestion_model,
        timeout=resolved_settings.suggestion_timeout_seconds,
        max_retries=0,
        max_tokens=240,
    )


def create_jd_model(settings: Settings | None = None) -> ChatOpenAI:
    """创建 JD 解析和证据判断模型，允许完整返回结构化批次结果。"""
    resolved_settings = settings or get_settings()
    return build_chat_model(
        resolved_settings,
        _require_api_key(resolved_settings),
        model=resolved_settings.router_model,
        max_tokens=resolved_settings.jd_model_max_output_tokens,
    )


def create_embeddings(settings: Settings | None = None) -> OpenAIEmbeddings:
    """使用显式配置或全局配置创建向量模型。"""
    resolved_settings = settings or get_settings()
    return build_embeddings(resolved_settings, _require_api_key(resolved_settings))
