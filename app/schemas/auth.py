"""管理端认证接口的数据结构。"""

from typing import Literal

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    """管理员登录请求。"""

    password: str = Field(min_length=1, max_length=256, description="管理员密码。")


class AdminTokenResponse(BaseModel):
    """登录成功后返回的短期访问令牌。"""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="令牌剩余有效秒数。")


class AdminProfileResponse(BaseModel):
    """当前管理端身份。"""

    role: Literal["admin"] = "admin"
