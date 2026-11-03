"""TranslationContextBuilder — monta o payload de contexto completo para o LLM (F5-AG-02)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Character,
    CharacterMention,
    Folder,
    Page,
    ReviewStatus,
    TextBlock,
    TranslationSuggestion,
)


@dataclass
class CharacterContext:
    """Personagem mencionado no bloco, com registro de fala (PRD §30.1)."""

    name: str
    speech_register: str | None
    notes: str | None


@dataclass
class NeighbourBlock:
    """Bloco vizinho na ordem de leitura."""

    original: str
    block_type: str | None
    location: str | None


@dataclass
class PriorTranslation:
    """Tradução aprovada do mesmo original em outra página da obra (PRD §17.6)."""

    page_number: int
    translation: str


@dataclass
class TranslationContext:
    """Payload de contexto completo para o LLM de tradução (PRD §18)."""

    original: str | None
    block_type: str | None
    location: str | None
    ocr_confidence: float | None
    previous_block: NeighbourBlock | None
    next_block: NeighbourBlock | None
    characters: list[CharacterContext] = field(default_factory=list)
    prior_translations: list[PriorTranslation] = field(default_factory=list)
    output_language: Literal["pt-BR"] = "pt-BR"


class TranslationContextBuilder:
    """Monta o contexto completo de tradução para um bloco de texto (PRD §18, F5-AG-02)."""

    async def build(
        self,
        block: TextBlock,
        page: Page,
        session: AsyncSession,
    ) -> TranslationContext:
        """Build translation context for *block* on *page*."""
        prev_block, next_block = await self._neighbours(block, page, session)
        characters = await self._characters(block, session)
        prior_translations = await self._prior_translations(block, page, session)

        return TranslationContext(
            original=block.original,
            block_type=block.type,
            location=block.location,
            ocr_confidence=block.ocr_confidence,
            previous_block=prev_block,
            next_block=next_block,
            characters=characters,
            prior_translations=prior_translations,
        )

    async def _neighbours(
        self,
        block: TextBlock,
        page: Page,
        session: AsyncSession,
    ) -> tuple[NeighbourBlock | None, NeighbourBlock | None]:
        """Return (previous, next) blocks by reading order on the same page."""
        stmt_prev = (
            select(TextBlock)
            .where(
                TextBlock.page_id == page.id,
                TextBlock.order_number < block.order_number,
            )
            .order_by(TextBlock.order_number.desc())
            .limit(1)
        )
        stmt_next = (
            select(TextBlock)
            .where(
                TextBlock.page_id == page.id,
                TextBlock.order_number > block.order_number,
            )
            .order_by(TextBlock.order_number.asc())
            .limit(1)
        )
        prev_row = (await session.execute(stmt_prev)).scalar_one_or_none()
        next_row = (await session.execute(stmt_next)).scalar_one_or_none()

        prev = (
            NeighbourBlock(
                original=prev_row.original or "",
                block_type=prev_row.type,
                location=prev_row.location,
            )
            if prev_row is not None
            else None
        )
        nxt = (
            NeighbourBlock(
                original=next_row.original or "",
                block_type=next_row.type,
                location=next_row.location,
            )
            if next_row is not None
            else None
        )
        return prev, nxt

    async def _characters(
        self,
        block: TextBlock,
        session: AsyncSession,
    ) -> list[CharacterContext]:
        """Return characters associated with *block* via character_mentions."""
        stmt = (
            select(Character)
            .join(CharacterMention, CharacterMention.character_id == Character.id)
            .where(CharacterMention.text_block_id == block.id)
        )
        rows = (await session.execute(stmt)).scalars().all()
        return [
            CharacterContext(
                name=c.name_preferred or c.name_original,
                speech_register=c.speech_register,
                notes=c.notes,
            )
            for c in rows
        ]

    async def _prior_translations(
        self,
        block: TextBlock,
        page: Page,
        session: AsyncSession,
    ) -> list[PriorTranslation]:
        """Return reviewed translations of the same original in this work."""
        if not block.original:
            return []

        work_id: UUID | None = (
            await session.execute(select(Folder.work_id).where(Folder.id == page.folder_id))
        ).scalar_one_or_none()
        if work_id is None:
            return []

        stmt = (
            select(TranslationSuggestion.translation, Page.page_number)
            .join(TextBlock, TextBlock.id == TranslationSuggestion.text_block_id)
            .join(Page, Page.id == TextBlock.page_id)
            .join(Folder, Folder.id == Page.folder_id)
            .where(
                TextBlock.original == block.original,
                TextBlock.id != block.id,
                TextBlock.review_status == ReviewStatus.REVIEWED,
                Folder.work_id == work_id,
            )
            .order_by(Page.page_number)
        )
        rows = (await session.execute(stmt)).all()
        return [
            PriorTranslation(
                page_number=row.page_number,
                translation=row.translation,
            )
            for row in rows
        ]
