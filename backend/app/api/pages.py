import io
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from arq.connections import ArqRedis
from contracts.models import TextBlockExport
from contracts.validator import validate_page_export
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import queue
from app.api.blocks import BlockOut, _to_block_out
from app.db.deps import get_db
from app.db.models import (
    BlockSource,
    Page,
    PageStatus,
    ProcessingRun,
    ReviewStatus,
    RunType,
    TextBlock,
    TranslationSuggestion,
)
from app.settings import settings

router = APIRouter(prefix="/pages", tags=["pages"])

_THUMBNAIL_WIDTH = 300
_PROCESS_TIMEOUT = 180.0


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


class PageSummary(BaseModel):
    id: UUID
    page_number: int
    file_name: str
    status: str
    block_count: int
    edited: bool
    thumbnail_url: str
    image_url: str


class ProcessPageOut(BaseModel):
    page: PageSummary
    blocos: list[TextBlockExport]


class RunSpan(BaseModel):
    span_id: str
    run_id: str
    stage: str
    provider: str
    model_version: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float
    success: bool
    fallback_used: bool


class RunOut(BaseModel):
    id: UUID
    run_type: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    error_message: str | None
    prompt_version: str | None
    created_at: datetime
    spans: list[RunSpan]


class PageUpdate(BaseModel):
    page_number: int | None = None


def _page_to_summary(page: Page, blocks: list[TextBlock]) -> PageSummary:
    return PageSummary(
        id=page.id,
        page_number=page.page_number,
        file_name=page.file_name,
        status=page.status.value,
        block_count=len(blocks),
        edited=any(b.source == BlockSource.MANUAL for b in blocks),
        thumbnail_url=f"/api/pages/{page.id}/thumbnail",
        image_url=f"/api/pages/{page.id}/image",
    )


async def _dispatch_and_wait(
    pool: ArqRedis,
    db: AsyncSession,
    page: Page,
    run: ProcessingRun,
) -> list[TextBlock]:
    """Set page to PROCESSING, enqueue arq job, wait up to 180 s, return blocks."""
    page.status = PageStatus.PROCESSING
    db.add(run)
    await db.commit()

    job = await pool.enqueue_job("analyze_page", str(page.id), str(run.id))
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao enfileirar tarefa de análise",
        )

    try:
        await job.result(timeout=_PROCESS_TIMEOUT)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tempo limite de processamento excedido",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no processamento: {exc}",
        ) from exc

    await db.refresh(page)
    result = await db.execute(
        select(TextBlock)
        .where(TextBlock.page_id == page.id)
        .options(selectinload(TextBlock.translation_suggestions))
        .order_by(TextBlock.order_number)
    )
    return list(result.scalars().all())


def _run_to_out(run: ProcessingRun) -> RunOut:
    duration_ms: int | None = None
    if run.started_at is not None and run.finished_at is not None:
        duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

    spans: list[RunSpan] = []
    if run.model_metadata:
        raw_spans: list[dict[str, Any]] = run.model_metadata.get("spans", [])
        spans = [RunSpan.model_validate(s) for s in raw_spans]

    return RunOut(
        id=run.id,
        run_type=run.run_type.value,
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_ms=duration_ms,
        error_message=run.error_message,
        prompt_version=run.prompt_version,
        created_at=run.created_at,
        spans=spans,
    )


async def _get_or_404(page_id: UUID, db: AsyncSession) -> Page:
    page = await db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Página não encontrada")
    return page


@router.get("/{page_id}", response_model=PageOut)
async def get_page(page_id: UUID, db: AsyncSession = Depends(get_db)) -> Page:
    return await _get_or_404(page_id, db)


@router.get("/{page_id}/blocks", response_model=list[BlockOut])
async def list_blocks(page_id: UUID, db: AsyncSession = Depends(get_db)) -> list[BlockOut]:
    await _get_or_404(page_id, db)
    result = await db.execute(
        select(TextBlock)
        .where(TextBlock.page_id == page_id)
        .options(selectinload(TextBlock.translation_suggestions))
        .order_by(TextBlock.order_number)
    )
    return [_to_block_out(b) for b in result.scalars().all()]


@router.get("/{page_id}/runs", response_model=list[RunOut])
async def list_runs(page_id: UUID, db: AsyncSession = Depends(get_db)) -> list[RunOut]:
    await _get_or_404(page_id, db)
    result = await db.execute(
        select(ProcessingRun)
        .where(ProcessingRun.page_id == page_id)
        .order_by(ProcessingRun.created_at.desc())
    )
    runs = list(result.scalars().all())
    return [_run_to_out(r) for r in runs]


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


