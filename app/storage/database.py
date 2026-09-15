"""创建数据库引擎、ORM 基类和请求级数据库会话。"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
# SQLite 默认限制连接只能在创建它的线程中使用；FastAPI 会在线程池中执行同步路由。
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _) -> None:
        """为每个 SQLite 连接启用外键约束和级联行为。"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# 提交后保留 ORM 对象字段，方便服务层继续构造响应。
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 SQLAlchemy ORM 实体的声明基类。"""

    pass


def create_database_schema() -> None:
    """创建缺失的数据表，仅供测试或临时环境使用。

    正式环境使用 Alembic 迁移，避免数据库结构脱离版本管理。
    """
    # 导入实体后，SQLAlchemy 才能在 Base.metadata 中发现所有表。
    from app.storage import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """为一次请求提供数据库会话，并在请求结束后自动关闭。"""
    with SessionLocal() as session:
        yield session
