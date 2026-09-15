"""增加 JD 已验证能力匹配率。

迁移版本：20260915_0010
前置版本：20260915_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0010"
down_revision: str | None = "20260915_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """保存只基于已有证据计算的匹配率。"""
    with op.batch_alter_table("jd_analyses") as batch_op:
        batch_op.add_column(sa.Column("verified_fit", sa.Float(), nullable=True))


def downgrade() -> None:
    """移除已验证匹配率。"""
    with op.batch_alter_table("jd_analyses") as batch_op:
        batch_op.drop_column("verified_fit")
