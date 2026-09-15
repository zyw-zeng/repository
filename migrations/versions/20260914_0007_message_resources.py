"""为会话消息增加结构化资源字段。

迁移版本：20260914_0007
前置版本：20260913_0006
创建日期：2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0007"
down_revision: str | None = "20260913_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """保存 Agent 返回的简历等结构化资源。"""
    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(sa.Column("resources_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    """移除消息资源字段。"""
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_column("resources_json")
