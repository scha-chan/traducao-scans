"""V2-BE-01/AG-02: CRUD do glossário, busca de ocorrências e sugestão automática."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent.glossary_suggester import GlossarySuggester
from app.db.deps import get_db
from app.db.models import GlossaryEntry, GlossaryOccurrence, Work

router = APIRouter(tags=["glossary"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class GlossaryEntryCreate(BaseModel):
    source_term: str = Field(..., min_length=1, max_length=500)
    preferred_translation: str | None = None
    category: str | None = Field(None, max_length=100)
    notes: str | None = None


class GlossaryEntryUpdate(BaseModel):
    source_term: str | None = Field(None, min_length=1, max_length=500)
    preferred_translation: str | None = None
    category: str | None = Field(None, max_length=100)
    notes: str | None = None


class GlossaryEntryOut(BaseModel):
    id: UUID
    work_id: UUID
    source_term: str
    preferred_translation: str | None
    category: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GlossaryOccurrenceOut(BaseModel):
    id: UUID
    glossary_entry_id: UUID
    page_id: UUID
    text_block_id: UUID | None
    created_at: datetime

    # Enriched fields
    page_number: int | None = None
    folder_id: UUID | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_entry_or_404(work_id: UUID, entry_id: UUID, db: AsyncSession) -> GlossaryEntry:
    entry = await db.get(GlossaryEntry, entry_id)
    if entry is None or entry.work_id != work_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrada não encontrada")
    return entry


# ---------------------------------------------------------------------------
# Routes — entries
# ---------------------------------------------------------------------------

works_router = APIRouter(prefix="/works/{work_id}/glossary", tags=["glossary"])


@works_router.get("", response_model=list[GlossaryEntryOut])
async def list_glossary_entries(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[GlossaryEntry]:
    work = await db.get(Work, work_id)
    if work is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")

    result = await db.execute(
        select(GlossaryEntry)
        .where(GlossaryEntry.work_id == work_id)
        .order_by(GlossaryEntry.source_term)
    )
    return list(result.scalars().all())


@works_router.post("", response_model=GlossaryEntryOut, status_code=status.HTTP_201_CREATED)
async def create_glossary_entry(
    work_id: UUID,
    body: GlossaryEntryCreate,
    db: AsyncSession = Depends(get_db),
) -> GlossaryEntry:
    work = await db.get(Work, work_id)
    if work is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")

    entry = GlossaryEntry(
        work_id=work_id,
        source_term=body.source_term,
        preferred_translation=body.preferred_translation,
        category=body.category,
        notes=body.notes,
    )
    db.add(entry)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma entrada para esse termo nessa obra",
        ) from None
    await db.refresh(entry)
    return entry


@works_router.get("/{entry_id}", response_model=GlossaryEntryOut)
async def get_glossary_entry(
    work_id: UUID,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> GlossaryEntry:
    return await _get_entry_or_404(work_id, entry_id, db)


@works_router.patch("/{entry_id}", response_model=GlossaryEntryOut)
async def update_glossary_entry(
    work_id: UUID,
    entry_id: UUID,
    body: GlossaryEntryUpdate,
    db: AsyncSession = Depends(get_db),
) -> GlossaryEntry:
    entry = await _get_entry_or_404(work_id, entry_id, db)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflito: já existe uma entrada para esse termo nessa obra",
        ) from None
    await db.refresh(entry)
    return entry


@works_router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_glossary_entry(
    work_id: UUID,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    entry = await _get_entry_or_404(work_id, entry_id, db)
    await db.delete(entry)
    await db.commit()


# ---------------------------------------------------------------------------
# Routes — occurrences
# ---------------------------------------------------------------------------


@works_router.get("/{entry_id}/occurrences", response_model=list[GlossaryOccurrenceOut])
async def list_entry_occurrences(
    work_id: UUID,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[GlossaryOccurrenceOut]:
    """Return all pages where this glossary term was detected."""
    entry = await _get_entry_or_404(work_id, entry_id, db)

    result = await db.execute(
        select(GlossaryOccurrence)
        .where(GlossaryOccurrence.glossary_entry_id == entry.id)
        .options(selectinload(GlossaryOccurrence.page))
        .order_by(GlossaryOccurrence.created_at)
    )
    occurrences = list(result.scalars().all())

    out: list[GlossaryOccurrenceOut] = []
    for occ in occurrences:
        item = GlossaryOccurrenceOut.model_validate(occ)
        if occ.page is not None:
            item.page_number = occ.page.page_number
            item.folder_id = occ.page.folder_id
        out.append(item)
    return out


# ---------------------------------------------------------------------------
# Route — search occurrences by term across a work
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Route — auto-suggest new glossary entries (V2-AG-02)
# ---------------------------------------------------------------------------


class GlossarySuggestionOut(BaseModel):
    source_term: str
    page_count: int
    category: str
    sample_context: str


@works_router.get("/suggest", response_model=list[GlossarySuggestionOut])
async def suggest_glossary_entries(
    work_id: UUID,
    min_occurrences: int = 2,
    db: AsyncSession = Depends(get_db),
) -> list[GlossarySuggestionOut]:
    """Scan reviewed blocks of the work and suggest new glossary entries.

    Returns candidate terms (katakana, honorifics, kanji sequences) that appear
    in at least *min_occurrences* distinct pages and are not yet in the glossary.
    """
    work = await db.get(Work, work_id)
    if work is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")

    suggester = GlossarySuggester(db, min_occurrences=min_occurrences)
    suggestions = await suggester.suggest(work_id)
    return [
        GlossarySuggestionOut(
            source_term=s.source_term,
            page_count=s.page_count,
            category=s.category,
            sample_context=s.sample_context,
        )
        for s in suggestions
    ]


# ---------------------------------------------------------------------------
# Route — search occurrences by term across a work
# ---------------------------------------------------------------------------

glossary_search_router = APIRouter(tags=["glossary"])


@glossary_search_router.get(
    "/works/{work_id}/glossary-search",
    response_model=list[GlossaryEntryOut],
)
async def search_glossary(
    work_id: UUID,
    q: str,
    db: AsyncSession = Depends(get_db),
) -> list[GlossaryEntry]:
    """Full-text search within the work's glossary entries."""
    work = await db.get(Work, work_id)
    if work is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")

    result = await db.execute(
        select(GlossaryEntry)
        .where(GlossaryEntry.work_id == work_id)
        .where(
            GlossaryEntry.source_term.ilike(f"%{q}%")
            | GlossaryEntry.preferred_translation.ilike(f"%{q}%")
        )
        .order_by(GlossaryEntry.source_term)
        .limit(50)
    )
    return list(result.scalars().all())
