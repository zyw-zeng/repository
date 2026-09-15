"""声明可复用的 FastAPI 依赖类型。"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.security import verify_admin_token
from app.storage.database import get_db_session

# 路由函数声明 DatabaseSession 后，会自动获得请求级数据库会话。
DatabaseSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]

# 不让 HTTPBearer 自动返回非统一结构的错误，由项目异常处理器负责响应。
admin_bearer = HTTPBearer(auto_error=False)


def require_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(admin_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """要求请求携带有效的管理员 Bearer 令牌。"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("需要管理员登录", status_code=401, code="admin_auth_required")
    verify_admin_token(credentials.credentials, settings)


AdminAuthorization = Annotated[None, Depends(require_admin)]
