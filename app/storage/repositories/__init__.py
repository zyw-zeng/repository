"""向服务层提供持久化能力的 Repository。"""

from app.storage.repositories.documents import DocumentRepository
from app.storage.repositories.ingestion_jobs import IngestionJobRepository

__all__ = ["DocumentRepository", "IngestionJobRepository"]
