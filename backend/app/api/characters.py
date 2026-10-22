from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.db.models import Character, Work

router = APIRouter(prefix="/characters", tags=["characters"])

_VALID_GENDERS = {"male", "female", "unknown"}
_VALID_REGISTERS = {"formal", "informal", "childlike", "rough", "polite"}


class CharacterOut(BaseModel):
    id: UUID
    work_id: UUID
    name_original: str
    name_preferred: str | None
    gender: str | None
    speech_register: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CharacterCreate(BaseModel):
    name_original: str = Field(..., min_length=1, max_length=255)
    name_preferred: str | None = Field(None, max_length=255)
    gender: str | None = None
    speech_register: str | None = None
    notes: str | None = None


class CharacterUpdate(BaseModel):
    name_original: str | None = Field(None, min_length=1, max_length=255)
    name_preferred: str | None = Field(None, max_length=255)
    gender: str | None = None
    speech_register: str | None = None
    notes: str | None = None


def _validate_gender(value: str | None) -> None:
    if value is not None and value not in _VALID_GENDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"gender deve ser um de: {sorted(_VALID_GENDERS)}",
        )


def _validate_register(value: str | None) -> None:
    if value is not None and value not in _VALID_REGISTERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"speech_register deve ser um de: {sorted(_VALID_REGISTERS)}",
        )


async def _get_or_404(character_id: UUID, db: AsyncSession) -> Character:
    char = await db.get(Character, character_id)
    if char is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Personagem não encontrado"
        )
    return char


@router.get("/{character_id}", response_model=CharacterOut)
async def get_character(character_id: UUID, db: AsyncSession = Depends(get_db)) -> Character:
    return await _get_or_404(character_id, db)


@router.patch("/{character_id}", response_model=CharacterOut)
async def update_character(
    character_id: UUID, body: CharacterUpdate, db: AsyncSession = Depends(get_db)
) -> Character:
    _validate_gender(body.gender)
    _validate_register(body.speech_register)
    char = await _get_or_404(character_id, db)
    if body.name_original is not None:
        char.name_original = body.name_original
    if body.name_preferred is not None:
        char.name_preferred = body.name_preferred
    if body.gender is not None:
        char.gender = body.gender
    if body.speech_register is not None:
        char.speech_register = body.speech_register
    if body.notes is not None:
        char.notes = body.notes
    await db.commit()
    await db.refresh(char)
    return char


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(character_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    char = await _get_or_404(character_id, db)
    await db.delete(char)
    await db.commit()


# ---------------------------------------------------------------------------
# Endpoints aninhados sob /works/{id}/characters — registrados em works.py
# ---------------------------------------------------------------------------


async def list_characters(work_id: UUID, db: AsyncSession) -> list[Character]:
    work = await db.get(Work, work_id)
    if work is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")
    result = await db.execute(
        select(Character).where(Character.work_id == work_id).order_by(Character.created_at.asc())
    )
    return list(result.scalars().all())


async def create_character(work_id: UUID, body: CharacterCreate, db: AsyncSession) -> Character:
    work = await db.get(Work, work_id)
    if work is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")
    _validate_gender(body.gender)
    _validate_register(body.speech_register)
    char = Character(
        work_id=work_id,
        name_original=body.name_original,
        name_preferred=body.name_preferred,
        gender=body.gender,
        speech_register=body.speech_register,
        notes=body.notes,
    )
    db.add(char)
    await db.commit()
    await db.refresh(char)
    return char
