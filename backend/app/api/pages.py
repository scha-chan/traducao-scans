import io
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.db.models import Page

router = APIRouter(prefix="/pages", tags=["pages"])

_THUMBNAIL_WIDTH = 300


class PageOut(BaseModel):
    id: UUID
    folder_id: UUID
    file_name: str
    mime_type: str
    width: int | None
    height: int | None
    page_number: int
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PageUpdate(BaseModel):
    page_number: int | None = None


async def _get_or_404(page_id: UUID, db: AsyncSession) -> Page:
    page = await db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Página não encontrada")
    return page


@router.get("/{page_id}", response_model=PageOut)
async def get_page(page_id: UUID, db: AsyncSession = Depends(get_db)) -> Page:
    return await _get_or_404(page_id, db)


@router.patch("/{page_id}", response_model=PageOut)
async def update_page(page_id: UUID, body: PageUpdate, db: AsyncSession = Depends(get_db)) -> Page:
    page = await _get_or_404(page_id, db)
    if body.page_number is not None:
        page.page_number = body.page_number
    await db.commit()
    await db.refresh(page)
    return page


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(page_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    page = await _get_or_404(page_id, db)
    file_path = Path(page.file_path)
    await db.delete(page)
    await db.commit()
    file_path.unlink(missing_ok=True)


@router.get("/{page_id}/image")
async def get_image(page_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    page = await _get_or_404(page_id, db)
    path = Path(page.file_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado")
    return Response(content=path.read_bytes(), media_type=page.mime_type)


@router.get("/{page_id}/thumbnail")
async def get_thumbnail(page_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    page = await _get_or_404(page_id, db)
    path = Path(page.file_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado")
    img = Image.open(path)
    w, h = img.size
    if w > _THUMBNAIL_WIDTH:
        new_h = int(h * _THUMBNAIL_WIDTH / w)
        img = img.resize((_THUMBNAIL_WIDTH, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="WEBP", quality=80)
    return Response(content=buf.getvalue(), media_type="image/webp")
