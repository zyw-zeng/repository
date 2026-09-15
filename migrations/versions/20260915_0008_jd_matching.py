"""增加 JD 岗位匹配分析记录。

迁移版本：20260915_0008
前置版本：20260914_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0008"
down_revision: str | None = "20260914_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建可恢复和查询的 JD 分析表。"""
    op.create_table(
        "jd_analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("job_title", sa.String(length=255), nullable=True),
        sa.Column("requirements_json", sa.JSON(), nullable=True),
        sa.Column("matches_json", sa.JSON(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("completeness", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jd_analyses_request_id", "jd_analyses", ["request_id"], unique=True)
    op.create_index("ix_jd_analyses_status", "jd_analyses", ["status"], unique=False)


def downgrade() -> None:
    """移除 JD 分析记录。"""
    op.drop_index("ix_jd_analyses_status", table_name="jd_analyses")
    op.drop_index("ix_jd_analyses_request_id", table_name="jd_analyses")
    op.drop_table("jd_analyses")
