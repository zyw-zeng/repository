"""定义只调用服务层能力、经过白名单限制的 Agent 工具。"""

from dataclasses import asdict
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from app.knowledge.types import SearchFilters
from app.services.agent_tool_service import AgentToolService

ALLOWED_TOOL_NAMES = {
    "answer_casual",
    "search_knowledge",
    "list_documents",
    "get_document_info",
    "read_document_chunks",
    "summarize_document",
    "get_resume",
}


class AgentToolbox:
    """创建和调用固定白名单工具，不允许动态执行任意函数。"""

    def __init__(self, service: AgentToolService):
        """绑定唯一可访问业务数据的服务门面。"""
        self.service = service
        self.tools = self._build_tools()

    def _build_tools(self) -> dict[str, BaseTool]:
        """把服务方法包装为 LangChain 结构化工具。"""

        def answer_casual(question: str, history: list[tuple[str, str]]) -> dict[str, Any]:
            """回答明确的普通闲聊。"""
            return asdict(self.service.answer_casual(question, history))

        def search_knowledge(
            question: str,
            history: list[tuple[str, str]],
            document_ids: list[str],
            filenames: list[str],
        ) -> dict[str, Any]:
            """搜索 ZYW 的公开知识库并返回经过引用校验的回答。"""
            result = self.service.search_knowledge(
                question,
                history,
                SearchFilters(document_ids=document_ids, filenames=filenames),
            )
            return asdict(result)

        def list_documents() -> list[dict]:
            """列出知识库中的文档摘要。"""
            return self.service.list_documents()

        def get_document_info(reference: str) -> dict:
            """读取指定文档的状态和索引信息。"""
            return self.service.get_document_info(reference)

        def read_document_chunks(reference: str, limit: int = 5) -> list[dict]:
            """读取指定文档活动版本的有限原文切片。"""
            return self.service.read_document_chunks(reference, limit=limit)

        def summarize_document(
            reference: str,
            history: list[tuple[str, str]],
        ) -> dict[str, Any]:
            """基于可靠 RAG 总结一个明确文档。"""
            return asdict(self.service.summarize_document(reference, history))

        def get_resume() -> dict[str, Any]:
            """获取当前公开简历的预览和下载信息。"""
            return self.service.get_resume()

        functions = [
            answer_casual,
            search_knowledge,
            list_documents,
            get_document_info,
            read_document_chunks,
            summarize_document,
            get_resume,
        ]
        return {
            function.__name__: StructuredTool.from_function(function)
            for function in functions
        }

    def invoke(self, name: str, arguments: dict[str, Any]) -> Any:
        """校验白名单后调用工具，未知名称不会被执行。"""
        if name not in ALLOWED_TOOL_NAMES or name not in self.tools:
            raise ValueError(f"不允许调用工具：{name}")
        return self.tools[name].invoke(arguments)
