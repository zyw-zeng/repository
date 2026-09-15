"""兼容入口，支持使用 ``uvicorn main:app`` 启动服务。"""

from app.main import app

__all__ = ["app"]