@router.post("/{page_id}/approve", response_model=PageOut)
async def approve_page(page_id: UUID, db: AsyncSession = Depends(get_db)) -> Page:
    page = await _get_or_404(page_id, db)

    if settings.export_policy == "EXPORT_BLOCK_ON_LOW_CONFIDENCE":
        result = await db.execute(
            select(TextBlock).where(
                TextBlock.page_id == page_id,
                TextBlock.review_status == ReviewStatus.NEEDS_REVIEW,
            )
        )
        needs_review = list(result.scalars().all())
        if needs_review:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"blocos": [str(b.id) for b in needs_review]},
            )

    page.status = PageStatus.APPROVED
    await db.commit()
    await db.refresh(page)
    return page


class AnalyzeOut(BaseModel):
    run_id: UUID


class RegenerateOut(BaseModel):
    run_id: UUID
    status: str


@router.post(
    "/{page_id}/regenerate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RegenerateOut,
)
async def regenerate_page(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> RegenerateOut:
    """Enqueue a TRANSLATE_ONLY run (preserves OCR blocks, replaces AUTO suggestions)."""
    page = await _get_or_404(page_id, db)

    if page.status == PageStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_PROCESSING",
                "message": "Esta página já está sendo processada",
            },
        )

    run = ProcessingRun(page_id=page_id, run_type=RunType.TRANSLATE_ONLY)
    page.status = PageStatus.PROCESSING
    db.add(run)
    await db.commit()
    await db.refresh(run)

    pool = await queue.get_pool()
    job = await pool.enqueue_job("analyze_page", str(page.id), str(run.id))
    if job is None:
        page.status = PageStatus.ERROR
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao enfileirar tarefa de regeneração",
        )

    return RegenerateOut(run_id=run.id, status="PROCESSING")


@router.post("/{page_id}/analyze", status_code=status.HTTP_202_ACCEPTED, response_model=AnalyzeOut)
async def analyze_page_async(
    page_id: UUID,
    force: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> AnalyzeOut:
    """Enqueue analysis without waiting (returns 202 immediately)."""
    page = await _get_or_404(page_id, db)

    if page.status == PageStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_PROCESSING",
                "message": "Esta página já está sendo processada",
            },
        )

    if not force:
        manual_res = await db.execute(
            select(TextBlock)
            .where(TextBlock.page_id == page_id, TextBlock.source == BlockSource.MANUAL)
            .limit(1)
        )
        reviewed_res = await db.execute(
            select(TextBlock)
            .where(TextBlock.page_id == page_id, TextBlock.review_status == ReviewStatus.REVIEWED)
            .limit(1)
        )
        has_manual = manual_res.scalars().first() is not None
        has_reviewed = reviewed_res.scalars().first() is not None
        if has_manual or has_reviewed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "HAS_MANUAL_EDITS",
                    "message": "Existem edições protegidas. Use force=true para sobrescrever",
                    "has_manual": has_manual,
                    "has_reviewed": has_reviewed,
                },
            )

    run = ProcessingRun(page_id=page_id, run_type=RunType.FULL)
    page.status = PageStatus.PROCESSING
    db.add(run)
    await db.commit()
    await db.refresh(run)

    pool = await queue.get_pool()
    job = await pool.enqueue_job("analyze_page", str(page.id), str(run.id))
    if job is None:
        page.status = PageStatus.ERROR
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao enfileirar tarefa de análise",
        )

    return AnalyzeOut(run_id=run.id)


@router.post("/{page_id}/process", response_model=ProcessPageOut)
async def reprocess_page(
    page_id: UUID,
    force: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> ProcessPageOut:
    page = await _get_or_404(page_id, db)

    if page.status == PageStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta página já está sendo processada",
        )

    if not force:
        manual_res = await db.execute(
            select(TextBlock)
            .where(TextBlock.page_id == page_id, TextBlock.source == BlockSource.MANUAL)
            .limit(1)
        )
        reviewed_res = await db.execute(
            select(TextBlock)
            .where(TextBlock.page_id == page_id, TextBlock.review_status == ReviewStatus.REVIEWED)
            .limit(1)
        )
        has_manual = manual_res.scalars().first() is not None
        has_reviewed = reviewed_res.scalars().first() is not None
        if has_manual or has_reviewed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Existem edições protegidas. Use force=true para sobrescrever",
                    "has_manual": has_manual,
                    "has_reviewed": has_reviewed,
                },
            )

    run = ProcessingRun(page_id=page_id, run_type=RunType.FULL)
    pool = await queue.get_pool()
    blocks = await _dispatch_and_wait(pool, db, page, run)
    return ProcessPageOut(
        page=_page_to_summary(page, blocks),
        blocos=[_block_to_export(b) for b in blocks],
    )


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
    page = await _get_or_404(page_id, db)

    if page.status == PageStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A página está sendo processada, tente em instantes",
        )

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

    if page.status == PageStatus.APPROVED:
        page.status = PageStatus.REVIEW
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=[b.model_dump() for b in body],
    )


