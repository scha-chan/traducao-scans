import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from arq import Retry
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent.orchestrator import build_pipeline, build_translate_only_pipeline
from agent.prompt_loader import load_prompt
from agent.state import BBox, DialogueState, PageAnalysisState
from app.db.models import (
    BlockSource,
    Page,
    PageStatus,
    ProcessingRun,
    RunStatus,
    RunType,
    TextBlock,
    TranslationSuggestion,
)
from app.settings import settings

logger = logging.getLogger(__name__)


async def analyze_page(ctx: dict[str, Any], page_id: str, run_id: str) -> dict[str, object]:
    """Process a manga page through the OCR + translation pipeline.

    Full pipeline wired in F5-AG-01; this scaffold updates ProcessingRun status
    and handles exponential-backoff retry for transient failures.
    """
    db_factory: async_sessionmaker[AsyncSession] = ctx["db_factory"]
    redis_client = ctx.get("redis")
    attempt: int = ctx.get("job_try", 1)

    async def _publish(event: str, **extra: object) -> None:
        if redis_client is not None:
            payload = json.dumps({"event": event, "page_id": page_id, "run_id": run_id, **extra})
            await redis_client.publish(f"page:{page_id}:events", payload)

    async with db_factory() as db:
        run: ProcessingRun | None = await db.get(ProcessingRun, UUID(run_id))
        if run is None:
            logger.error("ProcessingRun %s not found, skipping", run_id)
            return {"ok": False, "error": "run_not_found"}

        run.started_at = datetime.now(UTC)
        run.status = RunStatus.RUNNING
        _, run.prompt_version = load_prompt(settings.prompt_file)
        await db.commit()

        try:
            block_count = await _pipeline(db, UUID(page_id), run)

            run.status = RunStatus.SUCCESS
            run.finished_at = datetime.now(UTC)
            success_page: Page | None = await db.get(Page, UUID(page_id))
            if success_page is not None:
                success_page.status = PageStatus.REVIEW
            await db.commit()

            await _publish("done", block_count=block_count)
            logger.info("Page %s analysed: %d blocks", page_id, block_count)
            return {"ok": True, "page_id": page_id, "block_count": block_count}

        except _TransientError as exc:
            await db.rollback()
            run.status = RunStatus.ERROR
            run.finished_at = datetime.now(UTC)
            run.error_message = str(exc)
            await db.commit()
            delay = min(2**attempt, 300)
            logger.warning("Transient error attempt %d, retrying in %ds: %s", attempt, delay, exc)
            raise Retry(defer=timedelta(seconds=delay)) from exc

        except Exception as exc:
            await db.rollback()
            run.status = RunStatus.ERROR
            run.finished_at = datetime.now(UTC)
            run.error_message = str(exc)
            error_page: Page | None = await db.get(Page, UUID(page_id))
            if error_page is not None:
                error_page.status = PageStatus.ERROR
                error_page.error_message = str(exc)
            await db.commit()
            await _publish("error", message=str(exc))
            logger.exception("Fatal error on page %s attempt %d", page_id, attempt)
            raise


class _TransientError(Exception):
    """Transient failure (network, rate-limit, temporary unavailability) — safe to retry."""


async def _pipeline(db: AsyncSession, page_id: UUID, run: ProcessingRun) -> int:
    """Run the analysis pipeline via Orchestrator and persist results.

    Stages F3-AG-02 – F3-AG-07 fill dialogues; this scaffold wires the
    orchestrator call and persists model_metadata (spans + agent_log).
    """
    page: Page | None = await db.get(Page, page_id)
    if page is None:
        raise ValueError(f"Page {page_id} not found")

    if run.run_type == RunType.FULL:
        await db.execute(delete(TextBlock).where(TextBlock.page_id == page_id))
        initial_state = PageAnalysisState(
            page_id=page_id,
            run_id=run.id,
            image_path=page.file_path,
        )
        orchestrator = build_pipeline()
        final_state = await orchestrator.run(initial_state)
    else:
        final_state = await _run_translate_only(db, page, run)

    run.model_metadata = {
        "spans": [s.to_dict() for s in final_state.spans],
        "agent_log": [e.to_dict() for e in final_state.agent_log],
    }

    return len(final_state.dialogues)


async def _run_translate_only(
    db: AsyncSession, page: Page, run: ProcessingRun
) -> PageAnalysisState:
    """Delete AUTO suggestions, run only TranslationStage, persist new suggestions."""
    blocks_result = await db.execute(select(TextBlock).where(TextBlock.page_id == page.id))
    blocks = list(blocks_result.scalars().all())

    if blocks:
        block_ids = [b.id for b in blocks]
        await db.execute(
            delete(TranslationSuggestion).where(
                TranslationSuggestion.text_block_id.in_(block_ids),
                TranslationSuggestion.source == BlockSource.AUTO,
            )
        )
        await db.flush()

    dialogues = [
        DialogueState(
            id=str(b.id),
            bbox=BBox.from_dict(b.bbox) if b.bbox else BBox(0, 0, 0, 0),
            original=b.original,
        )
        for b in blocks
        if b.original
    ]

    initial_state = PageAnalysisState(
        page_id=page.id,
        run_id=run.id,
        image_path=page.file_path,
        dialogues=dialogues,
    )

    final_state = await build_translate_only_pipeline().run(initial_state)

    for dialogue in final_state.dialogues:
        for candidate in dialogue.translations:
            db.add(
                TranslationSuggestion(
                    text_block_id=UUID(dialogue.id),
                    translation=candidate.translation,
                    observation=candidate.observation,
                    relevance=candidate.relevance,
                    source=BlockSource.AUTO,
                )
            )

    return final_state
