"""定义模型供应商必须满足的最小接口。"""

from typing import Protocol

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel


class ModelProvider(Protocol):
    """可替换模型供应商需要实现的协议。"""

    def create_chat_model(self) -> BaseChatModel:
        """创建供 Agent 和问答服务使用的对话模型。"""
        ...

    def create_embeddings(self) -> Embeddings:
        """创建供文档入库和查询向量化使用的模型。"""
        ...
