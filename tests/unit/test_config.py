"""配置模块的单元测试。"""

from app.core.config import Settings


def test_default_models() -> None:
    """未提供环境变量时应使用项目约定的默认模型。"""
    settings = Settings(_env_file=None)
    assert settings.chat_model == "qwen3.7-plus"
    assert settings.router_model == "qwen3.7-flash"
    assert settings.model_enable_thinking is False
    assert settings.rag_min_score == 0.35
    assert settings.embedding_model == "qwen3.7-text-embedding"
    assert settings.embedding_dimensions == 1024
    assert settings.app_name == "ZYW 的 AI 小助理"
    assert settings.app_version == "0.6.3"


def test_api_key_is_hidden() -> None:
    """配置对象的调试输出不得泄露 API Key。"""
    settings = Settings(_env_file=None, dashscope_api_key="secret-value")
    assert "secret-value" not in repr(settings)
