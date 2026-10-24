import io
from datetime import datetime
from pathlib import Path
from uuid import UUID

from contracts.models import TextBlockExport
from contracts.validator import validate_page_export
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.deps import get_db
from app.db.models import BlockSource, Page, ReviewStatus, TextBlock, TranslationSuggestion

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
    img: Image.Image = Image.open(path)
    w, h = img.size
    if w > _THUMBNAIL_WIDTH:
        new_h = int(h * _THUMBNAIL_WIDTH / w)
        img = img.resize((_THUMBNAIL_WIDTH, new_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="WEBP", quality=80)
    return Response(content=buf.getvalue(), media_type="image/webp")


@router.get("/{page_id}/json", response_model=list[TextBlockExport])
async def get_page_json(page_id: UUID, db: AsyncSession = Depends(get_db)) -> list[TextBlockExport]:
    await _get_or_404(page_id, db)
    result = await db.execute(
        select(TextBlock)
        .where(TextBlock.page_id == page_id)
        .options(selectinload(TextBlock.translation_suggestions))
        .order_by(TextBlock.order_number)
    )
    blocks = list(result.scalars().all())
    return [_block_to_export(b) for b in blocks]


@router.put("/{page_id}/json", response_model=list[TextBlockExport])
async def save_page_json(
    page_id: UUID,
    body: list[TextBlockExport],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await _get_or_404(page_id, db)

    issues = validate_page_export([b.model_dump() for b in body])
    if issues:
        details = {issue.field: issue.message for issue in issues}
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"message": "Dados inválidos", "details": details}},
        )

    await db.execute(delete(TextBlock).where(TextBlock.page_id == page_id))

    for item in body:
        block = TextBlock(
            page_id=page_id,
            order_number=item.ordem,
            type=item.tipo,
            original=item.original,
            location=item.localizacao,
            source=BlockSource.MANUAL,
            review_status=ReviewStatus.REVIEWED,
        )
        db.add(block)
        await db.flush()

        for sugg in item.traducoes:
            db.add(
                TranslationSuggestion(
                    text_block_id=block.id,
                    translation=sugg.traducao,
                    observation=sugg.observacao,
                    relevance=sugg.relevancia,
                    source=BlockSource.MANUAL,
                )
            )

    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=[b.model_dump() for b in body],
    )


def _block_to_export(block: TextBlock) -> TextBlockExport:
    return TextBlockExport.model_validate(
        {
            "ordem": block.order_number,
            "tipo": block.type,
            "original": block.original or "",
            "localizacao": block.location or "",
            "traducoes": [
                {
                    "traducao": s.translation,
                    "observacao": s.observation or "",
                    "relevancia": s.relevance or 1,
                }
                for s in sorted(block.translation_suggestions, key=lambda s: s.relevance or 0)
            ],
        }
    )
