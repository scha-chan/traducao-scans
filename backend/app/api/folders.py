import hashlib
import io
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from contracts.models import TextBlockExport
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import queue
from app.api.pages import (
    PageOut,
    ProcessPageOut,
    _block_to_export,
    _dispatch_and_wait,
    _page_to_summary,
)
from app.db.deps import get_db
from app.db.models import Folder, Page, ProcessingRun, RunType, TextBlock, Work
from app.settings import settings

router = APIRouter(prefix="/folders", tags=["folders"])

_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
_PIL_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "BMP": "image/bmp",
    "TIFF": "image/tiff",
}


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


@router.post("/{folder_id}/pages/process", response_model=ProcessPageOut, tags=["pages"])
async def process_page_upload(
    folder_id: UUID,
    file: UploadFile,
    page_number: int = Form(...),
    db: AsyncSession = Depends(get_db),
) -> ProcessPageOut:
    folder = await _get_or_404(folder_id, db)
    dest_dir = Path(settings.upload_dir) / "folders" / str(folder_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    raw = await file.read()

    if len(raw) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{file.filename}: arquivo excede 20 MB",
        )

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"{file.filename}: extensão não permitida",
        )

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
    except (UnidentifiedImageError, Exception):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"{file.filename}: tipo de arquivo não suportado",
        ) from None

    img = Image.open(io.BytesIO(raw))
    width, height = img.size
    mime_type = _PIL_TO_MIME.get(img.format or "", "application/octet-stream")
    sha256 = hashlib.sha256(raw).hexdigest()

    safe_name = f"{uuid4().hex}_{Path(file.filename or 'page').name}"
    file_path = dest_dir / safe_name
    file_path.write_bytes(raw)

    page = Page(
        folder_id=folder.id,
        file_name=file.filename or safe_name,
        file_path=str(file_path),
        mime_type=mime_type,
        width=width,
        height=height,
        sha256=sha256,
        page_number=page_number,
    )
    db.add(page)
    await db.flush()

    run = ProcessingRun(page_id=page.id, run_type=RunType.FULL)
    pool = await queue.get_pool()
    blocks = await _dispatch_and_wait(pool, db, page, run)
    return ProcessPageOut(
        page=_page_to_summary(page, blocks),
        blocos=[_block_to_export(b) for b in blocks],
    )


@router.post(
    "/{folder_id}/pages",
    response_model=list[PageOut],
    status_code=status.HTTP_201_CREATED,
    tags=["pages"],
)
async def upload_pages(
    folder_id: UUID,
    files: list[UploadFile],
    db: AsyncSession = Depends(get_db),
) -> list[Page]:
    folder = await _get_or_404(folder_id, db)

    count_result = await db.execute(
        select(func.count()).select_from(Page).where(Page.folder_id == folder.id)
    )
    existing_count: int = count_result.scalar_one()

    dest_dir = Path(settings.upload_dir) / "folders" / str(folder_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    pages: list[Page] = []
    for i, upload in enumerate(files):
        raw = await upload.read()

        if len(raw) > _MAX_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{upload.filename}: arquivo excede 20 MB",
            )

        ext = Path(upload.filename or "").suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"{upload.filename}: extensão não permitida",
            )

        try:
            img = Image.open(io.BytesIO(raw))
            img.verify()
        except (UnidentifiedImageError, Exception):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"{upload.filename}: tipo de arquivo não suportado",
            ) from None

        img = Image.open(io.BytesIO(raw))
        width, height = img.size
        mime_type = _PIL_TO_MIME.get(img.format or "", "application/octet-stream")

        sha256 = hashlib.sha256(raw).hexdigest()

        safe_name = f"{uuid4().hex}_{Path(upload.filename or 'page').name}"
        file_path = dest_dir / safe_name
        file_path.write_bytes(raw)

        page = Page(
            folder_id=folder.id,
            file_name=upload.filename or safe_name,
            file_path=str(file_path),
            mime_type=mime_type,
            width=width,
            height=height,
            sha256=sha256,
            page_number=existing_count + i + 1,
        )
        db.add(page)
        pages.append(page)

    await db.commit()
    for page in pages:
        await db.refresh(page)
    return pages


# ---------------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------------


class PageExportOut(BaseModel):
    pagina: int
    arquivo: str
    status: str
    blocos: list[TextBlockExport] | None


class FolderExportOut(BaseModel):
    pasta: str
    paginas: list[PageExportOut]


@router.get("/{folder_id}/export", response_model=FolderExportOut)
async def export_folder(folder_id: UUID, db: AsyncSession = Depends(get_db)) -> FolderExportOut:
    folder = await _get_or_404(folder_id, db)

    result = await db.execute(
        select(Page)
        .where(Page.folder_id == folder_id)
        .options(selectinload(Page.text_blocks).selectinload(TextBlock.translation_suggestions))
        .order_by(Page.page_number)
    )
    pages = list(result.scalars().all())

    paginas: list[PageExportOut] = []
    for page in pages:
        blocos: list[TextBlockExport] | None = None
        if page.text_blocks:
            blocos = [
                _block_to_export(b) for b in sorted(page.text_blocks, key=lambda b: b.order_number)
            ]
        paginas.append(
            PageExportOut(
                pagina=page.page_number,
                arquivo=page.file_name,
                status=page.status.value,
                blocos=blocos,
            )
        )

    return FolderExportOut(pasta=folder.name, paginas=paginas)
