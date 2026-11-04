"""V2-BE-03: histórico e versionamento de blocos de texto

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-04

Mudanças:
- Cria enum change_type (EDITED, REVIEWED, UNREVIEW)
- Cria tabela text_block_history (N:1 com text_blocks, CASCADE DELETE)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE change_type AS ENUM ('EDITED', 'REVIEWED', 'UNREVIEW')")

    op.create_table(
        "text_block_history",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("block_id", sa.UUID(), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "change_type",
            sa.Enum("EDITED", "REVIEWED", "UNREVIEW", name="change_type"),
            nullable=False,
        ),
        sa.Column("original", sa.Text(), nullable=True),
        sa.Column(
            "review_status",
            sa.Enum("PENDING", "NEEDS_REVIEW", "REVIEWED", name="review_status"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["block_id"], ["text_blocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_text_block_history_block_id", "text_block_history", ["block_id"])


def downgrade() -> None:
    op.drop_index("ix_text_block_history_block_id", "text_block_history")
    op.drop_table("text_block_history")
    op.execute("DROP TYPE change_type")
