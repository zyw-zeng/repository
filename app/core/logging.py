"""配置包含请求 ID 的统一应用日志。"""

import logging

from app.core.middleware import request_id_context


class RequestIdFilter(logging.Filter):
    """把当前请求 ID 注入每一条日志记录。"""

    def filter(self, record: logging.LogRecord) -> bool:
        """补充格式化器所需字段，并允许日志继续输出。"""
        record.request_id = request_id_context.get()  # type: ignore[attr-defined]
        return True


def configure_logging(level: str) -> None:
    """按照配置的级别初始化根日志处理器。"""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s")
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())
    root_logger.handlers = [handler]
