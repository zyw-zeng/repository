"""需要主动触发的模型与外部依赖诊断接口。"""

from fastapi import APIRouter, Depends

from app.api.dependencies import require_admin

router = APIRouter(
    prefix="/diagnostics",
    tags=["系统诊断"],
    dependencies=[Depends(require_admin)],
)
