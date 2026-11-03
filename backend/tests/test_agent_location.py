"""Tests for LocationStage (F4-AG-03 / board, F4-AG-04 in PRD §8.1)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent.stages.location import LocationStage, _build_location_string
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


# ---------------------------------------------------------------------------
# Unit: _build_location_string — single section (no divisa)
# ---------------------------------------------------------------------------


def test_topo_direita_single_section() -> None:
    bbox = BBox(x=540, y=60, width=100, height=100)
    assert _build_location_string(bbox, 0, 1200, 750, 0, 1) == "Topo direita"


def test_inferior_esquerda_single_section() -> None:
    bbox = BBox(x=50, y=900, width=100, height=100)
    assert _build_location_string(bbox, 0, 1200, 750, 0, 1) == "Inferior esquerda"


def test_centro_when_both_center() -> None:
    bbox = BBox(x=300, y=500, width=100, height=100)
    assert _build_location_string(bbox, 0, 1200, 750, 0, 1) == "Centro"


def test_center_column_omitted_when_row_is_topo() -> None:
    bbox = BBox(x=300, y=50, width=100, height=50)
    assert _build_location_string(bbox, 0, 1200, 750, 0, 1) == "Topo"


def test_center_column_omitted_when_row_is_inferior() -> None:
    bbox = BBox(x=300, y=1000, width=100, height=50)
    assert _build_location_string(bbox, 0, 1200, 750, 0, 1) == "Inferior"


# ---------------------------------------------------------------------------
# Unit: size suffixes
# ---------------------------------------------------------------------------


def test_grande_suffix_when_above_threshold() -> None:
    # area=300×200=60000; section_area=750×1200=900000; ratio≈0.067; threshold=0.06
    bbox = BBox(x=200, y=400, width=300, height=200)
    label = _build_location_string(bbox, 0, 1200, 750, 0, 1, large_ratio=0.06)
    assert "(grande)" in label


def test_pequeno_suffix_when_below_threshold() -> None:
    bbox = BBox(x=200, y=400, width=10, height=10)
    label = _build_location_string(bbox, 0, 1200, 750, 0, 1)
    assert "(pequeno)" in label


def test_no_suffix_in_normal_range() -> None:
    bbox = BBox(x=200, y=400, width=100, height=100)
    label = _build_location_string(bbox, 0, 1200, 750, 0, 1)
    assert "(grande)" not in label
    assert "(pequeno)" not in label


# ---------------------------------------------------------------------------
# Unit: panel qualifier
# ---------------------------------------------------------------------------


def test_no_qualifier_for_first_section_in_two_section_page() -> None:
    bbox = BBox(x=300, y=200, width=100, height=100)
    label = _build_location_string(bbox, 0, 548, 750, section_idx=0, total_sections=2)
    assert "painel" not in label


def test_painel_inferior_qualifier_for_last_section() -> None:
    bbox = BBox(x=300, y=700, width=100, height=100)
    label = _build_location_string(bbox, 548, 1200, 750, section_idx=1, total_sections=2)
    assert "do painel inferior" in label


def test_middle_section_uses_numeric_qualifier() -> None:
    bbox = BBox(x=300, y=500, width=100, height=100)
    label = _build_location_string(bbox, 400, 800, 750, section_idx=1, total_sections=3)
    assert "do painel 2" in label


def test_last_of_three_sections_gets_inferior() -> None:
    bbox = BBox(x=300, y=900, width=100, height=100)
    label = _build_location_string(bbox, 800, 1200, 750, section_idx=2, total_sections=3)
    assert "do painel inferior" in label


# ---------------------------------------------------------------------------
# Acceptance: pagina_01 reference (PRD §8.1 / F4-AG-04)
# ---------------------------------------------------------------------------


def test_pagina01_b1_topo_direita() -> None:
    """Block 1: bbox (590, 110, 50, 125) — upper panel, page 750×1200, divisa at 548."""
    bbox = BBox(x=590, y=110, width=50, height=125)
    label = _build_location_string(bbox, 0, 548, 750, section_idx=0, total_sections=2)
    assert label == "Topo direita"


def test_pagina01_b9_centro_painel_inferior_grande() -> None:
    """Block 9: bbox (375, 590, 95, 425) — lower panel, page 750×1200, divisa at 548."""
    bbox = BBox(x=375, y=590, width=95, height=425)
    label = _build_location_string(bbox, 548, 1200, 750, section_idx=1, total_sections=2)
    assert label == "Centro do painel inferior (grande)"


# ---------------------------------------------------------------------------
# Stage integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage_assigns_location_to_all_dialogues() -> None:
    dialogues = [
        _make_dialogue(x=500, y=100, width=100, height=50, did="a"),
        _make_dialogue(x=200, y=100, width=100, height=50, did="b"),
    ]
    state = _make_state(dialogues)
    result = await LocationStage().run(state)
    assert all(d.location is not None for d in result.dialogues)


@pytest.mark.asyncio
async def test_stage_noop_on_empty_dialogues() -> None:
    state = _make_state([])
    result = await LocationStage().run(state)
    assert result.dialogues == []


@pytest.mark.asyncio
async def test_stage_uses_divisa_to_assign_panel_qualifier() -> None:
    d = _make_dialogue(x=300, y=700, width=100, height=100, did="lower")
    panels = [PanelRegion(bbox=BBox(x=0, y=548, width=750, height=1))]
    state = _make_state([d], panels=panels)
    result = await LocationStage().run(state)
    assert result.dialogues[0].location is not None
    assert "do painel inferior" in result.dialogues[0].location


@pytest.mark.asyncio
async def test_stage_pagina01_full_acceptance() -> None:
    """pagina_01 full acceptance: b1 → 'Topo direita', b9 → 'Centro do painel inferior (grande)'."""
    b1 = _make_dialogue(x=590, y=110, width=50, height=125, did="b1")
    b9 = _make_dialogue(x=375, y=590, width=95, height=425, did="b9")
    panels = [PanelRegion(bbox=BBox(x=0, y=548, width=750, height=1))]
    state = _make_state([b1, b9], panels=panels)

    result = await LocationStage().run(state)
    loc = {d.id: d.location for d in result.dialogues}

    assert loc["b1"] == "Topo direita"
    assert loc["b9"] == "Centro do painel inferior (grande)"


@pytest.mark.asyncio
async def test_stage_llm_refinement_overrides_base() -> None:
    from agent.providers.location import LocationProvider
    from agent.state import BBox as _BBox

    class OverrideProvider:
        def refine(self, base_location: str, bbox: _BBox) -> str:
            return "Dentro do logo (direita)"

    assert isinstance(OverrideProvider(), LocationProvider)

    d = _make_dialogue(x=300, y=200, width=100, height=50)
    state = _make_state([d])
    result = await LocationStage(provider=OverrideProvider()).run(state)
    assert result.dialogues[0].location == "Dentro do logo (direita)"


@pytest.mark.asyncio
async def test_stage_llm_fallback_on_empty_refinement() -> None:
    from agent.providers.location import StubLocationProvider

    d = _make_dialogue(x=550, y=80, width=100, height=80)
    state = _make_state([d])
    result = await LocationStage(provider=StubLocationProvider()).run(state)
    assert result.dialogues[0].location is not None
    assert result.dialogues[0].location != ""
