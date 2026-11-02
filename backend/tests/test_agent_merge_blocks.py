"""Unit tests for MergeBlocksStage (F3-AG-06)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent.stages.merge_blocks import MergeBlocksStage
from agent.state import BBox, DialogueState, PageAnalysisState


def _make_state(dialogues: list[DialogueState]) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="/fake/page.png",
        dialogues=dialogues,
    )


def _d(
    x: int, y: int, w: int, h: int, original: str = "", lines: list[str] | None = None
) -> DialogueState:
    d = DialogueState(id=str(uuid4()), bbox=BBox(x=x, y=y, width=w, height=h))
    d.original = original
    d.lines = lines or ([original] if original else [])
    return d


# ---------------------------------------------------------------------------
# Stage name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage_name() -> None:
    assert MergeBlocksStage().name == "merge_blocks"


# ---------------------------------------------------------------------------
# Empty / single dialogue passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_dialogues_unchanged() -> None:
    result = await MergeBlocksStage().run(_make_state([]))
    assert result.dialogues == []


@pytest.mark.asyncio
async def test_single_dialogue_unchanged() -> None:
    d = _d(100, 10, 40, 200, "テスト")
    result = await MergeBlocksStage().run(_make_state([d]))
    assert len(result.dialogues) == 1
    assert result.dialogues[0].original == "テスト"


# ---------------------------------------------------------------------------
# Furigana detection and merging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_furigana_absorbed() -> None:
    """Small adjacent region should be absorbed as ruby, not kept as dialogue."""
    parent = _d(x=100, y=10, w=40, h=200, original="誰よりも")
    furigana = _d(x=142, y=10, w=15, h=200, original="だれ")  # width ≤ 50% of 40? No: 15 ≤ 20 ✓
    result = await MergeBlocksStage().run(_make_state([parent, furigana]))
    assert len(result.dialogues) == 1
    assert result.dialogues[0].id == parent.id
    assert len(result.dialogues[0].ruby) == 1
    assert result.dialogues[0].ruby[0].reading == "だれ"


@pytest.mark.asyncio
async def test_furigana_base_is_empty_string() -> None:
    parent = _d(x=100, y=0, w=40, h=200, original="君")
    furigana = _d(x=142, y=0, w=15, h=200, original="きみ")
    result = await MergeBlocksStage().run(_make_state([parent, furigana]))
    assert result.dialogues[0].ruby[0].base == ""


@pytest.mark.asyncio
async def test_furigana_too_wide_not_absorbed() -> None:
    """If candidate is wider than 50% of parent, it is NOT furigana."""
    parent = _d(x=100, y=0, w=40, h=200, original="誰")
    wide_neighbor = _d(x=142, y=0, w=25, h=200, original="other")  # 25 > 20 (50% of 40)
    result = await MergeBlocksStage().run(_make_state([parent, wide_neighbor]))
    assert len(result.dialogues) == 2


@pytest.mark.asyncio
async def test_furigana_no_overlap_not_absorbed() -> None:
    """Non-overlapping Y ranges → not furigana."""
    parent = _d(x=100, y=0, w=40, h=100, original="誰")
    separate = _d(x=142, y=200, w=15, h=100, original="だれ")  # no Y overlap
    result = await MergeBlocksStage().run(_make_state([parent, separate]))
    assert len(result.dialogues) == 2


@pytest.mark.asyncio
async def test_furigana_empty_reading_not_added_to_ruby() -> None:
    """A furigana region with empty original contributes no RubyPair."""
    parent = _d(x=100, y=0, w=40, h=200, original="誰")
    furigana = _d(x=142, y=0, w=15, h=200, original="")
    result = await MergeBlocksStage().run(_make_state([parent, furigana]))
    assert len(result.dialogues) == 1
    assert result.dialogues[0].ruby == []


# ---------------------------------------------------------------------------
# Continuous-column grouping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adjacent_columns_merged() -> None:
    """Two horizontally adjacent, vertically overlapping columns should merge."""
    col_a = _d(x=100, y=0, w=40, h=200, original="──誰よりも", lines=["──誰よりも"])
    col_b = _d(x=55, y=0, w=40, h=200, original="何よりも", lines=["何よりも"])
    # gap = 100 - (55+40) = 5 ≤ 15
    result = await MergeBlocksStage().run(_make_state([col_a, col_b]))
    assert len(result.dialogues) == 1
    assert "──誰よりも" in result.dialogues[0].original
    assert "何よりも" in result.dialogues[0].original


@pytest.mark.asyncio
async def test_merged_block_lines_combined() -> None:
    col_a = _d(x=100, y=0, w=40, h=200, original="君の", lines=["君の"])
    col_b = _d(x=55, y=0, w=40, h=200, original="おかげだから", lines=["おかげだから"])
    result = await MergeBlocksStage().run(_make_state([col_a, col_b]))
    assert "君の" in result.dialogues[0].lines
    assert "おかげだから" in result.dialogues[0].lines


@pytest.mark.asyncio
async def test_columns_too_far_not_merged() -> None:
    """Gap > MERGE_GAP_PX: columns should NOT be merged."""
    col_a = _d(x=200, y=0, w=40, h=200, original="A")
    col_b = _d(x=100, y=0, w=40, h=200, original="B")  # gap = 200-(100+40)=60 > 15
    result = await MergeBlocksStage().run(_make_state([col_a, col_b]))
    assert len(result.dialogues) == 2


@pytest.mark.asyncio
async def test_columns_no_y_overlap_not_merged() -> None:
    """Regions without vertical overlap should not merge even if horizontally close."""
    col_a = _d(x=100, y=0, w=40, h=100, original="A")
    col_b = _d(x=55, y=200, w=40, h=100, original="B")  # no Y overlap
    result = await MergeBlocksStage().run(_make_state([col_a, col_b]))
    assert len(result.dialogues) == 2


@pytest.mark.asyncio
async def test_merged_bbox_is_union() -> None:
    col_a = _d(x=100, y=0, w=40, h=200, original="A")
    col_b = _d(x=55, y=10, w=40, h=180, original="B")
    result = await MergeBlocksStage().run(_make_state([col_a, col_b]))
    bbox = result.dialogues[0].bbox
    assert bbox.x == 55
    assert bbox.y == 0
    assert bbox.width == 85  # 140 - 55
    assert bbox.height == 200


@pytest.mark.asyncio
async def test_merged_confidence_is_minimum() -> None:
    col_a = _d(x=100, y=0, w=40, h=200, original="A")
    col_b = _d(x=55, y=0, w=40, h=200, original="B")
    col_a.ocr_confidence = 0.90
    col_b.ocr_confidence = 0.70
    result = await MergeBlocksStage().run(_make_state([col_a, col_b]))
    assert result.dialogues[0].ocr_confidence == pytest.approx(0.70)


@pytest.mark.asyncio
async def test_merged_needs_review_propagated() -> None:
    col_a = _d(x=100, y=0, w=40, h=200, original="A")
    col_b = _d(x=55, y=0, w=40, h=200, original="B")
    col_b.needs_review = True
    col_b.review_reason = "low_ocr_confidence"
    result = await MergeBlocksStage().run(_make_state([col_a, col_b]))
    assert result.dialogues[0].needs_review is True
