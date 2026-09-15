"""提供阶段 3 的可靠 RAG 问答接口。"""

from fastapi import APIRouter, status

from app.api.dependencies import DatabaseSession
from app.core.middleware import request_id_context
from app.knowledge.types import SearchFilters
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.errors import ErrorResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["会话"])


@router.post(
    "/query",
    response_model=ChatResponse,
    summary="执行知识库问答或闲聊",
    description=(
        "knowledge_base 模式强制执行查询改写、向量检索和引用校验；"
        "没有可靠依据时返回 grounded=false。casual 模式不查询知识库。"
    ),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "模型密钥未配置或模型服务不可用。",
        }
    },
)
def query_knowledge(request: ChatRequest, session: DatabaseSession) -> ChatResponse:
    """调用可靠 RAG 服务，并附带当前请求的追踪 ID。"""
    result = ChatService(session).ask(
        request.question,
        mode=request.mode,
        history=[(message.role, message.content) for message in request.history],
        filters=SearchFilters(
            document_ids=request.filters.document_ids,
            filenames=request.filters.filenames,
        ),
    )
    return ChatResponse(
        answer=result.answer,
        answer_mode=result.answer_mode,
        grounded=result.grounded,
        rewritten_query=result.rewritten_query,
        citations=result.citations,
        retrieved_count=result.retrieved_count,
        request_id=request_id_context.get(),
    )
