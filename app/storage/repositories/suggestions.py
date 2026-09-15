"""持久化会话推荐问题和公开知识库推荐缓存。"""

from sqlalchemy.orm import Session

from app.storage.models import Message, SuggestionCache


class SuggestionRepository:
    """封装推荐结果读写，事务边界由服务层统一管理。"""

    def __init__(self, session: Session):
        """绑定当前数据库工作单元。"""
        self.session = session

    def get_cache(self, cache_key: str) -> SuggestionCache | None:
        """按公开资料签名读取空状态推荐缓存。"""
        return self.session.get(SuggestionCache, cache_key)

    def save_cache(
        self,
        cache_key: str,
        source_signature: str,
        suggestions: list[str],
    ) -> SuggestionCache:
        """新增或覆盖指定知识库版本的推荐缓存。"""
        record = self.get_cache(cache_key)
        if record is None:
            record = SuggestionCache(
                cache_key=cache_key,
                source_signature=source_signature,
                suggestions_json=suggestions,
            )
            self.session.add(record)
        else:
            record.source_signature = source_signature
            record.suggestions_json = suggestions
        self.session.flush()
        return record

    def save_message_suggestions(self, message: Message, suggestions: list[str]) -> None:
        """把推荐问题绑定到产生它们的助手消息。"""
        message.suggestions_json = suggestions
        self.session.flush()
