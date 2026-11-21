"""Colunas source_lang e target_lang na tabela folders

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "folders",
        sa.Column("source_lang", sa.String(10), nullable=False, server_default="ja"),
    )
    op.add_column(
        "folders",
        sa.Column("target_lang", sa.String(10), nullable=False, server_default="pt"),
    )


def downgrade() -> None:
    op.drop_column("folders", "target_lang")
    op.drop_column("folders", "source_lang")
