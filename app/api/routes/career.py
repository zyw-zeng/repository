"""提供岗位定制求职材料预览与引用报告下载接口。"""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Path
from fastapi.responses import Response

from app.api.dependencies import AppSettings, DatabaseSession
from app.core.exceptions import AppError
from app.schemas.career import CareerMaterialsResponse
from app.services.career_advice_service import CareerAdviceService
from app.storage.repositories.conversations import ConversationRepository

router = APIRouter(prefix="/api/v1/career", tags=["求职顾问"])


def _get_service(
    conversation_id: str,
    session: DatabaseSession,
    settings: AppSettings,
) -> CareerAdviceService:
    """读取绑定岗位的会话并建立统一材料服务。"""
    conversation = ConversationRepository(session).get(conversation_id)
    if conversation is None:
        raise AppError("会话不存在", status_code=404, code="conversation_not_found")
    service = CareerAdviceService(session, settings, conversation)
    if service.context is None:
        raise AppError(
            "当前会话尚未完成岗位分析",
            status_code=409,
            code="career_context_missing",
        )
    if service.context.stale:
        raise AppError(
            "个人档案已更新，请重新分析该岗位后再生成材料",
            status_code=409,
            code="career_context_stale",
        )
    return service


@router.get(
    "/conversations/{conversation_id}/materials",
    response_model=CareerMaterialsResponse,
    summary="生成岗位定制求职材料",
)
def get_career_materials(
    conversation_id: Annotated[str, Path(description="已绑定 JD 的会话 ID。")],
    session: DatabaseSession,
    settings: AppSettings,
) -> CareerMaterialsResponse:
    """返回自我介绍、项目亮点、面试准备和能力补足计划。"""
    bundle = _get_service(conversation_id, session, settings).build_material_bundle()
    for section in bundle["sections"]:
        for index, evidence in enumerate(section["evidence"], start=1):
            evidence["reference_number"] = index
    return CareerMaterialsResponse.model_validate(bundle)


@router.get(
    "/conversations/{conversation_id}/report",
    summary="下载带引用的求职分析报告",
    response_class=Response,
)
def download_career_report(
    conversation_id: Annotated[str, Path(description="已绑定 JD 的会话 ID。")],
    session: DatabaseSession,
    settings: AppSettings,
) -> Response:
    """下载 UTF-8 Markdown 报告，保留正文与引用之间的可审计关系。"""
    service = _get_service(conversation_id, session, settings)
    report = service.render_material_report()
    job_title = service.context.job_title if service.context else "目标岗位"
    filename = quote(f"ZYW-{job_title}-求职分析报告.md")
    return Response(
        content=report.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
