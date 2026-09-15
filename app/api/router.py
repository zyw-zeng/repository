"""集中注册应用的所有 HTTP 路由。"""

from fastapi import APIRouter

from app.api.routes import (
    agent,
    auth,
    career,
    chat,
    diagnostics,
    documents,
    health,
    jd_matching,
    jobs,
    resume,
    suggestions,
    tts,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(diagnostics.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
api_router.include_router(chat.router)
api_router.include_router(agent.router)
api_router.include_router(jd_matching.router)
api_router.include_router(career.router)
api_router.include_router(suggestions.router)
api_router.include_router(tts.router)
api_router.include_router(resume.router)
