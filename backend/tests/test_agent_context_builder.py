"""Unit tests for TranslationContextBuilder (F5-AG-02)."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from agent.context_builder import (  # noqa: E402
    TranslationContext,
    TranslationContextBuilder,
)
from app.db import Base  # noqa: E402
from app.db.models import (  # noqa: E402
    BlockSource,
    Character,
    CharacterMention,
    Folder,
    Page,
    PageStatus,
    ReviewStatus,
    TextBlock,
    TranslationSuggestion,
    Work,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _remove_deferrable_constraints() -> list[object]:
    """Temporarily remove DEFERRABLE UniqueConstraints from TextBlock for SQLite.

    SQLite does not support DEFERRABLE on table constraints; we pull them out
    before create_all and restore them afterwards so other tests are unaffected.
    """
    from sqlalchemy import UniqueConstraint  # noqa: PLC0415

    removed = [
        c
        for c in list(TextBlock.__table__.constraints)
        if isinstance(c, UniqueConstraint) and getattr(c, "deferrable", False)
    ]
    for c in removed:
        TextBlock.__table__.constraints.discard(c)
    return removed


def _restore_constraints(removed: list[object]) -> None:
    for c in removed:
        TextBlock.__table__.constraints.add(c)  # type: ignore[arg-type]


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    removed = _remove_deferrable_constraints()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _restore_constraints(removed)

    async with session_factory() as s:
        yield s

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


async def _make_work(session: AsyncSession, title: str = "Test Work") -> Work:
    work = Work(id=uuid4(), title=title)
    session.add(work)
    await session.flush()
    return work


async def _make_folder(session: AsyncSession, work: Work | None = None) -> Folder:
    folder = Folder(id=uuid4(), name=f"folder-{uuid4()}", work_id=work.id if work else None)
    session.add(folder)
    await session.flush()
    return folder


async def _make_page(session: AsyncSession, folder: Folder, page_number: int = 1) -> Page:
    page = Page(
        id=uuid4(),
        folder_id=folder.id,
        file_name=f"page{page_number}.jpg",
        file_path=f"/fake/page{page_number}.jpg",
        mime_type="image/jpeg",
        page_number=page_number,
        status=PageStatus.PENDING,
    )
    session.add(page)
    await session.flush()
    return page


def _make_block(
    page: Page,
    order_number: int,
    original: str | None = "テスト",
    block_type: str | None = "#",
    location: str | None = "Topo esquerda",
    ocr_confidence: float | None = 0.95,
    review_status: ReviewStatus = ReviewStatus.PENDING,
) -> TextBlock:
    return TextBlock(
        id=uuid4(),
        page_id=page.id,
        order_number=order_number,
        type=block_type,
        original=original,
        location=location,
        ocr_confidence=ocr_confidence,
        review_status=review_status,
        source=BlockSource.AUTO,
    )


# ---------------------------------------------------------------------------
# Tests — basic build
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_minimal(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)
    block = _make_block(page, order_number=1)
    session.add(block)
    await session.flush()

    ctx: TranslationContext = await TranslationContextBuilder().build(block, page, session)

    assert ctx.original == "テスト"
    assert ctx.block_type == "#"
    assert ctx.location == "Topo esquerda"
    assert ctx.ocr_confidence == pytest.approx(0.95)
    assert ctx.output_language == "pt-BR"
    assert ctx.previous_block is None
    assert ctx.next_block is None
    assert ctx.characters == []
    assert ctx.prior_translations == []


@pytest.mark.asyncio
async def test_build_block_with_no_original(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)
    block = _make_block(page, order_number=1, original=None)
    session.add(block)
    await session.flush()

    ctx = await TranslationContextBuilder().build(block, page, session)

    assert ctx.original is None
    assert ctx.prior_translations == []


# ---------------------------------------------------------------------------
# Tests — neighbours
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_neighbours_none_when_only_block(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)
    block = _make_block(page, order_number=2)
    session.add(block)
    await session.flush()

    ctx = await TranslationContextBuilder().build(block, page, session)
    assert ctx.previous_block is None
    assert ctx.next_block is None


@pytest.mark.asyncio
async def test_neighbours_prev_and_next(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)

    b1 = _make_block(page, order_number=1, original="最初")
    b2 = _make_block(page, order_number=2, original="中間")
    b3 = _make_block(page, order_number=3, original="最後")
    session.add_all([b1, b2, b3])
    await session.flush()

    ctx = await TranslationContextBuilder().build(b2, page, session)
    assert ctx.previous_block is not None
    assert ctx.previous_block.original == "最初"
    assert ctx.next_block is not None
    assert ctx.next_block.original == "最後"


@pytest.mark.asyncio
async def test_neighbour_original_none_becomes_empty_string(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)

    b1 = _make_block(page, order_number=1, original=None)
    b2 = _make_block(page, order_number=2, original="テスト")
    session.add_all([b1, b2])
    await session.flush()

    ctx = await TranslationContextBuilder().build(b2, page, session)
    assert ctx.previous_block is not None
    assert ctx.previous_block.original == ""


@pytest.mark.asyncio
async def test_neighbours_carry_type_and_location(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)

    b1 = _make_block(page, order_number=1, block_type="$", location="Centro")
    b2 = _make_block(page, order_number=2)
    session.add_all([b1, b2])
    await session.flush()

    ctx = await TranslationContextBuilder().build(b2, page, session)
    assert ctx.previous_block is not None
    assert ctx.previous_block.block_type == "$"
    assert ctx.previous_block.location == "Centro"


# ---------------------------------------------------------------------------
# Tests — characters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_characters_empty_when_no_mentions(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)
    block = _make_block(page, order_number=1)
    session.add(block)
    await session.flush()

    ctx = await TranslationContextBuilder().build(block, page, session)
    assert ctx.characters == []


@pytest.mark.asyncio
async def test_characters_included_via_mentions(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)
    block = _make_block(page, order_number=1)
    session.add(block)

    char = Character(
        id=uuid4(),
        work_id=work.id,
        name_original="桜子",
        name_preferred="Sakiko",
        speech_register="infantil",
        notes="protagonista",
    )
    session.add(char)
    await session.flush()

    mention = CharacterMention(
        id=uuid4(),
        character_id=char.id,
        page_id=page.id,
        text_block_id=block.id,
    )
    session.add(mention)
    await session.flush()

    ctx = await TranslationContextBuilder().build(block, page, session)
    assert len(ctx.characters) == 1
    assert ctx.characters[0].name == "Sakiko"
    assert ctx.characters[0].speech_register == "infantil"
    assert ctx.characters[0].notes == "protagonista"


@pytest.mark.asyncio
async def test_character_name_falls_back_to_original(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)
    block = _make_block(page, order_number=1)
    session.add(block)

    char = Character(
        id=uuid4(),
        work_id=work.id,
        name_original="桜子",
        name_preferred=None,
    )
    session.add(char)
    await session.flush()

    mention = CharacterMention(
        id=uuid4(), character_id=char.id, page_id=page.id, text_block_id=block.id
    )
    session.add(mention)
    await session.flush()

    ctx = await TranslationContextBuilder().build(block, page, session)
    assert ctx.characters[0].name == "桜子"


# ---------------------------------------------------------------------------
# Tests — prior translations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prior_translations_empty_when_none_reviewed(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)
    block = _make_block(page, order_number=1, original="同じテキスト")
    session.add(block)
    await session.flush()

    ctx = await TranslationContextBuilder().build(block, page, session)
    assert ctx.prior_translations == []


@pytest.mark.asyncio
async def test_prior_translations_found_from_reviewed_block(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)

    page1 = await _make_page(session, folder, page_number=1)
    page2 = await _make_page(session, folder, page_number=2)

    reviewed_block = _make_block(
        page1,
        order_number=1,
        original="同じテキスト",
        review_status=ReviewStatus.REVIEWED,
    )
    session.add(reviewed_block)
    await session.flush()

    suggestion = TranslationSuggestion(
        id=uuid4(),
        text_block_id=reviewed_block.id,
        translation="Mesmo texto",
        source=BlockSource.AUTO,
    )
    session.add(suggestion)
    await session.flush()

    target_block = _make_block(page2, order_number=1, original="同じテキスト")
    session.add(target_block)
    await session.flush()

    ctx = await TranslationContextBuilder().build(target_block, page2, session)
    assert len(ctx.prior_translations) == 1
    assert ctx.prior_translations[0].page_number == 1
    assert ctx.prior_translations[0].translation == "Mesmo texto"


@pytest.mark.asyncio
async def test_prior_translations_skips_pending_blocks(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)

    page1 = await _make_page(session, folder, page_number=1)
    page2 = await _make_page(session, folder, page_number=2)

    pending_block = _make_block(
        page1,
        order_number=1,
        original="同じテキスト",
        review_status=ReviewStatus.PENDING,
    )
    session.add(pending_block)
    await session.flush()

    suggestion = TranslationSuggestion(
        id=uuid4(),
        text_block_id=pending_block.id,
        translation="Tradução não aprovada",
        source=BlockSource.AUTO,
    )
    session.add(suggestion)
    await session.flush()

    target_block = _make_block(page2, order_number=1, original="同じテキスト")
    session.add(target_block)
    await session.flush()

    ctx = await TranslationContextBuilder().build(target_block, page2, session)
    assert ctx.prior_translations == []


@pytest.mark.asyncio
async def test_prior_translations_empty_when_no_original(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)
    page = await _make_page(session, folder)
    block = _make_block(page, order_number=1, original=None)
    session.add(block)
    await session.flush()

    ctx = await TranslationContextBuilder().build(block, page, session)
    assert ctx.prior_translations == []


@pytest.mark.asyncio
async def test_prior_translations_empty_when_folder_has_no_work(session: AsyncSession) -> None:
    folder = await _make_folder(session, work=None)
    page = await _make_page(session, folder)
    block = _make_block(page, order_number=1, original="テスト")
    session.add(block)
    await session.flush()

    ctx = await TranslationContextBuilder().build(block, page, session)
    assert ctx.prior_translations == []


@pytest.mark.asyncio
async def test_prior_translations_ordered_by_page_number(session: AsyncSession) -> None:
    work = await _make_work(session)
    folder = await _make_folder(session, work)

    page3 = await _make_page(session, folder, page_number=3)
    page1 = await _make_page(session, folder, page_number=1)
    page5 = await _make_page(session, folder, page_number=5)

    for pg in (page3, page1, page5):
        b = _make_block(
            pg, order_number=1, original="繰り返し", review_status=ReviewStatus.REVIEWED
        )
        session.add(b)
        await session.flush()
        s = TranslationSuggestion(
            id=uuid4(),
            text_block_id=b.id,
            translation=f"Repetido p{pg.page_number}",
            source=BlockSource.AUTO,
        )
        session.add(s)
        await session.flush()

    target_page = await _make_page(session, folder, page_number=7)
    target_block = _make_block(target_page, order_number=1, original="繰り返し")
    session.add(target_block)
    await session.flush()

    ctx = await TranslationContextBuilder().build(target_block, target_page, session)
    page_numbers = [pt.page_number for pt in ctx.prior_translations]
    assert page_numbers == sorted(page_numbers)
