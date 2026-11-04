"""ReadingOrderStage: assign dialogue order using ReadingOrderStrategy (F4-AG-01).

Three strategies are provided (PRD §6.1):

    tiered_column_rtl  (default/MVP)
        1. Divide page into horizontal tiers using divisa y-coords from
           state.panels.  If state.panels is empty, the whole page is one tier.
        2. Within each tier, split further on "wide blocks" (width > 60% of
           page width) which act as sub-tier boundaries.
        3. In each sub-tier, group dialogues into columns: two blocks share a
           column when their horizontal overlap ≥ 50% of the smaller block's
           width.
        4. Sort columns by their rightmost x (right edge), descending.
        5. Within each column, sort by top-y, ascending.
        6. Tiebreak: centre-x descending, then centre-y ascending.
        7. Concatenate all sub-tiers top-to-bottom; assign order 1..N.

    column_rtl  (literal / comparison baseline)
        Same as steps 3–6 above, treating the whole page as one tier.

    panel_aware  (V2-AG-03)
        1. Use full panel bounding boxes from state.panels.
        2. Group panels into horizontal rows: two panels share a row when their
           vertical overlap ≥ 30% of the smaller panel's height.
        3. Sort rows top-to-bottom; within each row sort panels right-to-left
           (manga RTL) by right edge descending.
        4. Assign each dialogue to the panel containing its centre point.
        5. Apply column_rtl ordering within each panel.
        6. Dialogues outside all panels are appended after the last panel.
        Falls back to tiered_column_rtl when state.panels is empty.

Both strategies set ``dialogue.order`` in-place and return the sorted list.

Environment variable:
    READING_ORDER_STRATEGY   "tiered_column_rtl" | "column_rtl" | "panel_aware"
                             (default: "tiered_column_rtl")
    COLUMN_OVERLAP_THRESHOLD fraction [0-1] of smaller block width that must
                             overlap horizontally for two blocks to share a
                             column  (default: 0.50)
    WIDE_BLOCK_RATIO         same as in DivisaStage; used here for sub-tier
                             detection within tiered_column_rtl  (default: 0.60)
    PANEL_ROW_OVERLAP_RATIO  fraction [0-1] of smaller panel height for two
                             panels to be considered in the same row
                             (default: 0.30, panel_aware only)
"""

from __future__ import annotations

import logging
import os
from typing import Protocol, runtime_checkable

from agent.stage import Stage
from agent.state import DialogueState, PageAnalysisState, PanelRegion

logger = logging.getLogger(__name__)

_DEFAULT_STRATEGY = os.environ.get("READING_ORDER_STRATEGY", "tiered_column_rtl")
_COLUMN_OVERLAP_THRESHOLD: float = float(os.environ.get("COLUMN_OVERLAP_THRESHOLD", "0.50"))
_WIDE_BLOCK_RATIO: float = float(os.environ.get("WIDE_BLOCK_RATIO", "0.60"))
_PANEL_ROW_OVERLAP_RATIO: float = float(os.environ.get("PANEL_ROW_OVERLAP_RATIO", "0.30"))


# ---------------------------------------------------------------------------
# Strategy protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ReadingOrderStrategy(Protocol):
    """Assign ``order`` to each dialogue and return them sorted 1..N."""

    def order(
        self,
        dialogues: list[DialogueState],
        page_width: int,
        page_height: int,
        panel_divisa_ys: list[int],
        panels: list[PanelRegion] | None = None,
    ) -> list[DialogueState]:
        """Return dialogues sorted by reading order with .order set to 1..N."""
        ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _h_overlap_ratio(a: DialogueState, b: DialogueState) -> float:
    """Horizontal overlap as a fraction of the smaller block's width."""
    ax1, ax2 = a.bbox.x, a.bbox.x + a.bbox.width
    bx1, bx2 = b.bbox.x, b.bbox.x + b.bbox.width
    overlap = max(0, min(ax2, bx2) - max(ax1, bx1))
    min_w = min(a.bbox.width, b.bbox.width)
    return overlap / min_w if min_w > 0 else 0.0


def _sort_key(d: DialogueState) -> tuple[float, float, float]:
    """Primary sort key within a column: (top_y asc, centre_x desc, centre_y asc)."""
    cx = -(d.bbox.x + d.bbox.width / 2)
    cy = d.bbox.y + d.bbox.height / 2
    return (float(d.bbox.y), cx, cy)


def _right_edge(group: list[DialogueState]) -> int:
    return max(d.bbox.x + d.bbox.width for d in group)


