"""增加推荐问题持久化字段和空状态缓存表。

迁移版本：20260913_0006
前置版本：20260913_0005
创建日期：2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0006"
down_revision: str | None = "20260913_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为助手消息增加推荐结果，并创建公开知识库推荐缓存。"""
    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(sa.Column("suggestions_json", sa.JSON(), nullable=True))

    op.create_table(
        "suggestion_caches",
        sa.Column("cache_key", sa.String(length=80), primary_key=True),
        sa.Column("suggestions_json", sa.JSON(), nullable=False),
        sa.Column("source_signature", sa.String(length=64), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_suggestion_caches_source_signature",
        "suggestion_caches",
        ["source_signature"],
        unique=False,
    )


def downgrade() -> None:
    """移除推荐缓存和消息推荐字段。"""
    op.drop_index(
        "ix_suggestion_caches_source_signature",
        table_name="suggestion_caches",
    )
    op.drop_table("suggestion_caches")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_column("suggestions_json")
