"""实现会话和消息的持久化操作。"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.storage.models import Conversation, Message, utc_now


class ConversationRepository:
    """封装会话和消息查询，事务提交由服务层负责。"""

    def __init__(self, session: Session):
        """绑定一次请求使用的数据库会话。"""
        self.session = session

    def add(self, conversation: Conversation) -> Conversation:
        """创建会话并立即生成公开 ID。"""
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        """按 ID 读取会话。"""
        return self.session.get(Conversation, conversation_id)

    def list_conversations(self, *, offset: int = 0, limit: int = 50) -> list[Conversation]:
        """按最近更新时间倒序返回会话，供受保护的管理入口使用。"""
        statement = (
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .offset(max(0, offset))
            .limit(min(max(1, limit), 100))
        )
        return list(self.session.scalars(statement))

    def delete(self, conversation_id: str) -> bool:
        """删除会话及级联消息，返回是否确实删除了记录。"""
        result = self.session.execute(
            delete(Conversation).where(Conversation.id == conversation_id)
        )
        return bool(result.rowcount)

    def add_message(self, message: Message) -> Message:
        """追加消息并刷新会话更新时间。"""
        self.session.add(message)
        conversation = self.get(message.conversation_id)
        if conversation is not None:
            conversation.updated_at = utc_now()
        self.session.flush()
        return message

    def list_messages(self, conversation_id: str, *, limit: int = 20) -> list[Message]:
        """按时间正序返回最近若干条消息。"""
        recent_ids = (
            select(Message.id)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(max(1, limit))
            .subquery()
        )
        statement = (
            select(Message)
            .where(Message.id.in_(select(recent_ids.c.id)))
            .order_by(Message.created_at)
        )
        return list(self.session.scalars(statement))
