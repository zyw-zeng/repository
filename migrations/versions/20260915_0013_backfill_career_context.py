"""为历史会话补充最近完成的 JD 绑定。

迁移版本：20260915_0013
前置版本：20260915_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0013"
down_revision: str | None = "20260915_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """绑定最近报告；旧记录没有档案版本，使用时会要求重新分析。"""
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE conversations
            SET active_jd_analysis_id = (
                    SELECT jd.id
                    FROM jd_analyses AS jd
                    WHERE jd.conversation_id = conversations.id
                      AND jd.status = 'completed'
                    ORDER BY jd.updated_at DESC
                    LIMIT 1
                ),
                career_context_updated_at = (
                    SELECT jd.updated_at
                    FROM jd_analyses AS jd
                    WHERE jd.conversation_id = conversations.id
                      AND jd.status = 'completed'
                    ORDER BY jd.updated_at DESC
                    LIMIT 1
                )
            WHERE active_jd_analysis_id IS NULL
              AND EXISTS (
                    SELECT 1
                    FROM jd_analyses AS jd
                    WHERE jd.conversation_id = conversations.id
                      AND jd.status = 'completed'
                )
            """
        )
    )


def downgrade() -> None:
    """只清除无法证明由新版流程写入的空版本历史绑定。"""
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE conversations
            SET active_jd_analysis_id = NULL,
                career_context_updated_at = NULL
            WHERE candidate_profile_version IS NULL
            """
        )
    )
