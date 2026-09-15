"""增加文档入库任务、权威切片正文和索引版本。

迁移版本：20260912_0002
前置版本：20260912_0001
创建日期：2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_0002"
down_revision: str | None = "20260912_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """扩展文档与切片表，并创建持久化入库任务表。"""
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("active_index_version", sa.Integer(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("document_chunks", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("index_version", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(sa.Column("content", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(
            sa.Column("token_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("start_offset", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("end_offset", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint(
            "uq_document_chunk_version_index",
            ["document_id", "index_version", "chunk_index"],
        )

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("operation", sa.String(length=20), nullable=False),
        sa.Column("target_index_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_jobs_document_id", "ingestion_jobs", ["document_id"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])


def downgrade() -> None:
    """删除文档入库任务，并恢复初始文档与切片结构。"""
    op.drop_index("ix_ingestion_jobs_status", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_document_id", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")

    with op.batch_alter_table("document_chunks", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_document_chunk_version_index", type_="unique")
        batch_op.drop_column("created_at")
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("end_offset")
        batch_op.drop_column("start_offset")
        batch_op.drop_column("token_count")
        batch_op.drop_column("content")
        batch_op.drop_column("index_version")

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("active_index_version")
        batch_op.drop_column("size_bytes")
