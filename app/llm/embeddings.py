"""构建兼容 OpenAI 协议的文本向量模型客户端。"""

from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings


def build_embeddings(settings: Settings, api_key: str) -> OpenAIEmbeddings:
    """根据应用配置创建 Embedding 模型；不在此处发起网络请求。"""
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=api_key,
        base_url=settings.model_base_url,
        dimensions=settings.embedding_dimensions,
        # 百炼 Embedding 接口单次最多接收 20 条文本，长文档必须自动分批。
        chunk_size=settings.embedding_batch_size,
        # 百炼兼容接口只接受字符串或字符串列表，不能接收预分词后的整数 Token 数组。
        check_embedding_ctx_length=False,
        timeout=settings.model_timeout_seconds,
        max_retries=settings.model_max_retries,
    )
