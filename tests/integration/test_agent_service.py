"""Agent 会话、消息和运行轨迹持久化集成测试。"""

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.agent.runtime import bind_agent_runtime
from app.core.config import Settings
from app.knowledge.types import RagAnswer
from app.services.agent_service import AgentService
from app.storage.models import AgentRun, Message
from tests.unit.test_agent_graph import StubAgentToolService


def test_agent_persists_conversation_messages_and_run(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """成功执行后应同时保存两条消息和完整节点轨迹。"""
    with session_factory() as session:
        service = AgentService(
            session,
            test_settings,
            model=FakeListChatModel(responses=["answer_casual"]),
            tool_service=StubAgentToolService(),
        )
        conversation = service.create_conversation()
        result = service.run(conversation.id, "你好", "request-agent-1")

        messages = list(
            session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at)
            )
        )
        run = session.scalar(select(AgentRun).where(AgentRun.request_id == "request-agent-1"))

    assert result.degraded is False
    assert result.timings["total_ms"] >= 0
    assert "router_ms" in result.timings
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[1].content == "你好"
    assert run is not None
    assert run.status == "completed"
    assert len(run.tool_calls_json or []) == 2


def test_agent_tool_failure_is_persisted_as_degraded(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """工具异常应可控退出，并保存降级消息和失败步骤。"""

    class FailingToolService(StubAgentToolService):
        """模拟知识库服务暂时不可用。"""

        def search_knowledge(self, question: str, history: object, filters: object) -> RagAnswer:
            """始终抛出连接错误。"""
            raise ConnectionError("测试连接失败")

    with session_factory() as session:
        service = AgentService(
            session,
            test_settings,
            model=FakeListChatModel(responses=["search_knowledge"]),
            tool_service=FailingToolService(),
        )
        conversation = service.create_conversation("失败测试")
        result = service.run(conversation.id, "查询资料", "request-agent-2")
        run = session.scalar(select(AgentRun).where(AgentRun.request_id == "request-agent-2"))

    assert result.degraded is True
    assert result.grounded is False
    assert run is not None
    assert run.status == "degraded"
    assert run.tool_calls_json[-1]["status"] == "failed"


def test_agent_cancellation_is_persisted_separately_from_failure(
    session_factory: sessionmaker[Session], test_settings: Settings
) -> None:
    """用户取消应保存 cancelled 状态，并且不伪装成系统故障。"""
    with session_factory() as session:
        service = AgentService(
            session,
            test_settings,
            model=FakeListChatModel(responses=[]),
            tool_service=StubAgentToolService(),
        )
        conversation = service.create_conversation("取消测试")
        with bind_agent_runtime(lambda _event, _data: None, lambda: True):
            result = service.run(conversation.id, "停止这个回答", "request-agent-cancel")
        run = session.scalar(
            select(AgentRun).where(AgentRun.request_id == "request-agent-cancel")
        )

    assert result.cancelled is True
    assert result.answer == "回答已停止。"
    assert run is not None
    assert run.status == "cancelled"


def test_resume_tool_runs_without_model_and_persists_resource(
    session_factory: sessionmaker[Session], test_settings: Settings, tmp_path
) -> None:
    """固定简历工具不依赖模型密钥，并应保存可恢复的资源卡片数据。"""
    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"%PDF-1.7\nresume\n")
    settings = test_settings.model_copy(update={"resume_file_path": resume_path})

    with session_factory() as session:
        service = AgentService(session, settings)
        conversation = service.create_conversation("简历测试")
        result = service.run(conversation.id, "请把简历 PDF 发给我", "request-resume")
        messages = list(
            session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at)
            )
        )

    assert result.degraded is False
    assert result.resources[0]["type"] == "resume"
    assert messages[1].resources_json == result.resources
