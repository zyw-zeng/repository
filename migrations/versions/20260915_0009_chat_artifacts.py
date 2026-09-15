"""将 JD 分析绑定到会话，并支持聊天内工具卡片。

迁移版本：20260915_0009
前置版本：20260915_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0009"
down_revision: str | None = "20260915_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增加消息结构化产物和 JD 所属会话字段。"""
    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(sa.Column("artifacts_json", sa.JSON(), nullable=True))
    with op.batch_alter_table("jd_analyses") as batch_op:
        batch_op.add_column(sa.Column("conversation_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_jd_analyses_conversation_id",
            "conversations",
            ["conversation_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_jd_analyses_conversation_id", ["conversation_id"])


def downgrade() -> None:
    """移除聊天内 JD 关联字段。"""
    with op.batch_alter_table("jd_analyses") as batch_op:
        batch_op.drop_index("ix_jd_analyses_conversation_id")
        batch_op.drop_constraint("fk_jd_analyses_conversation_id", type_="foreignkey")
        batch_op.drop_column("conversation_id")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_column("artifacts_json")
