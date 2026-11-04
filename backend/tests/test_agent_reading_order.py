"""Tests for ReadingOrderStage, DivisaStage helpers and both strategies (F4-AG-01/04)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent.stages.reading_order import (
    ColumnRtlStrategy,
    PanelAwareStrategy,
    ReadingOrderStage,
    TieredColumnRtlStrategy,
    _group_into_columns,
    _split_at_wide_blocks,
)
from agent.state import BBox, DialogueState, PageAnalysisState, PanelRegion

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dialogue(
    x: int,
    y: int,
    width: int,
    height: int,
    did: str | None = None,
) -> DialogueState:
    return DialogueState(
        id=did or str(uuid4()),
        bbox=BBox(x=x, y=y, width=width, height=height),
    )


def _make_state(
    dialogues: list[DialogueState],
    page_width: int = 750,
    page_height: int = 1200,
    panels: list[PanelRegion] | None = None,
) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="fake.png",
        page_width=page_width,
        page_height=page_height,
        panels=panels or [],
        dialogues=dialogues,
    )


def _ids_ordered(state: PageAnalysisState) -> list[str]:
    return [d.id for d in sorted(state.dialogues, key=lambda d: d.order or 0)]


# ---------------------------------------------------------------------------
# Unit: _group_into_columns
# ---------------------------------------------------------------------------


def test_group_into_columns_separate() -> None:
    a = _make_dialogue(x=500, y=0, width=100, height=50, did="a")
    b = _make_dialogue(x=200, y=0, width=100, height=50, did="b")
    cols = _group_into_columns([a, b])
    assert len(cols) == 2


def test_group_into_columns_overlapping() -> None:
    # a and b overlap 70% of the smaller block's width (60/80 > 50%)
    a = _make_dialogue(x=100, y=0, width=100, height=200, did="a")
    b = _make_dialogue(x=120, y=210, width=80, height=200, did="b")
    cols = _group_into_columns([a, b])
    assert len(cols) == 1


def test_group_into_columns_transitivity() -> None:
    # a-b share column, b-c share column → all three in same column
    a = _make_dialogue(x=100, y=0, width=100, height=50, did="a")
    b = _make_dialogue(x=110, y=60, width=100, height=50, did="b")
    c = _make_dialogue(x=120, y=120, width=100, height=50, did="c")
    cols = _group_into_columns([a, b, c])
    assert len(cols) == 1


# ---------------------------------------------------------------------------
# Unit: _split_at_wide_blocks
# ---------------------------------------------------------------------------


def test_split_wide_block_creates_own_subtier() -> None:
    narrow1 = _make_dialogue(x=300, y=10, width=100, height=40, did="n1")
    narrow2 = _make_dialogue(x=200, y=10, width=100, height=40, did="n2")
    wide = _make_dialogue(x=20, y=100, width=600, height=50, did="wide")  # 600/750 = 80%
    narrow3 = _make_dialogue(x=100, y=200, width=100, height=40, did="n3")

    sub_tiers = _split_at_wide_blocks([narrow1, narrow2, wide, narrow3], page_width=750)
    # Expect: [narrow1, narrow2], [wide], [narrow3]
    assert len(sub_tiers) == 3
    assert any(d.id == "wide" for d in sub_tiers[1])
    assert len(sub_tiers[1]) == 1


def test_split_no_wide_blocks_returns_single_tier() -> None:
    blocks = [
        _make_dialogue(x=100, y=10, width=200, height=50),
        _make_dialogue(x=400, y=10, width=200, height=50),
    ]
    result = _split_at_wide_blocks(blocks, page_width=750)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Strategy: column_rtl (simple page, no tiers)
# ---------------------------------------------------------------------------


def test_column_rtl_rtl_order() -> None:
    # Three narrow columns from right to left
    right_col = _make_dialogue(x=600, y=100, width=80, height=200, did="right")
    mid_col = _make_dialogue(x=350, y=100, width=80, height=200, did="mid")
    left_col = _make_dialogue(x=100, y=100, width=80, height=200, did="left")

    strategy = ColumnRtlStrategy()
    ordered = strategy.order([right_col, mid_col, left_col], 750, 1200, [])
    assert [d.id for d in ordered] == ["right", "mid", "left"]


def test_column_rtl_within_column_top_to_bottom() -> None:
    top = _make_dialogue(x=500, y=50, width=80, height=100, did="top")
    bottom = _make_dialogue(x=520, y=200, width=80, height=100, did="bottom")

    strategy = ColumnRtlStrategy()
    ordered = strategy.order([bottom, top], 750, 1200, [])
    assert [d.id for d in ordered] == ["top", "bottom"]


# ---------------------------------------------------------------------------
# Strategy: tiered_column_rtl — pagina_01 reference (PRD §23.2)
# ---------------------------------------------------------------------------


def test_tiered_column_rtl_pagina01_order() -> None:
    """Full pagina_01 layout must reproduce the order in PRD §23.2."""
    blocks = [
        # Tier 1 (y < 548)
        ("b1", 590, 110, 50, 125),  # きめたよ!       → order 1
        ("b2", 505, 265, 40, 75),  # おれも          → order 2
        ("b3", 205, 50, 265, 80),  # だれかを…       → order 3
        ("b4", 100, 285, 95, 205),  # ──誰よりも…    → order 4
        # Tier 2 (y >= 548)
        ("b5", 490, 590, 145, 35),  # とくだ さきこ   → order 5
        ("b6", 590, 710, 65, 105),  # しあわせにするん → order 6
        ("b7", 490, 895, 145, 35),  # あべかわ さくら → order 7
        ("b8", 490, 1148, 145, 34),  # みやた ゆき     → order 8
        ("b9", 375, 590, 95, 425),  # 君のおかげだから → order 9
        ("b10", 65, 615, 235, 35),  # はせがわ ごうた → order 10
        ("b11", 65, 865, 235, 35),  # にしかわ じろう  → order 11
        ("b12", 65, 1135, 235, 35),  # くぼ りょうじ   → order 12
    ]
    dialogues = [_make_dialogue(x, y, w, h, did=did) for did, x, y, w, h in blocks]

    strategy = TieredColumnRtlStrategy()
    ordered = strategy.order(dialogues, page_width=750, page_height=1200, panel_divisa_ys=[548])

    result = [d.id for d in ordered]
    assert result == [f"b{i}" for i in range(1, 13)], result


# ---------------------------------------------------------------------------
# Strategy: tiered_column_rtl — banner_01 reference (PRD §23.3)
# ---------------------------------------------------------------------------


def test_tiered_column_rtl_banner01_order() -> None:
    """banner_01 has no divisa but block 4 is wide → sub-tier, order 1–4 correct."""
    blocks = [
        # Wide banner (750px page)
        ("b1", 440, 5, 210, 65),  # 上位5名に続く人気キャラは誰かな…!? → order 1
        ("b2", 240, 10, 195, 60),  # 幸福喫茶3丁目                       → order 2
        ("b3", 20, 20, 215, 50),  # 連載50回記念企画♡                   → order 3
        ("b4", 20, 95, 590, 55),  # キャラクターコンテスト結果発表!!     → order 4 (wide)
    ]
    dialogues = [_make_dialogue(x, y, w, h, did=did) for did, x, y, w, h in blocks]

    strategy = TieredColumnRtlStrategy()
    ordered = strategy.order(dialogues, page_width=750, page_height=166, panel_divisa_ys=[])

    result = [d.id for d in ordered]
    assert result == ["b1", "b2", "b3", "b4"], result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_dialogues_returns_empty() -> None:
    strategy = TieredColumnRtlStrategy()
    result = strategy.order([], 750, 1200, [])
    assert result == []


def test_single_dialogue_gets_order_one() -> None:
    d = _make_dialogue(x=100, y=100, width=100, height=100)
    strategy = TieredColumnRtlStrategy()
    result = strategy.order([d], 750, 1200, [])
    assert result[0].order == 1


def test_order_is_sequential_no_gaps() -> None:
    dialogues = [
        _make_dialogue(x=600 - i * 100, y=50 + i * 10, width=80, height=50) for i in range(5)
    ]
    strategy = TieredColumnRtlStrategy()
    result = strategy.order(dialogues, 750, 1200, [])
    orders = sorted(d.order for d in result if d.order is not None)
    assert orders == list(range(1, 6))


# ---------------------------------------------------------------------------
# ReadingOrderStage integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage_assigns_order_to_all_dialogues() -> None:
    dialogues = [
        _make_dialogue(x=500, y=100, width=100, height=50, did="a"),
        _make_dialogue(x=200, y=100, width=100, height=50, did="b"),
    ]
    state = _make_state(dialogues)
    stage = ReadingOrderStage(strategy=TieredColumnRtlStrategy())
    result = await stage.run(state)
    assert all(d.order is not None for d in result.dialogues)
    assert {d.order for d in result.dialogues} == {1, 2}


@pytest.mark.asyncio
async def test_stage_with_panel_divisa_from_state() -> None:
    dialogues = [
        _make_dialogue(x=500, y=100, width=100, height=50, did="tier1"),
        _make_dialogue(x=500, y=700, width=100, height=50, did="tier2"),
    ]
    panels = [PanelRegion(bbox=BBox(x=0, y=548, width=750, height=1))]
    state = _make_state(dialogues, panels=panels)
    stage = ReadingOrderStage(strategy=TieredColumnRtlStrategy())
    result = await stage.run(state)
    order_map = {d.id: d.order for d in result.dialogues}
    assert order_map["tier1"] == 1
    assert order_map["tier2"] == 2


@pytest.mark.asyncio
async def test_stage_noop_on_empty_state() -> None:
    state = _make_state([])
    stage = ReadingOrderStage()
    result = await stage.run(state)
    assert result.dialogues == []


# ---------------------------------------------------------------------------
# Tiebreak rules (PRD §6.1 rule 6)
# ---------------------------------------------------------------------------


def test_tiebreak_centre_x_desc_within_column() -> None:
    """Within a column, blocks at the same top-y are ordered by centre-x descending."""
    # Both blocks share a column (exactly 50% horizontal overlap)
    # a: x=300, width=200 → cx=400, right=500
    # b: x=200, width=200 → cx=300, right=400
    # overlap = min(500,400)-max(300,200) = 100; min_w=200 → 0.50 → same column
    a = _make_dialogue(x=300, y=100, width=200, height=50, did="a")  # cx=400
    b = _make_dialogue(x=200, y=100, width=200, height=50, did="b")  # cx=300

    strategy = ColumnRtlStrategy()
    ordered = strategy.order([b, a], 750, 1200, [])
    assert [d.id for d in ordered] == ["a", "b"]


# ---------------------------------------------------------------------------
# Strategy: panel_aware (V2-AG-03)
# ---------------------------------------------------------------------------


def _make_panel(x: int, y: int, width: int, height: int) -> PanelRegion:
    return PanelRegion(bbox=BBox(x=x, y=y, width=width, height=height))


def test_panel_aware_two_panels_rtl_order() -> None:
    """Two side-by-side panels on the same row → right panel read first."""
    # Right panel: x=400..750
    right_d = _make_dialogue(x=500, y=100, width=100, height=50, did="right_d")
    # Left panel: x=0..350
    left_d = _make_dialogue(x=100, y=100, width=100, height=50, did="left_d")

    right_panel = _make_panel(x=400, y=0, width=350, height=600)
    left_panel = _make_panel(x=0, y=0, width=350, height=600)

    strategy = PanelAwareStrategy()
    ordered = strategy.order([left_d, right_d], 750, 1200, [], panels=[right_panel, left_panel])
    assert [d.id for d in ordered] == ["right_d", "left_d"]


def test_panel_aware_two_rows_top_before_bottom() -> None:
    """Two vertically stacked panels → top panel read first."""
    top_d = _make_dialogue(x=100, y=100, width=100, height=50, did="top_d")
    bottom_d = _make_dialogue(x=100, y=700, width=100, height=50, did="bottom_d")

    top_panel = _make_panel(x=0, y=0, width=750, height=500)
    bottom_panel = _make_panel(x=0, y=600, width=750, height=600)

    strategy = PanelAwareStrategy()
    ordered = strategy.order([bottom_d, top_d], 750, 1200, [], panels=[top_panel, bottom_panel])
    assert [d.id for d in ordered] == ["top_d", "bottom_d"]


def test_panel_aware_four_panels_manga_order() -> None:
    """2×2 grid: top-right → top-left → bottom-right → bottom-left."""
    # Top row: y=0..500; bottom row: y=600..1200
    # Right col: x=400..750; left col: x=0..350
    tr_d = _make_dialogue(x=500, y=200, width=80, height=60, did="tr")
    tl_d = _make_dialogue(x=100, y=200, width=80, height=60, did="tl")
    br_d = _make_dialogue(x=500, y=800, width=80, height=60, did="br")
    bl_d = _make_dialogue(x=100, y=800, width=80, height=60, did="bl")

    panels = [
        _make_panel(x=400, y=0, width=350, height=500),  # top-right
        _make_panel(x=0, y=0, width=350, height=500),  # top-left
        _make_panel(x=400, y=600, width=350, height=600),  # bottom-right
        _make_panel(x=0, y=600, width=350, height=600),  # bottom-left
    ]
    strategy = PanelAwareStrategy()
    ordered = strategy.order([bl_d, br_d, tl_d, tr_d], 750, 1200, [], panels=panels)
    assert [d.id for d in ordered] == ["tr", "tl", "br", "bl"]


def test_panel_aware_unassigned_fallback_appended_last() -> None:
    """Dialogue outside all panels is appended after all panel dialogues."""
    inside_d = _make_dialogue(x=100, y=100, width=80, height=50, did="inside")
    outside_d = _make_dialogue(x=680, y=1100, width=50, height=50, did="outside")

    panel = _make_panel(x=0, y=0, width=750, height=500)

    strategy = PanelAwareStrategy()
    ordered = strategy.order([outside_d, inside_d], 750, 1200, [], panels=[panel])
    assert ordered[0].id == "inside"
    assert ordered[1].id == "outside"
    assert ordered[0].order == 1
    assert ordered[1].order == 2


def test_panel_aware_no_panels_falls_back_to_tiered() -> None:
    """With no panels, panel_aware degrades to tiered_column_rtl."""
    right = _make_dialogue(x=600, y=100, width=80, height=50, did="right")
    left = _make_dialogue(x=100, y=100, width=80, height=50, did="left")

    strategy = PanelAwareStrategy()
    ordered = strategy.order([left, right], 750, 1200, [], panels=[])
    assert [d.id for d in ordered] == ["right", "left"]


def test_panel_aware_column_rtl_within_panel() -> None:
    """Within a single panel, dialogues obey column_rtl (right column first)."""
    panel = _make_panel(x=0, y=0, width=750, height=600)

    right_d = _make_dialogue(x=580, y=100, width=80, height=100, did="right_d")
    left_d = _make_dialogue(x=100, y=100, width=80, height=100, did="left_d")

    strategy = PanelAwareStrategy()
    ordered = strategy.order([left_d, right_d], 750, 1200, [], panels=[panel])
    assert [d.id for d in ordered] == ["right_d", "left_d"]


@pytest.mark.asyncio
async def test_stage_panel_aware_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """ReadingOrderStage selects PanelAwareStrategy when env var is set."""
    monkeypatch.setenv("READING_ORDER_STRATEGY", "panel_aware")
    import importlib

    import agent.stages.reading_order as ro_mod

    importlib.reload(ro_mod)

    stage = ro_mod.ReadingOrderStage()
    assert isinstance(stage._strategy, ro_mod.PanelAwareStrategy)
    # Clean up
    importlib.reload(ro_mod)


def test_tiebreak_centre_y_asc_within_column() -> None:
    """Blocks with same top-y and same centre-x use centre-y as final tiebreak (ascending)."""
    # Both at x=300, y=0, same width → same top-y, same cx
    # a: height=200 → cy=100; b: height=100 → cy=50 → b comes first
    a = _make_dialogue(x=300, y=0, width=100, height=200, did="a")  # cy=100
    b = _make_dialogue(x=300, y=0, width=100, height=100, did="b")  # cy=50

    strategy = ColumnRtlStrategy()
    ordered = strategy.order([a, b], 750, 1200, [])
    assert [d.id for d in ordered] == ["b", "a"]


# ---------------------------------------------------------------------------
# Overlap threshold boundary (PRD §6.1 rule 3)
# ---------------------------------------------------------------------------


def test_column_grouping_at_threshold() -> None:
    """Exactly 50% horizontal overlap → same column; just below 50% → separate columns."""
    a = _make_dialogue(x=0, y=0, width=100, height=50, did="a")

    # overlap = 50, min_w = 100 → 0.50 → merged
    b_at = _make_dialogue(x=50, y=60, width=100, height=50, did="b_at")
    cols_at = _group_into_columns([a, b_at], overlap_threshold=0.50)
    assert len(cols_at) == 1

    # overlap = 49, min_w = 100 → 0.49 → separate
    b_below = _make_dialogue(x=51, y=60, width=100, height=50, did="b_below")
    cols_below = _group_into_columns([a, b_below], overlap_threshold=0.50)
    assert len(cols_below) == 2


# ---------------------------------------------------------------------------
# Dialogues outside tier boundaries (PRD §6.1 — unordered fallback)
# ---------------------------------------------------------------------------


def test_dialogues_outside_tier_boundaries_appended() -> None:
    """Blocks whose centre-y falls outside all tier ranges are appended at the end."""
    in_tier = _make_dialogue(x=600, y=10, width=80, height=50, did="in_tier")
    # centre_y = 1025 — falls beyond page_height=900
    out_of_range = _make_dialogue(x=600, y=1000, width=80, height=50, did="out_of_range")

    strategy = TieredColumnRtlStrategy()
    ordered = strategy.order(
        [out_of_range, in_tier],
        page_width=750,
        page_height=900,
        panel_divisa_ys=[548],
    )

    ids = [d.id for d in ordered]
    assert ids == ["in_tier", "out_of_range"]
    assert ordered[0].order == 1
    assert ordered[1].order == 2
