"""Fixtures compartilhadas para os testes de API."""

import io
import os
from collections.abc import AsyncGenerator
from pathlib import Path

# Must be set before any app import so Settings() picks up the SQLite URL
# and engine.py does not try to connect to asyncpg.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db import Base, get_db  # noqa: E402
from app.db.models import Folder, Page, Work  # noqa: E402
from app.main import app  # noqa: E402
from app.settings import settings  # noqa: E402

_TABLES = [Work.__table__, Folder.__table__, Page.__table__]


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    engine = create_async_engine(db_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=_TABLES)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=_TABLES)

    await engine.dispose()


@pytest.fixture
def png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()
