"""模型适配器的单元测试。"""

from app.core.config import Settings
from app.llm.factory import (
    create_chat_model,
    create_embeddings,
    create_router_model,
)


def test_dashscope_embeddings_keep_string_inputs() -> None:
    """百炼 Embedding 必须关闭预分词，确保接口收到字符串列表。"""
    settings = Settings(_env_file=None, dashscope_api_key="test-key")

    embeddings = create_embeddings(settings)

    assert embeddings.check_embedding_ctx_length is False
    assert embeddings.dimensions == settings.embedding_dimensions
    assert embeddings.chunk_size == settings.embedding_batch_size


def test_speed_mode_splits_models_and_disables_thinking() -> None:
    """回答和路由使用各自模型，并统一关闭默认思考。"""
    settings = Settings(_env_file=None, dashscope_api_key="test-key")

    answer = create_chat_model(settings)
    router = create_router_model(settings)

    assert answer.model_name == settings.chat_model
    assert router.model_name == settings.router_model
    assert answer.model_dump()["extra_body"] == {"enable_thinking": False}
    assert router.model_dump()["extra_body"] == {"enable_thinking": False}
