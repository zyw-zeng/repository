"""增加 JD 求职可行度指标。

迁移版本：20260915_0011
前置版本：20260915_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0011"
down_revision: str | None = "20260915_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """保存考虑必备项和证据覆盖率的求职可行度。"""
    with op.batch_alter_table("jd_analyses") as batch_op:
        batch_op.add_column(sa.Column("feasibility", sa.Float(), nullable=True))


def downgrade() -> None:
    """移除求职可行度字段。"""
    with op.batch_alter_table("jd_analyses") as batch_op:
        batch_op.drop_column("feasibility")
