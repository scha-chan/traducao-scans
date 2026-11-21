"""Tabela processing_logs — log granular de etapas do pipeline

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-05
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


_CREATE_LOG_LEVEL = """
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'log_level') THEN
    CREATE TYPE log_level AS ENUM ('INFO', 'WARNING', 'ERROR', 'SUCCESS');
  END IF;
END $$
"""


def upgrade() -> None:
    op.execute(_CREATE_LOG_LEVEL)

    op.create_table(
        "processing_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_runs.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "page_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pages.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "level",
            sa.Enum("INFO", "WARNING", "ERROR", "SUCCESS", name="log_level", create_type=False),
            nullable=False,
            server_default="INFO",
        ),
        sa.Column("stage", sa.String(64), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("processing_logs")
    op.execute("DROP TYPE IF EXISTS log_level")