def _group_into_columns(
    dialogues: list[DialogueState],
    overlap_threshold: float = _COLUMN_OVERLAP_THRESHOLD,
) -> list[list[DialogueState]]:
    """Group dialogues into columns using greedy union-find."""
    if not dialogues:
        return []

    # Each dialogue starts in its own column
    columns: list[list[DialogueState]] = [[d] for d in dialogues]

    changed = True
    while changed:
        changed = False
        merged: list[list[DialogueState]] = []
        used = [False] * len(columns)

        for i in range(len(columns)):
            if used[i]:
                continue
            col = list(columns[i])
            for j in range(i + 1, len(columns)):
                if used[j]:
                    continue
                # Two columns merge if any pair of their members share a column
                should_merge = any(
                    _h_overlap_ratio(a, b) >= overlap_threshold for a in col for b in columns[j]
                )
                if should_merge:
                    col.extend(columns[j])
                    used[j] = True
                    changed = True
            merged.append(col)
            used[i] = True

        columns = merged

    return columns


def _order_within_tier(
    tier_dialogues: list[DialogueState],
    start_order: int,
    overlap_threshold: float = _COLUMN_OVERLAP_THRESHOLD,
) -> int:
    """Assign order to dialogues within a tier; return next available order number."""
    if not tier_dialogues:
        return start_order

    columns = _group_into_columns(tier_dialogues, overlap_threshold)
    # Sort columns by right edge, descending
    columns.sort(key=_right_edge, reverse=True)

    order = start_order
    for col in columns:
        col.sort(key=_sort_key)
        for d in col:
            d.order = order
            order += 1

    return order


def _split_at_wide_blocks(
    tier_dialogues: list[DialogueState],
    page_width: int,
    wide_block_ratio: float = _WIDE_BLOCK_RATIO,
) -> list[list[DialogueState]]:
    """Split tier into sub-tiers at wide blocks.

    A dialogue whose width > wide_block_ratio * page_width acts as a sub-tier
    boundary.  Wide blocks occupy their own single-element sub-tier between the
    blocks above and below them.
    """
    if not page_width:
        return [tier_dialogues]

    threshold = page_width * wide_block_ratio
    # Sort by top y so we process top-to-bottom
    sorted_ds = sorted(tier_dialogues, key=lambda d: d.bbox.y)

    sub_tiers: list[list[DialogueState]] = []
    current: list[DialogueState] = []

    for d in sorted_ds:
        if d.bbox.width >= threshold:
            if current:
                sub_tiers.append(current)
                current = []
            sub_tiers.append([d])  # wide block is its own sub-tier
        else:
            current.append(d)

    if current:
        sub_tiers.append(current)

    return sub_tiers if sub_tiers else [tier_dialogues]


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------


class ColumnRtlStrategy:
    """column_rtl: literal right-to-left column ordering, no tier detection."""

    def order(
        self,
        dialogues: list[DialogueState],
        page_width: int,
        page_height: int,
        panel_divisa_ys: list[int],
        panels: list[PanelRegion] | None = None,
    ) -> list[DialogueState]:
        _order_within_tier(dialogues, start_order=1)
        return sorted(dialogues, key=lambda d: d.order or 0)


