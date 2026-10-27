import logging
from typing import Any

from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.settings import settings
from worker.tasks.analysis import analyze_page

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    engine = create_async_engine(settings.database_url)
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    ctx["db_engine"] = engine
    ctx["db_factory"] = factory
    logger.info("Worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    engine = ctx.get("db_engine")
    if engine is not None:
        await engine.dispose()
    logger.info("Worker shut down")


class WorkerSettings:
    functions = [analyze_page]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_tries = 5
    job_timeout = 200
    keep_result = 3600
