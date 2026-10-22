from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.characters import CharacterCreate, CharacterOut, create_character, list_characters
from app.db.deps import get_db
from app.db.models import Work

router = APIRouter(prefix="/works", tags=["works"])


class WorkCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class WorkUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class WorkOut(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


async def _get_or_404(work_id: UUID, db: AsyncSession) -> Work:
    result = await db.get(Work, work_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")
    return result


@router.get("", response_model=list[WorkOut])
async def list_works(db: AsyncSession = Depends(get_db)) -> list[Work]:
    result = await db.execute(select(Work).order_by(Work.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=WorkOut, status_code=status.HTTP_201_CREATED)
async def create_work(body: WorkCreate, db: AsyncSession = Depends(get_db)) -> Work:
    work = Work(title=body.title)
    db.add(work)
    await db.commit()
    await db.refresh(work)
    return work


@router.get("/{work_id}", response_model=WorkOut)
async def get_work(work_id: UUID, db: AsyncSession = Depends(get_db)) -> Work:
    return await _get_or_404(work_id, db)


@router.patch("/{work_id}", response_model=WorkOut)
async def update_work(work_id: UUID, body: WorkUpdate, db: AsyncSession = Depends(get_db)) -> Work:
    work = await _get_or_404(work_id, db)
    work.title = body.title
    await db.commit()
    await db.refresh(work)
    return work


@router.delete("/{work_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work(work_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    work = await _get_or_404(work_id, db)
    await db.delete(work)
    await db.commit()


@router.get("/{work_id}/characters", response_model=list[CharacterOut], tags=["characters"])
async def list_work_characters(work_id: UUID, db: AsyncSession = Depends(get_db)) -> list:
    return await list_characters(work_id, db)


@router.post(
    "/{work_id}/characters",
    response_model=CharacterOut,
    status_code=status.HTTP_201_CREATED,
    tags=["characters"],
)
async def create_work_character(
    work_id: UUID, body: CharacterCreate, db: AsyncSession = Depends(get_db)
) -> object:
    return await create_character(work_id, body, db)
