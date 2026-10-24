"""F2-DB-01: processing_runs, text_blocks e translation_suggestions

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NOW = sa.text("now()")
_DT = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("CREATE TYPE run_type AS ENUM ('FULL', 'TRANSLATE_ONLY')")
    op.execute("CREATE TYPE run_status AS ENUM ('PENDING', 'RUNNING', 'SUCCESS', 'ERROR')")
    op.execute("CREATE TYPE review_status AS ENUM ('PENDING', 'NEEDS_REVIEW', 'REVIEWED')")
    op.execute("CREATE TYPE block_source AS ENUM ('AUTO', 'MANUAL')")
    op.execute("CREATE TYPE orientation AS ENUM ('VERTICAL', 'HORIZONTAL')")

    _run_type = sa.Enum("FULL", "TRANSLATE_ONLY", name="run_type", create_type=False)
    _run_status = sa.Enum(
        "PENDING", "RUNNING", "SUCCESS", "ERROR", name="run_status", create_type=False
    )
    _review_status = sa.Enum(
        "PENDING", "NEEDS_REVIEW", "REVIEWED", name="review_status", create_type=False
    )
    _block_source = sa.Enum("AUTO", "MANUAL", name="block_source", create_type=False)
    _orientation = sa.Enum("VERTICAL", "HORIZONTAL", name="orientation", create_type=False)

    op.create_table(
        "processing_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("page_id", sa.UUID(), nullable=False),
        sa.Column("run_type", _run_type, nullable=False),
        sa.Column("status", _run_status, nullable=False, server_default="PENDING"),
        sa.Column("started_at", _DT, nullable=True),
        sa.Column("finished_at", _DT, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("model_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("prompt_version", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_processing_runs_page_id", "processing_runs", ["page_id"])
    op.create_index("ix_processing_runs_status", "processing_runs", ["status"])

    op.create_table(
        "text_blocks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("page_id", sa.UUID(), nullable=False),
        sa.Column("processing_run_id", sa.UUID(), nullable=True),
        sa.Column("order_number", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(1), nullable=True),
        sa.Column("original", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("lines", postgresql.JSONB(), nullable=True),
        sa.Column("orientation", _orientation, nullable=True),
        sa.Column("ruby", postgresql.JSONB(), nullable=True),
        sa.Column("handwritten", sa.Boolean(), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("review_status", _review_status, nullable=False, server_default="PENDING"),
        sa.Column("source", _block_source, nullable=False, server_default="AUTO"),
        sa.Column("created_at", _DT, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _DT, server_default=_NOW, nullable=False),
        sa.CheckConstraint("type IN ('#', '$')", name="ck_text_blocks_type"),
        sa.ForeignKeyConstraint(["page_id"], ["pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_run_id"], ["processing_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "page_id",
            "order_number",
            name="uq_text_blocks_page_order",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index("ix_text_blocks_page_id", "text_blocks", ["page_id"])
    op.create_index("ix_text_blocks_processing_run_id", "text_blocks", ["processing_run_id"])
    op.create_index("ix_text_blocks_review_status", "text_blocks", ["review_status"])

    op.create_table(
        "translation_suggestions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("text_block_id", sa.UUID(), nullable=False),
        sa.Column("translation", sa.Text(), nullable=False),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column("relevance", sa.SmallInteger(), nullable=True),
        sa.Column("source", _block_source, nullable=False, server_default="AUTO"),
        sa.Column("created_at", _DT, server_default=_NOW, nullable=False),
        sa.Column("updated_at", _DT, server_default=_NOW, nullable=False),
        sa.CheckConstraint(
            "relevance BETWEEN 1 AND 5", name="ck_translation_suggestions_relevance"
        ),
        sa.ForeignKeyConstraint(["text_block_id"], ["text_blocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_translation_suggestions_text_block_id", "translation_suggestions", ["text_block_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_translation_suggestions_text_block_id", "translation_suggestions")
    op.drop_table("translation_suggestions")

    op.drop_index("ix_text_blocks_review_status", "text_blocks")
    op.drop_index("ix_text_blocks_processing_run_id", "text_blocks")
    op.drop_index("ix_text_blocks_page_id", "text_blocks")
    op.drop_table("text_blocks")

    op.drop_index("ix_processing_runs_status", "processing_runs")
    op.drop_index("ix_processing_runs_page_id", "processing_runs")
    op.drop_table("processing_runs")

    op.execute("DROP TYPE orientation")
    op.execute("DROP TYPE block_source")
    op.execute("DROP TYPE review_status")
    op.execute("DROP TYPE run_status")
    op.execute("DROP TYPE run_type")
