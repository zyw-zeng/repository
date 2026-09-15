"""统一文档切片创建时间的非空约束。

迁移版本：20260912_0003
前置版本：20260912_0002
创建日期：2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_0003"
down_revision: str | None = "20260912_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """补齐历史空值，并把切片创建时间改为非空。"""
    op.execute(
        sa.text(
            "UPDATE document_chunks SET created_at = CURRENT_TIMESTAMP "
            "WHERE created_at IS NULL"
        )
    )
    with op.batch_alter_table("document_chunks", recreate="always") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )


def downgrade() -> None:
    """允许切片创建时间为空，以恢复上一版本结构。"""
    with op.batch_alter_table("document_chunks", recreate="always") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )
