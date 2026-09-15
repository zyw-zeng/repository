"""测试共享夹具，所有数据库和文件都隔离在 pytest 临时目录。"""

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.security import authenticate_admin
from app.storage.database import Base


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """创建不读取真实 .env 的隔离配置。"""
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        documents_path=tmp_path / "documents",
        chroma_path=tmp_path / "chroma",
        chroma_collection="test_knowledge",
        chunk_size=80,
        chunk_overlap=10,
        ingestion_max_attempts=2,
        admin_password="test-admin-password",
        auth_secret_key="test-auth-secret-key-with-at-least-32-bytes",
    )


@pytest.fixture
def admin_headers(test_settings: Settings) -> dict[str, str]:
    """生成管理接口测试使用的有效 Bearer 请求头。"""
    token = authenticate_admin(test_settings.admin_password, test_settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def session_factory(test_settings: Settings) -> Generator[sessionmaker[Session], None, None]:
    """创建启用外键约束的临时 SQLite 会话工厂。"""
    engine = create_engine(test_settings.database_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _) -> None:
        """确保测试行为与应用中的 SQLite 配置一致。"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()
