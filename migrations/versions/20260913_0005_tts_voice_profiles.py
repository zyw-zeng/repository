"""增加三个精灵角色的 CosyVoice 音色配置。

迁移版本：20260913_0005
前置版本：20260912_0004
创建日期：2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0005"
down_revision: str | None = "20260912_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建角色音色表，并让三个角色默认启用自动朗读。"""
    table = op.create_table(
        "tts_voice_profiles",
        sa.Column("character_id", sa.String(length=20), primary_key=True),
        sa.Column("display_name", sa.String(length=30), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("voice", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_speak", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.bulk_insert(
        table,
        [
            {
                "character_id": "nova",
                "display_name": "星云",
                "model": "cosyvoice-v3-flash",
                "voice": "longanyang",
                "enabled": True,
                "auto_speak": True,
            },
            {
                "character_id": "byte",
                "display_name": "比特",
                "model": "cosyvoice-v3-flash",
                "voice": "longanyang",
                "enabled": True,
                "auto_speak": True,
            },
            {
                "character_id": "momo",
                "display_name": "沫沫",
                "model": "cosyvoice-v3-flash",
                "voice": "longanyang",
                "enabled": True,
                "auto_speak": True,
            },
        ],
    )


def downgrade() -> None:
    """移除角色音色配置。"""
    op.drop_table("tts_voice_profiles")