class ReorderAutoOut(BaseModel):
    blocos: list[TextBlockExport]
    reordered_count: int


class BlockOrderIn(BaseModel):
    block_ids: list[UUID] = Field(..., min_length=1)


@router.post("/{page_id}/reorder/auto", response_model=ReorderAutoOut)
async def reorder_auto(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ReorderAutoOut:
    """Recalculate block reading order from stored bboxes using the same pipeline stages."""
    from agent.stages.divisa import DivisaStage  # noqa: PLC0415
    from agent.stages.reading_order import ReadingOrderStage  # noqa: PLC0415
    from agent.state import BBox, DialogueState, PageAnalysisState  # noqa: PLC0415

    page = await _get_or_404(page_id, db)

    if page.status == PageStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A página está sendo processada, tente em instantes",
        )

    result = await db.execute(
        select(TextBlock)
        .where(TextBlock.page_id == page_id)
        .options(selectinload(TextBlock.translation_suggestions))
    )
    blocks = list(result.scalars().all())

    if not blocks:
        return ReorderAutoOut(blocos=[], reordered_count=0)

    blocks_with_bbox = [b for b in blocks if b.bbox]
    blocks_without_bbox = [b for b in blocks if not b.bbox]

    if not blocks_with_bbox:
        ordered = sorted(blocks, key=lambda b: b.order_number)
        return ReorderAutoOut(blocos=[_block_to_export(b) for b in ordered], reordered_count=0)

    from uuid import uuid4 as _uuid4  # noqa: PLC0415

    dialogues = [
        DialogueState(id=str(b.id), bbox=BBox.from_dict(b.bbox))  # type: ignore[arg-type]
        for b in blocks_with_bbox
    ]
    state = PageAnalysisState(
        page_id=page_id,
        run_id=_uuid4(),
        image_path=page.file_path,
        page_width=page.width,
        page_height=page.height,
        dialogues=dialogues,
    )

    state = await DivisaStage().run(state)
    state = await ReadingOrderStage().run(state)

    new_order_by_id: dict[str, int] = {
        d.id: d.order for d in state.dialogues if d.order is not None
    }

    total = len(blocks)
    # Use temp values above total to avoid unique-constraint conflicts during flush
    for i, b in enumerate(blocks):
        b.order_number = total + 1 + i
    await db.flush()

    for b in blocks_with_bbox:
        b.order_number = new_order_by_id.get(str(b.id), total)

    max_bbox_order = max(new_order_by_id.values(), default=0)
    for i, b in enumerate(blocks_without_bbox):
        b.order_number = max_bbox_order + 1 + i

    await db.commit()

    all_blocks = sorted(blocks, key=lambda b: b.order_number)
    for b in all_blocks:
        await db.refresh(b)

    return ReorderAutoOut(
        blocos=[_block_to_export(b) for b in all_blocks],
        reordered_count=len(blocks_with_bbox),
    )


@router.put("/{page_id}/blocks/order", response_model=list[TextBlockExport])
async def reorder_blocks(
    page_id: UUID,
    body: BlockOrderIn,
    db: AsyncSession = Depends(get_db),
) -> list[TextBlockExport]:
    page = await _get_or_404(page_id, db)

    result = await db.execute(
        select(TextBlock)
        .where(TextBlock.page_id == page_id)
        .options(selectinload(TextBlock.translation_suggestions))
    )
    blocks_by_id = {b.id: b for b in result.scalars().all()}

    if set(body.block_ids) != set(blocks_by_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="block_ids deve conter exatamente os IDs dos blocos da página",
        )

    # Use temporary values above current range to avoid unique-constraint conflicts
    n = len(body.block_ids)
    for i, block_id in enumerate(body.block_ids):
        blocks_by_id[block_id].order_number = n + 1 + i
    await db.flush()

    for i, block_id in enumerate(body.block_ids):
        blocks_by_id[block_id].order_number = i + 1
    if page.status == PageStatus.APPROVED:
        page.status = PageStatus.REVIEW
    await db.commit()

    ordered = [blocks_by_id[bid] for bid in body.block_ids]
    for b in ordered:
        await db.refresh(b)
    return [_block_to_export(b) for b in ordered]


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
