"""验证推荐问题的小模型生成、持久化和公开主题缓存。"""

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.services.suggestion_service import SuggestionService
from app.storage.models import Conversation, DocumentRecord, Message


def test_empty_suggestions_are_generated_from_public_topics_and_cached(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """相同公开文档版本第二次读取时应直接复用数据库缓存。"""
    model = FakeListChatModel(
        responses=[
            '["这个项目使用了哪些技术？", "ZYW 如何实现可靠引用？", "还可以了解哪些项目？"]'
        ]
    )
    with session_factory() as session:
        session.add(
            DocumentRecord(
                filename="AI Agent 项目说明.md",
                file_hash="a" * 64,
                file_type="md",
                storage_path="/tmp/agent.md",
                status="ready",
                visibility="public",
                active_index_version=2,
            )
        )
        session.commit()
        service = SuggestionService(session, test_settings, model=model)

        generated = service.get_empty_suggestions()
        cached = service.get_empty_suggestions()

    assert generated.source == "generated"
    assert len(generated.suggestions) == 3
    assert cached.source == "cache"
    assert cached.suggestions == generated.suggestions


def test_followups_are_saved_on_latest_assistant_message(
    session_factory: sessionmaker[Session],
    test_settings: Settings,
) -> None:
    """回答后的动态追问应绑定助手消息，并可在刷新会话时恢复。"""
    model = FakeListChatModel(
        responses=[
            '["项目为什么选择 LangGraph？", "引用是如何验证的？", "ZYW 还做过哪些项目？"]'
        ]
    )
    with session_factory() as session:
        conversation = Conversation(title="项目咨询")
        session.add(conversation)
        session.flush()
        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    role="user",
                    content="介绍一下这个项目",
                ),
                Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content="这是一个可靠 RAG 项目。",
                    citations_json=[],
                ),
            ]
        )
        session.commit()

        result = SuggestionService(session, test_settings, model=model).generate_for_answer(
            conversation.id,
            answer_mode="knowledge_base",
            citations=[],
        )
        assistant = next(
            item
            for item in reversed(conversation.messages)
            if item.role == "assistant"
        )

    assert result.source == "generated"
    assert assistant.suggestions_json == result.suggestions
    assert len(result.suggestions) == 3
