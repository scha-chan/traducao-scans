import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from arq import Retry
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Page, PageStatus, ProcessingRun, RunStatus

logger = logging.getLogger(__name__)


async def analyze_page(ctx: dict[str, Any], page_id: str, run_id: str) -> dict[str, object]:
    """Process a manga page through the OCR + translation pipeline.

    Full pipeline wired in F5-AG-01; this scaffold updates ProcessingRun status
    and handles exponential-backoff retry for transient failures.
    """
    db_factory: async_sessionmaker[AsyncSession] = ctx["db_factory"]
    attempt: int = ctx.get("job_try", 1)

    async with db_factory() as db:
        run: ProcessingRun | None = await db.get(ProcessingRun, UUID(run_id))
        if run is None:
            logger.error("ProcessingRun %s not found, skipping", run_id)
            return {"ok": False, "error": "run_not_found"}

        run.started_at = datetime.now(UTC)
        run.status = RunStatus.RUNNING
        await db.commit()

        try:
            block_count = await _pipeline(db, UUID(page_id))

            run.status = RunStatus.SUCCESS
            run.finished_at = datetime.now(UTC)
            success_page: Page | None = await db.get(Page, UUID(page_id))
            if success_page is not None:
                success_page.status = PageStatus.REVIEW
            await db.commit()

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
            logger.exception("Fatal error on page %s attempt %d", page_id, attempt)
            raise


class _TransientError(Exception):
    """Transient failure (network, rate-limit, temporary unavailability) — safe to retry."""


async def _pipeline(db: AsyncSession, page_id: UUID) -> int:
    """Scaffold — OCR + translation to be wired in F5-AG-01."""
    return 0
