"""Tabela page_slices — anotações manuais de regiões (V3-AN)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-18
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "page_slices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("page_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(1), nullable=False),
        sa.Column("bbox_x", sa.Integer(), nullable=False),
        sa.Column("bbox_y", sa.Integer(), nullable=False),
        sa.Column("bbox_width", sa.Integer(), nullable=False),
        sa.Column("bbox_height", sa.Integer(), nullable=False),
        sa.Column("text_block_id", sa.Uuid(), nullable=True),
        sa.Column(
            "annotated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("type IN ('#', '$')", name="ck_page_slices_type"),
        sa.ForeignKeyConstraint(["page_id"], ["pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["text_block_id"], ["text_blocks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "page_id",
            "order_number",
            name="uq_page_slices_page_order",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index("ix_page_slices_page_id", "page_slices", ["page_id"])


def downgrade() -> None:
    op.drop_index("ix_page_slices_page_id", table_name="page_slices")
    op.drop_table("page_slices")
