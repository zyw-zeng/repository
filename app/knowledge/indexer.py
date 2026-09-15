"""实现带版本控制的 Chroma 向量写入、查询与幂等清理。"""

import hashlib
from collections.abc import Sequence

import chromadb
from langchain_core.embeddings import Embeddings

from app.core.config import Settings, get_settings
from app.knowledge.types import ChunkDraft
from app.llm.factory import create_embeddings


def build_vector_id(
    *, document_id: str, index_version: int, chunk_index: int, content_hash: str
) -> str:
    """根据文档、版本、位置和内容生成可重复计算的稳定向量 ID。"""
    identity = f"{document_id}:{index_version}:{chunk_index}:{content_hash}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


class VectorIndexer:
    """封装 Chroma 和 Embedding，避免服务层依赖向量库细节。"""

    def __init__(
        self,
        settings: Settings | None = None,
        embeddings: Embeddings | None = None,
    ):
        """连接持久化 Chroma；允许测试注入本地假 Embedding。"""
        self.settings = settings or get_settings()
        # 延迟创建远程模型，使删除索引和健康检查不要求配置 API Key。
        self.embeddings = embeddings
        client = chromadb.PersistentClient(path=str(self.settings.chroma_path))
        self.collection = client.get_or_create_collection(
            name=self.settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def _get_embeddings(self) -> Embeddings:
        """首次需要向量计算时再创建远程 Embedding 客户端。"""
        if self.embeddings is None:
            self.embeddings = create_embeddings(self.settings)
        return self.embeddings

    def upsert_chunks(
        self,
        *,
        document_id: str,
        filename: str,
        index_version: int,
        chunks: Sequence[ChunkDraft],
    ) -> list[str]:
        """向量化并幂等写入一个文档版本的全部切片。"""
        vector_ids = [
            build_vector_id(
                document_id=document_id,
                index_version=index_version,
                chunk_index=chunk.chunk_index,
                content_hash=chunk.content_hash,
            )
            for chunk in chunks
        ]
        embedding_inputs = [
            f"{chunk.heading}\n{chunk.content}" if chunk.heading else chunk.content
            for chunk in chunks
        ]
        vectors = self._get_embeddings().embed_documents(embedding_inputs)
        metadatas = []
        for chunk in chunks:
            metadata: dict[str, str | int | float | bool] = {
                "document_id": document_id,
                "filename": filename,
                "index_version": index_version,
                "chunk_index": chunk.chunk_index,
            }
            if chunk.page_number is not None:
                metadata["page_number"] = chunk.page_number
            if chunk.heading:
                metadata["heading"] = chunk.heading
            metadatas.append(metadata)

        self.collection.upsert(
            ids=vector_ids,
            embeddings=vectors,
            documents=[chunk.content for chunk in chunks],
            metadatas=metadatas,
        )
        return vector_ids

    def query_ids(
        self,
        query: str,
        *,
        fetch_k: int = 20,
        where: dict | None = None,
    ) -> list[tuple[str, float]]:
        """返回候选向量 ID 与余弦距离，最终有效性由 SQLite 再次校验。"""
        query_vector = self._get_embeddings().embed_query(query)
        query_arguments = {
            "query_embeddings": [query_vector],
            "n_results": max(1, fetch_k),
            "include": ["distances"],
        }
        # Chroma 不接受值为 None 的 where，因此只在确有过滤条件时传入。
        if where:
            query_arguments["where"] = where
        result = self.collection.query(
            **query_arguments,
        )
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return list(zip(ids, distances, strict=False))

    def delete_vectors(self, vector_ids: Sequence[str]) -> None:
        """幂等删除指定向量；空列表不会访问 Chroma。"""
        if vector_ids:
            self.collection.delete(ids=list(vector_ids))

    def delete_document_version(self, document_id: str, index_version: int) -> None:
        """清理指定文档版本可能残留的全部向量。"""
        self.collection.delete(
            where={
                "$and": [
                    {"document_id": {"$eq": document_id}},
                    {"index_version": {"$eq": index_version}},
                ]
            }
        )
