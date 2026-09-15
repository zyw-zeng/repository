"""构建兼容 OpenAI 协议的对话模型客户端。"""

from langchain_openai import ChatOpenAI

from app.core.config import Settings


def build_chat_model(
    settings: Settings,
    api_key: str,
    *,
    model: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """按角色创建对话模型；速度模式默认关闭 Qwen 深度思考。"""
    return ChatOpenAI(
        model=model or settings.chat_model,
        api_key=api_key,
        base_url=settings.model_base_url,
        timeout=timeout if timeout is not None else settings.model_timeout_seconds,
        max_retries=max_retries if max_retries is not None else settings.model_max_retries,
        temperature=0,
        max_tokens=max_tokens if max_tokens is not None else settings.model_max_output_tokens,
        # DashScope 的 OpenAI 兼容接口通过 extra_body 接收思考开关。
        extra_body={"enable_thinking": settings.model_enable_thinking},
    )
