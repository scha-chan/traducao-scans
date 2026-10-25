from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.deps import get_db
from app.db.models import BlockSource, TextBlock, TranslationSuggestion

router = APIRouter(prefix="/blocks", tags=["blocks"])

_MAX_SUGGESTIONS = 5


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SuggestionOut(BaseModel):
    id: UUID
    text_block_id: UUID
    translation: str
    observation: str | None
    relevance: int | None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BlockOut(BaseModel):
    id: UUID
    page_id: UUID
    order_number: int
    type: str | None
    original: str | None
    location: str | None
    source: str
    review_status: str
    created_at: datetime
    updated_at: datetime
    suggestions: list[SuggestionOut] = []

    model_config = {"from_attributes": True}


class BlockUpdate(BaseModel):
    tipo: str | None = Field(None, pattern=r"^[#$]$")
    original: str | None = None
    localizacao: str | None = None


class SuggestionIn(BaseModel):
    traducao: str = Field(..., min_length=1)
    observacao: str = ""
    relevancia: int = Field(..., ge=1, le=5)


class SuggestionUpdate(BaseModel):
    traducao: str | None = Field(None, min_length=1)
    observacao: str | None = None
    relevancia: int | None = Field(None, ge=1, le=5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_block_or_404(block_id: UUID, db: AsyncSession) -> TextBlock:
    result = await db.execute(
        select(TextBlock)
        .where(TextBlock.id == block_id)
        .options(selectinload(TextBlock.translation_suggestions))
    )
    block = result.scalar_one_or_none()
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bloco não encontrado")
    return block


async def _get_suggestion_or_404(
    block_id: UUID, suggestion_id: UUID, db: AsyncSession
) -> TranslationSuggestion:
    result = await db.execute(
        select(TranslationSuggestion).where(
            TranslationSuggestion.id == suggestion_id,
            TranslationSuggestion.text_block_id == block_id,
        )
    )
    suggestion = result.scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sugestão não encontrada")
    return suggestion


def _to_block_out(block: TextBlock) -> BlockOut:
    return BlockOut(
        id=block.id,
        page_id=block.page_id,
        order_number=block.order_number,
        type=block.type,
        original=block.original,
        location=block.location,
        source=block.source.value,
        review_status=block.review_status.value,
        created_at=block.created_at,
        updated_at=block.updated_at,
        suggestions=[
            SuggestionOut(
                id=s.id,
                text_block_id=s.text_block_id,
                translation=s.translation,
                observation=s.observation,
                relevance=s.relevance,
                source=s.source.value,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sorted(block.translation_suggestions, key=lambda s: s.relevance or 0)
        ],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{block_id}", response_model=BlockOut)
async def get_block(block_id: UUID, db: AsyncSession = Depends(get_db)) -> BlockOut:
    block = await _get_block_or_404(block_id, db)
    return _to_block_out(block)


@router.patch("/{block_id}", response_model=BlockOut)
async def update_block(
    block_id: UUID, body: BlockUpdate, db: AsyncSession = Depends(get_db)
) -> BlockOut:
    block = await _get_block_or_404(block_id, db)
    if body.tipo is not None:
        block.type = body.tipo
    if body.original is not None:
        block.original = body.original
    if body.localizacao is not None:
        block.location = body.localizacao
    block.source = BlockSource.MANUAL
    await db.commit()
    await db.refresh(block)
    block = await _get_block_or_404(block_id, db)
    return _to_block_out(block)


@router.get("/{block_id}/suggestions", response_model=list[SuggestionOut])
async def list_suggestions(
    block_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[SuggestionOut]:
    block = await _get_block_or_404(block_id, db)
    return [
        SuggestionOut.model_validate(s)
        for s in sorted(block.translation_suggestions, key=lambda s: s.relevance or 0)
    ]


@router.post(
    "/{block_id}/suggestions",
    response_model=SuggestionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_suggestion(
    block_id: UUID, body: SuggestionIn, db: AsyncSession = Depends(get_db)
) -> SuggestionOut:
    block = await _get_block_or_404(block_id, db)
    if len(block.translation_suggestions) >= _MAX_SUGGESTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Bloco já tem {_MAX_SUGGESTIONS} sugestões (máximo permitido)",
        )
    suggestion = TranslationSuggestion(
        text_block_id=block_id,
        translation=body.traducao,
        observation=body.observacao,
        relevance=body.relevancia,
        source=BlockSource.MANUAL,
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)
    return SuggestionOut.model_validate(suggestion)


@router.patch("/{block_id}/suggestions/{suggestion_id}", response_model=SuggestionOut)
async def update_suggestion(
    block_id: UUID,
    suggestion_id: UUID,
    body: SuggestionUpdate,
    db: AsyncSession = Depends(get_db),
) -> SuggestionOut:
    suggestion = await _get_suggestion_or_404(block_id, suggestion_id, db)
    if body.traducao is not None:
        suggestion.translation = body.traducao
    if body.observacao is not None:
        suggestion.observation = body.observacao
    if body.relevancia is not None:
        suggestion.relevance = body.relevancia
    suggestion.source = BlockSource.MANUAL
    await db.commit()
    await db.refresh(suggestion)
    return SuggestionOut.model_validate(suggestion)


@router.delete("/{block_id}/suggestions/{suggestion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suggestion(
    block_id: UUID,
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    block = await _get_block_or_404(block_id, db)
    if len(block.translation_suggestions) <= 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bloco deve ter pelo menos 1 sugestão de tradução",
        )
    suggestion = await _get_suggestion_or_404(block_id, suggestion_id, db)
    await db.delete(suggestion)
    await db.commit()
