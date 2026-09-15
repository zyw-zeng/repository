"""向 Agent 工具提供受控的知识库和文档服务能力。"""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.knowledge.types import RagAnswer, SearchFilters
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.resume_service import ResumeService
from app.storage.models import DocumentRecord
from app.storage.repositories.documents import DocumentRepository


class AgentToolService:
    """隔离 Agent 工具与 SQLite、Chroma 和文件系统实现细节。"""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        chat_service: ChatService | None = None,
    ):
        """组装工具允许调用的服务；测试可注入可靠 RAG 替身。"""
        self.settings = settings or get_settings()
        self.documents = DocumentService(session, self.settings)
        self.document_repository = DocumentRepository(session)
        # 确定性工具（如简历下载）不应为未使用的问答模型付出初始化成本。
        self._chat = chat_service
        self.resume = ResumeService(self.settings)

    @property
    def chat(self) -> ChatService:
        """仅在真正执行闲聊或知识检索时创建模型与向量依赖。"""
        if self._chat is None:
            self._chat = ChatService(self.session, self.settings)
        return self._chat

    def answer_casual(
        self,
        question: str,
        history: Sequence[tuple[str, str]],
    ) -> RagAnswer:
        """明确使用闲聊模式回答，不产生知识库引用。"""
        return self.chat.ask(question, mode="casual", history=history)

    def search_knowledge(
        self,
        question: str,
        history: Sequence[tuple[str, str]],
        filters: SearchFilters,
    ) -> RagAnswer:
        """强制通过可靠 RAG 服务搜索知识库并生成受支持回答。"""
        return self.chat.ask(
            question,
            mode="knowledge_base",
            history=history,
            filters=filters,
        )

    def list_documents(self) -> list[dict]:
        """返回 Agent 可以公开使用的文档摘要，不暴露内部存储路径。"""
        return [
            {
                "id": document.id,
                "filename": document.filename,
                "status": document.status,
                "chunk_count": document.chunk_count,
                "active_index_version": document.active_index_version,
            }
            for document in self.document_repository.list(limit=100, public_only=True)
        ]

    def get_document_info(self, reference: str) -> dict:
        """根据文档 ID、完整文件名或问题中提到的文件名查找文档。"""
        document = self._resolve_document(reference)
        return {
            "id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "status": document.status,
            "size_bytes": document.size_bytes,
            "chunk_count": document.chunk_count,
            "active_index_version": document.active_index_version,
        }

    def read_document_chunks(self, reference: str, *, limit: int = 5) -> list[dict]:
        """读取指定文档活动版本的有限切片，禁止任意文件访问。"""
        document = self._resolve_document(reference)
        chunks = self.document_repository.get_chunks_for_version(
            document.id,
            document.active_index_version,
        )
        return [
            {
                "chunk_id": chunk.id,
                "heading": chunk.heading,
                "page_number": chunk.page_number,
                "content": chunk.content,
                "index_version": chunk.index_version,
            }
            for chunk in chunks[: min(max(1, limit), 10)]
        ]

    def summarize_document(
        self,
        reference: str,
        history: Sequence[tuple[str, str]],
    ) -> RagAnswer:
        """把摘要请求限制在解析出的单个文档 ID 内。"""
        document = self._resolve_document(reference)
        return self.search_knowledge(
            f"请总结文档《{document.filename}》的主要内容。",
            history,
            SearchFilters(document_ids=[document.id]),
        )

    def get_resume(self) -> dict:
        """返回公开简历资源；Agent 不直接接触文件系统路径。"""
        return self.resume.get_public_info().model_dump(mode="json")

    def _resolve_document(self, reference: str) -> DocumentRecord:
        """只从文档服务可见记录中解析用户给出的文档引用。"""
        normalized = reference.strip()
        for document in self.document_repository.list(limit=100, public_only=True):
            if document.id == normalized or document.filename == normalized:
                return document
            if document.filename and document.filename in normalized:
                return document
        raise AppError(
            "无法确定要操作的文档，请提供文档 ID 或完整文件名",
            status_code=404,
            code="document_reference_not_found",
        )
