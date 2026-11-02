"""MergeBlocksStage: furigana merging and continuous-column grouping (F3-AG-06).

PRD §9.1 (furigana/ruby) and §9.2 (block grouping).

Furigana detection heuristic (vertical text):
    A region is furigana of a parent when:
    - candidate.width ≤ FURIGANA_WIDTH_RATIO × parent.width
    - vertical Y-overlap ≥ FURIGANA_OVERLAP_RATIO × max(heights)
    - horizontal gap ≤ FURIGANA_GAP_PX (negative = overlapping)

Block-grouping heuristic:
    Two regions are merged into one block when:
    - vertical Y-overlap ≥ MERGE_OVERLAP_RATIO × max(heights)
    - horizontal gap ≤ MERGE_GAP_PX
"""

from __future__ import annotations

import logging

from agent.stage import Stage
from agent.state import BBox, DialogueState, PageAnalysisState, RubyPair

logger = logging.getLogger(__name__)

_FURIGANA_WIDTH_RATIO: float = 0.5
_FURIGANA_OVERLAP_RATIO: float = 0.5
_FURIGANA_GAP_PX: int = 8

_MERGE_OVERLAP_RATIO: float = 0.5
_MERGE_GAP_PX: int = 15


def _y_overlap_ratio(a: BBox, b: BBox) -> float:
    overlap = max(0, min(a.y + a.height, b.y + b.height) - max(a.y, b.y))
    return overlap / max(a.height, b.height, 1)


def _h_gap(a: BBox, b: BBox) -> int:
    """Horizontal gap between A and B; negative means they overlap in X."""
    return max(a.x, b.x) - min(a.x + a.width, b.x + b.width)


def _bbox_union(a: BBox, b: BBox) -> BBox:
    x1 = min(a.x, b.x)
    y1 = min(a.y, b.y)
    x2 = max(a.x + a.width, b.x + b.width)
    y2 = max(a.y + a.height, b.y + b.height)
    return BBox(x=x1, y=y1, width=x2 - x1, height=y2 - y1)


def _merge_into(parent: DialogueState, child: DialogueState) -> None:
    """Merge child into parent in-place, combining lines, bbox and metadata."""
    child_lines = child.lines if child.lines else ([child.original] if child.original else [])
    parent_lines = parent.lines if parent.lines else ([parent.original] if parent.original else [])
    parent.lines = parent_lines + child_lines
    parent.original = "\n".join(ln for ln in parent.lines if ln) or parent.original
    parent.bbox = _bbox_union(parent.bbox, child.bbox)
    parent.ruby.extend(child.ruby)
    if child.needs_review:
        parent.needs_review = True
        if not parent.review_reason:
            parent.review_reason = child.review_reason
    if child.ocr_confidence is not None:
        parent.ocr_confidence = (
            min(parent.ocr_confidence, child.ocr_confidence)
            if parent.ocr_confidence is not None
            else child.ocr_confidence
        )


class MergeBlocksStage(Stage):
    """Funde regiões de furigana ao bloco-pai e agrupa colunas contínuas.

    Deve rodar após OcrStage (precisa de ``original`` e ``bbox`` preenchidos)
    e antes de LowConfidenceStage (que avalia ``ocr_confidence`` do bloco final).
    """

    def __init__(
        self,
        furigana_width_ratio: float = _FURIGANA_WIDTH_RATIO,
        furigana_overlap_ratio: float = _FURIGANA_OVERLAP_RATIO,
        furigana_gap_px: int = _FURIGANA_GAP_PX,
        merge_overlap_ratio: float = _MERGE_OVERLAP_RATIO,
        merge_gap_px: int = _MERGE_GAP_PX,
    ) -> None:
        self._fw_ratio = furigana_width_ratio
        self._fo_ratio = furigana_overlap_ratio
        self._fg_px = furigana_gap_px
        self._mo_ratio = merge_overlap_ratio
        self._mg_px = merge_gap_px

    @property
    def name(self) -> str:
        return "merge_blocks"

    def _is_furigana_of(self, cand: DialogueState, parent: DialogueState) -> bool:
        c, p = cand.bbox, parent.bbox
        if c.width > self._fw_ratio * p.width:
            return False
        if _y_overlap_ratio(c, p) < self._fo_ratio:
            return False
        return _h_gap(c, p) <= self._fg_px

    def _should_merge(self, a: DialogueState, b: DialogueState) -> bool:
        if _y_overlap_ratio(a.bbox, b.bbox) < self._mo_ratio:
            return False
        return _h_gap(a.bbox, b.bbox) <= self._mg_px

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        dialogues = list(state.dialogues)

        # ── Step 1: absorb furigana regions ─────────────────────────────────
        furigana_ids: set[str] = set()

        for parent in dialogues:
            for cand in dialogues:
                if parent.id == cand.id or cand.id in furigana_ids:
                    continue
                if self._is_furigana_of(cand, parent):
                    reading = cand.original or ""
                    if reading:
                        parent.ruby.append(RubyPair(base="", reading=reading))
                    furigana_ids.add(cand.id)
                    logger.debug(
                        "merge_blocks: furigana %s → parent %s (reading=%r)",
                        cand.id,
                        parent.id,
                        reading,
                    )

        dialogues = [d for d in dialogues if d.id not in furigana_ids]

        # ── Step 2: group continuous columns ─────────────────────────────────
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(dialogues):
                j = i + 1
                while j < len(dialogues):
                    if self._should_merge(dialogues[i], dialogues[j]):
                        child = dialogues.pop(j)
                        _merge_into(dialogues[i], child)
                        logger.debug(
                            "merge_blocks: column %s merged into %s",
                            child.id,
                            dialogues[i].id,
                        )
                        changed = True
                    else:
                        j += 1
                i += 1

        state.dialogues = dialogues
        return state
