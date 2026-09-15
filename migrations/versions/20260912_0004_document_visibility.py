"""增加文档公开范围，历史文档按最安全策略设为私有。

迁移版本：20260912_0004
前置版本：20260912_0003
创建日期：2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_0004"
down_revision: str | None = "20260912_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """新增可见性字段，现有和未来文档默认不向访客公开。"""
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "visibility",
                sa.String(length=20),
                nullable=False,
                server_default="private",
            )
        )
        batch_op.create_index("ix_documents_visibility", ["visibility"], unique=False)


def downgrade() -> None:
    """移除文档公开范围字段和索引。"""
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_index("ix_documents_visibility")
        batch_op.drop_column("visibility")
