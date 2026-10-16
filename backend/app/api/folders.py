from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.db.models import Folder, Work

router = APIRouter(prefix="/folders", tags=["folders"])


class FolderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120, alias="name")
    work_id: UUID | None = None

    model_config = {"populate_by_name": True}


class FolderUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class FolderOut(BaseModel):
    id: UUID
    name: str
    work_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


async def _get_or_404(folder_id: UUID, db: AsyncSession) -> Folder:
    result = await db.get(Folder, folder_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pasta não encontrada")
    return result


@router.get("", response_model=list[FolderOut])
async def list_folders(db: AsyncSession = Depends(get_db)) -> list[Folder]:
    result = await db.execute(select(Folder).order_by(Folder.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
async def create_folder(body: FolderCreate, db: AsyncSession = Depends(get_db)) -> Folder:
    if body.work_id is not None:
        work = await db.get(Work, body.work_id)
        if work is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")
    folder = Folder(name=body.title, work_id=body.work_id)
    db.add(folder)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma pasta com esse nome",
        ) from None
    await db.refresh(folder)
    return folder


@router.get("/{folder_id}", response_model=FolderOut)
async def get_folder(folder_id: UUID, db: AsyncSession = Depends(get_db)) -> Folder:
    return await _get_or_404(folder_id, db)


@router.patch("/{folder_id}", response_model=FolderOut)
async def update_folder(
    folder_id: UUID, body: FolderUpdate, db: AsyncSession = Depends(get_db)
) -> Folder:
    folder = await _get_or_404(folder_id, db)
    folder.name = body.name
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma pasta com esse nome",
        ) from None
    await db.refresh(folder)
    return folder


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(folder_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    folder = await _get_or_404(folder_id, db)
    await db.delete(folder)
    await db.commit()
