"""为会话增加当前求职岗位和档案版本。

迁移版本：20260915_0012
前置版本：20260915_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0012"
down_revision: str | None = "20260915_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """保存会话当前绑定的 JD、档案版本和更新时间。"""
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.add_column(sa.Column("active_jd_analysis_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("candidate_profile_version", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("career_context_updated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index(
            "ix_conversations_active_jd_analysis_id",
            ["active_jd_analysis_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_conversations_active_jd_analysis_id",
            "jd_analyses",
            ["active_jd_analysis_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """移除会话求职上下文。"""
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.drop_constraint("fk_conversations_active_jd_analysis_id", type_="foreignkey")
        batch_op.drop_index("ix_conversations_active_jd_analysis_id")
        batch_op.drop_column("career_context_updated_at")
        batch_op.drop_column("candidate_profile_version")
        batch_op.drop_column("active_jd_analysis_id")
