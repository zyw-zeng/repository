"""创建 FastAPI 应用并管理服务生命周期。"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.workers.ingestion import recover_and_run_pending_jobs

API_DESCRIPTION = """
ZYW 的 AI 小助理后端 API。

这是面向访客了解 ZYW 及其项目的知识库助手，当前提供文档管理、可靠 RAG 问答和有状态 LangGraph Agent。
文档操作采用异步任务：接口返回 `202 Accepted` 后，客户端通过 `job_id` 查询处理进度。

任务状态通常按照 `pending → parsing → chunking → embedding → completed` 流转；
失败时状态为 `failed`，并通过 `error_message` 返回可读原因。

Agent 只调用白名单工具，知识检索受重试、步骤、时间和递归上限约束；
每次执行都会返回 `run_id`、精简步骤和降级状态，并持久化到会话记录。
"""

OPENAPI_TAGS = [
    {"name": "系统", "description": "应用存活和本地依赖就绪检查。"},
    {"name": "认证", "description": "管理端登录和登录状态验证。"},
    {"name": "文档管理", "description": "管理员上传、查看、公开、重新索引和删除文档。"},
    {"name": "文档任务", "description": "管理员查询文档后台处理任务状态与进度。"},
    {"name": "会话", "description": "可靠 RAG 知识问答和明确标记的闲聊模式。"},
    {"name": "Agent", "description": "ZYW 的 AI 小助理会话、工具选择和流式执行。"},
    {"name": "岗位匹配", "description": "使用独立 LangGraph 对 JD 与公开知识库证据进行可靠匹配。"},
    {"name": "求职顾问", "description": "生成岗位定制求职材料并导出带引用的分析报告。"},
    {"name": "推荐问题", "description": "根据公开知识主题与当前会话动态生成后续问题。"},
    {"name": "语音", "description": "使用 CosyVoice 朗读回答并控制合成任务。"},
    {"name": "个人简历", "description": "公开简历信息、在线预览和安全下载。"},
    {"name": "系统诊断", "description": "管理员主动触发的模型和外部依赖诊断。"},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    """初始化目录，并在后台恢复上次中断的文档任务。"""
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.ensure_local_directories()
    recovery_task = asyncio.create_task(asyncio.to_thread(recover_and_run_pending_jobs, settings))
    yield
    # 正常关闭时等待已经启动的恢复扫描结束，避免任务状态停在未知位置。
    await recovery_task


def create_app() -> FastAPI:
    """组装中间件、异常处理器和 API 路由。"""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=API_DESCRIPTION,
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url="/docs",
        # 当前项目统一使用 Swagger，关闭重复的 ReDoc 页面。
        redoc_url=None,
        openapi_tags=OPENAPI_TAGS,
    )
    # 请求 ID 中间件需要先注册，确保后续日志和响应都能关联一次请求。
    application.add_middleware(RequestIdMiddleware)
    register_exception_handlers(application)
    application.include_router(api_router)

    @application.get("/", include_in_schema=False)
    def open_api_documentation() -> RedirectResponse:
        """访问根路径时直接跳转到 Swagger API 文档。"""
        return RedirectResponse(url="/docs")

    return application


app = create_app()