class TieredColumnRtlStrategy:
    """tiered_column_rtl: split into tiers (divisas + wide blocks), then column_rtl."""

    def order(
        self,
        dialogues: list[DialogueState],
        page_width: int,
        page_height: int,
        panel_divisa_ys: list[int],
        panels: list[PanelRegion] | None = None,
    ) -> list[DialogueState]:
        if not dialogues:
            return []

        # Build tier y-boundaries from divisa_ys
        sorted_ys = sorted(panel_divisa_ys)
        boundaries = [0] + sorted_ys + [page_height or 999_999]

        current_order = 1
        all_ordered: list[DialogueState] = []

        for tier_idx in range(len(boundaries) - 1):
            y_start = boundaries[tier_idx]
            y_end = boundaries[tier_idx + 1]

            # Assign dialogue to tier by its centre y
            tier_dialogues = [
                d for d in dialogues if y_start <= (d.bbox.y + d.bbox.height // 2) < y_end
            ]

            # Split tier further at wide blocks (sub-tier boundaries)
            sub_tiers = _split_at_wide_blocks(tier_dialogues, page_width)

            for sub_tier in sub_tiers:
                current_order = _order_within_tier(sub_tier, current_order)
                all_ordered.extend(sub_tier)

        # Handle any dialogues that fell outside tier boundaries (edge case)
        unordered = [d for d in dialogues if d.order is None]
        if unordered:
            current_order = _order_within_tier(unordered, current_order)
            all_ordered.extend(unordered)

        return sorted(all_ordered, key=lambda d: d.order or 0)


class PanelAwareStrategy:
    """panel_aware (V2-AG-03): sort panels top→bottom / right→left, column_rtl inside each."""

    def __init__(self, row_overlap_ratio: float = _PANEL_ROW_OVERLAP_RATIO) -> None:
        self._row_overlap_ratio = row_overlap_ratio

    def order(
        self,
        dialogues: list[DialogueState],
        page_width: int,
        page_height: int,
        panel_divisa_ys: list[int],
        panels: list[PanelRegion] | None = None,
    ) -> list[DialogueState]:
        if not dialogues:
            return []
        if not panels:
            return TieredColumnRtlStrategy().order(
                dialogues, page_width, page_height, panel_divisa_ys
            )

        # Assign each dialogue to the panel containing its centre point
        panel_groups: dict[int, list[DialogueState]] = {i: [] for i in range(len(panels))}
        unassigned: list[DialogueState] = []

        for d in dialogues:
            cx = d.bbox.x + d.bbox.width // 2
            cy = d.bbox.y + d.bbox.height // 2
            idx = self._find_panel(cx, cy, panels)
            if idx >= 0:
                panel_groups[idx].append(d)
            else:
                unassigned.append(d)

        # Determine manga reading order across panels
        sorted_panel_indices = self._sort_panels_manga(panels)

        current_order = 1
        all_ordered: list[DialogueState] = []

        for panel_idx in sorted_panel_indices:
            group = panel_groups[panel_idx]
            if group:
                current_order = _order_within_tier(group, current_order)
                all_ordered.extend(group)

        if unassigned:
            current_order = _order_within_tier(unassigned, current_order)
            all_ordered.extend(unassigned)

        return sorted(all_ordered, key=lambda d: d.order or 0)

    @staticmethod
    def _find_panel(cx: int, cy: int, panels: list[PanelRegion]) -> int:
        """Return index of first panel whose bbox contains (cx, cy), or -1."""
        for i, p in enumerate(panels):
            bx1 = p.bbox.x
            by1 = p.bbox.y
            bx2 = bx1 + p.bbox.width
            by2 = by1 + p.bbox.height
            if bx1 <= cx < bx2 and by1 <= cy < by2:
                return i
        return -1

    def _sort_panels_manga(self, panels: list[PanelRegion]) -> list[int]:
        """Return panel indices in manga reading order: rows top→bottom, within row right→left."""
        if not panels:
            return []

        rows: list[list[int]] = []
        for i in range(len(panels)):
            placed = False
            for row in rows:
                if any(
                    self._v_overlap_ratio(panels[i], panels[j]) >= self._row_overlap_ratio
                    for j in row
                ):
                    row.append(i)
                    placed = True
                    break
            if not placed:
                rows.append([i])

        # Sort rows by topmost y of any panel in the row
        rows.sort(key=lambda row: min(panels[j].bbox.y for j in row))

        # Within each row, sort panels by right edge descending (RTL)
        result: list[int] = []
        for row in rows:
            row.sort(key=lambda j: panels[j].bbox.x + panels[j].bbox.width, reverse=True)
            result.extend(row)

        return result

    @staticmethod
    def _v_overlap_ratio(a: PanelRegion, b: PanelRegion) -> float:
        """Vertical overlap as fraction of the smaller panel's height."""
        ay1, ay2 = a.bbox.y, a.bbox.y + a.bbox.height
        by1, by2 = b.bbox.y, b.bbox.y + b.bbox.height
        overlap = max(0, min(ay2, by2) - max(ay1, by1))
        min_h = min(a.bbox.height, b.bbox.height)
        return overlap / min_h if min_h > 0 else 0.0


# ---------------------------------------------------------------------------
# Stage
# ---------------------------------------------------------------------------


class ReadingOrderStage(Stage):
    """Apply a ReadingOrderStrategy to assign order 1..N to each dialogue.

    Must run after DivisaStage (or at least after MergeBlocksStage so the
    dialogue list is final).
    """

    def __init__(
        self,
        strategy: ReadingOrderStrategy | None = None,
    ) -> None:
        if strategy is None:
            if _DEFAULT_STRATEGY == "panel_aware":
                strategy = PanelAwareStrategy()
            elif _DEFAULT_STRATEGY == "tiered_column_rtl":
                strategy = TieredColumnRtlStrategy()
            else:
                strategy = ColumnRtlStrategy()
        self._strategy = strategy

    @property
    def name(self) -> str:
        return "reading_order"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        if not state.dialogues:
            return state

        page_width = state.page_width or 0
        page_height = state.page_height or 0
        panel_divisa_ys = [p.bbox.y for p in state.panels]

        # Reset order before applying strategy
        for d in state.dialogues:
            d.order = None

        ordered = self._strategy.order(
            state.dialogues, page_width, page_height, panel_divisa_ys, state.panels
        )
        state.dialogues = ordered

        logger.debug(
            "reading_order: page_id=%s strategy=%s ordered %d dialogues",
            state.page_id,
            type(self._strategy).__name__,
            len(ordered),
        )
        return state
