"""V2-DB-01: glossary_entries, glossary_occurrences e work_id obrigatório em folders

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-04

Mudanças:
- Cria tabela glossary_entries (N:1 com works)
- Cria tabela glossary_occurrences (N:1 com glossary_entries, pages e text_blocks)
- Torna folders.work_id NOT NULL:
    - Cria obra-padrão ("Sem Título") para pastas órfãs
    - Atualiza pastas órfãs para apontar para a obra-padrão
    - Altera coluna para NOT NULL
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- glossary_entries --------------------------------------------------
    op.create_table(
        "glossary_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "work_id",
            UUID(as_uuid=True),
            sa.ForeignKey("works.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("source_term", sa.Text, nullable=False),
        sa.Column("preferred_translation", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("work_id", "source_term", name="uq_glossary_entries_work_term"),
    )

    # --- glossary_occurrences ----------------------------------------------
    op.create_table(
        "glossary_occurrences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "glossary_entry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("glossary_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "page_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "text_block_id",
            UUID(as_uuid=True),
            sa.ForeignKey("text_blocks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "glossary_entry_id", "text_block_id", name="uq_glossary_occurrences_entry_block"
        ),
    )

    # --- folders.work_id NOT NULL ------------------------------------------
    # 1. Create a default work for orphan folders
    default_work_id = str(uuid.uuid4())
    conn = op.get_bind()

    orphan_exists = conn.execute(
        sa.text("SELECT EXISTS(SELECT 1 FROM folders WHERE work_id IS NULL)")
    ).scalar()

    if orphan_exists:
        conn.execute(
            sa.text(
                "INSERT INTO works (id, title, created_at, updated_at) "
                "VALUES (:id, :title, now(), now())"
            ),
            {"id": default_work_id, "title": "Sem Título"},
        )
        conn.execute(
            sa.text("UPDATE folders SET work_id = :wid WHERE work_id IS NULL"),
            {"wid": default_work_id},
        )

    # 2. Make work_id NOT NULL and change FK action to RESTRICT
    op.alter_column("folders", "work_id", nullable=False)

    # Update FK constraint to RESTRICT on delete (was SET NULL)
    op.drop_constraint("folders_work_id_fkey", "folders", type_="foreignkey")
    op.create_foreign_key(
        "fk_folders_work_id",
        "folders",
        "works",
        ["work_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Revert FK to SET NULL and make nullable again
    op.drop_constraint("fk_folders_work_id", "folders", type_="foreignkey")
    op.create_foreign_key(
        "folders_work_id_fkey",
        "folders",
        "works",
        ["work_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("folders", "work_id", nullable=True)

    op.drop_table("glossary_occurrences")
    op.drop_table("glossary_entries")
