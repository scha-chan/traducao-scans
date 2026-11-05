import logging
from typing import Any

import redis.asyncio as aioredis
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
    ctx["redis"] = aioredis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
    logger.info("Worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    engine = ctx.get("db_engine")
    if engine is not None:
        await engine.dispose()
    redis_client = ctx.get("redis")
    if redis_client is not None:
        await redis_client.aclose()
    logger.info("Worker shut down")


class WorkerSettings:
    functions = [analyze_page]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_tries = 5
    job_timeout = 660
    keep_result = 3600
