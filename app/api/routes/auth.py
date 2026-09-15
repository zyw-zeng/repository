"""提供管理端登录和登录状态验证接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import AdminAuthorization
from app.core.config import Settings, get_settings
from app.core.security import authenticate_admin
from app.schemas.auth import AdminLoginRequest, AdminProfileResponse, AdminTokenResponse
from app.schemas.errors import ErrorResponse

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post(
    "/login",
    response_model=AdminTokenResponse,
    summary="管理员登录",
    responses={401: {"model": ErrorResponse, "description": "管理员密码错误。"}},
)
def login(
    request: AdminLoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminTokenResponse:
    """校验环境变量中的管理员密码并签发短期令牌。"""
    token = authenticate_admin(request.password, settings)
    return AdminTokenResponse(
        access_token=token,
        expires_in=settings.admin_token_ttl_minutes * 60,
    )


@router.get(
    "/me",
    response_model=AdminProfileResponse,
    summary="验证管理员登录状态",
    responses={401: {"model": ErrorResponse, "description": "登录状态无效或已过期。"}},
)
def get_current_admin(_: AdminAuthorization) -> AdminProfileResponse:
    """令牌验证通过后返回最小管理员身份信息。"""
    return AdminProfileResponse()
