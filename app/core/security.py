"""提供不依赖外部服务的管理端密码校验和签名令牌。"""

import base64
import binascii
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.config import Settings
from app.core.exceptions import AppError


def _encode_base64(value: bytes) -> str:
    """生成适合放入 HTTP 头的无填充 URL 安全 Base64。"""
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_base64(value: str) -> bytes:
    """恢复被省略的 Base64 填充并解码。"""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _require_auth_configuration(settings: Settings) -> None:
    """拒绝在未设置管理员凭据时误开放管理接口。"""
    if not settings.admin_password or not settings.auth_secret_key:
        raise AppError(
            "管理员认证尚未配置",
            status_code=503,
            code="admin_auth_not_configured",
        )


def authenticate_admin(password: str, settings: Settings) -> str:
    """校验管理员密码并签发带到期时间的 HMAC 令牌。"""
    _require_auth_configuration(settings)
    if not hmac.compare_digest(password.encode("utf-8"), settings.admin_password.encode("utf-8")):
        raise AppError("管理员密码错误", status_code=401, code="invalid_credentials")

    payload = {
        "role": "admin",
        "exp": int(time.time()) + settings.admin_token_ttl_minutes * 60,
    }
    encoded_payload = _encode_base64(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_encode_base64(signature)}"


def verify_admin_token(token: str, settings: Settings) -> dict[str, Any]:
    """验证令牌签名、角色和有效期，失败时返回统一 401。"""
    _require_auth_configuration(settings)
    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        expected_signature = hmac.new(
            settings.auth_secret_key.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        supplied_signature = _decode_base64(encoded_signature)
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise ValueError("签名不匹配")
        payload = json.loads(_decode_base64(encoded_payload))
        if payload.get("role") != "admin" or int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("令牌无效或已过期")
        return payload
    except AppError:
        raise
    except (binascii.Error, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise AppError(
            "管理员登录状态无效或已过期",
            status_code=401,
            code="invalid_admin_token",
        ) from exc
