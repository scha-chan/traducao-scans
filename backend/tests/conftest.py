"""Fixtures compartilhadas para os testes de API."""

import io
import os
import re
from collections.abc import AsyncGenerator
from pathlib import Path

# Must be set before any app import so Settings() picks up the SQLite URL
# and engine.py does not try to connect to asyncpg.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db import Base, get_db  # noqa: E402
from app.db.models import (  # noqa: E402
    Character,
    CharacterMention,
    Folder,
    GlossaryEntry,
    GlossaryOccurrence,
    Page,
    ProcessingRun,
    TextBlock,
    TranslationSuggestion,
    Work,
)
from app.main import app  # noqa: E402
from app.settings import settings  # noqa: E402

_TABLES = [
    Work.__table__,
    Folder.__table__,
    Page.__table__,
    Character.__table__,
    CharacterMention.__table__,
    ProcessingRun.__table__,
    TextBlock.__table__,
    TranslationSuggestion.__table__,
    GlossaryEntry.__table__,
    GlossaryOccurrence.__table__,
]


def _strip_sqlite_unsupported_ddl(ddl: str) -> str:
    # SQLite does not support DEFERRABLE INITIALLY in CREATE TABLE DDL
    return re.sub(r"\s+DEFERRABLE\s+INITIALLY\s+\w+", "", ddl, flags=re.IGNORECASE)


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    engine = create_async_engine(db_url)

    @event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
    def _fix_sqlite_ddl(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,  # noqa: ANN001
    ) -> tuple[str, object]:
        return _strip_sqlite_unsupported_ddl(statement), parameters

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
