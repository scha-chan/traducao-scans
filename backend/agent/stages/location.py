"""LocationStage: assign location string to each dialogue region (F4-AG-03 / board).

PRD §8 and §8.1 — hybrid location generation.

Runs after ClassificationStage (or at minimum after DivisaStage so that
state.panels is populated with divisa y-coordinates).

Algorithm (§8.1 hybrid generation):
1. Deterministic base: 3×3 grid (Topo/Centro/Inferior × esquerda/centro/direita)
   using the bbox centre, computed relative to the panel section that contains
   the block.  Divisas in state.panels split the page into sections.
   - Size suffix "(grande)" when block area ≥ LOCATION_LARGE_RATIO × section area.
   - Size suffix "(pequeno)" when block area ≤ LOCATION_SMALL_RATIO × section area.
2. Optional LLM refinement: if the injected LocationProvider returns a non-empty
   string, that string replaces the deterministic base.  Falls back to the base
   when the provider returns '' or raises.

Environment variables:
    LOCATION_LARGE_RATIO  bbox/section area ratio ≥ this → "(grande)"  (default 0.08)
    LOCATION_SMALL_RATIO  bbox/section area ratio ≤ this → "(pequeno)" (default 0.005)
"""

from __future__ import annotations

import logging
import os

from agent.providers.location import LocationProvider, StubLocationProvider
from agent.stage import Stage
from agent.state import BBox, DialogueState, PageAnalysisState  # noqa: F401

logger = logging.getLogger(__name__)

_LARGE_RATIO: float = float(os.environ.get("LOCATION_LARGE_RATIO", "0.08"))
_SMALL_RATIO: float = float(os.environ.get("LOCATION_SMALL_RATIO", "0.005"))

_ROW_LABELS = ("Topo", "Centro", "Inferior")
_COL_LABELS = ("esquerda", "centro", "direita")


def _grid_idx(fraction: float) -> int:
    """Map a [0, 1] fraction to a 0/1/2 grid index (equal thirds)."""
    if fraction < 1 / 3:
        return 0
    if fraction < 2 / 3:
        return 1
    return 2


def _build_location_string(
    bbox: BBox,
    section_y_start: int,
    section_y_end: int,
    page_width: int,
    section_idx: int,
    total_sections: int,
    large_ratio: float = _LARGE_RATIO,
    small_ratio: float = _SMALL_RATIO,
) -> str:
    """Compute the deterministic location label for a bbox within a page section."""
    cx = bbox.x + bbox.width / 2
    cy = bbox.y + bbox.height / 2

    section_h = section_y_end - section_y_start
    x_frac = cx / page_width if page_width else 0.0
    y_frac = (cy - section_y_start) / section_h if section_h else 0.0
    y_frac = max(0.0, min(1.0, y_frac))

    row = _ROW_LABELS[_grid_idx(y_frac)]
    col = _COL_LABELS[_grid_idx(x_frac)]

    # Position label — centre column is omitted when redundant
    if row == "Centro" and col == "centro":
        position = "Centro"
    elif col == "centro":
        position = row
    else:
        position = f"{row} {col}"

    # Panel qualifier for sections after the first
    if total_sections > 1 and section_idx > 0:
        qualifier = (
            "do painel inferior"
            if section_idx == total_sections - 1
            else f"do painel {section_idx + 1}"
        )
        position = f"{position} {qualifier}"

    # Size suffix
    block_area = bbox.width * bbox.height
    section_area = page_width * section_h if page_width and section_h else 0
    if section_area > 0:
        ratio = block_area / section_area
        if ratio >= large_ratio:
            position = f"{position} (grande)"
        elif ratio <= small_ratio:
            position = f"{position} (pequeno)"

    return position


class LocationStage(Stage):
    """Assign a human-readable location string to each dialogue region.

    The deterministic 3×3 grid always runs first.  If an optional
    LocationProvider is supplied and returns a non-empty string, that string
    replaces the deterministic base.
    """

    def __init__(
        self,
        provider: LocationProvider | None = None,
        large_ratio: float = _LARGE_RATIO,
        small_ratio: float = _SMALL_RATIO,
    ) -> None:
        self._provider: LocationProvider = (
            provider if provider is not None else StubLocationProvider()
        )
        self._large_ratio = large_ratio
        self._small_ratio = small_ratio

    @property
    def name(self) -> str:
        return "location"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        if not state.dialogues:
            return state

        page_width = state.page_width or 0
        page_height = state.page_height or 0

        divisa_ys = sorted(p.bbox.y for p in state.panels)
        boundaries = [0] + divisa_ys + [page_height]
        sections = [(boundaries[i], boundaries[i + 1]) for i in range(len(boundaries) - 1)]
        total_sections = len(sections)

        for dialogue in state.dialogues:
            cy = dialogue.bbox.y + dialogue.bbox.height / 2

            section_idx = total_sections - 1
            for i, (y_start, y_end) in enumerate(sections):
                if y_start <= cy < y_end:
                    section_idx = i
                    break

            y_start, y_end = sections[section_idx]
            base = _build_location_string(
                dialogue.bbox,
                y_start,
                y_end,
                page_width,
                section_idx,
                total_sections,
                self._large_ratio,
                self._small_ratio,
            )

            try:
                refined = self._provider.refine(base, dialogue.bbox)
                location = refined if refined else base
            except Exception:
                location = base

            dialogue.location = location
            logger.debug("location: id=%s base=%r location=%r", dialogue.id, base, location)

        return state
