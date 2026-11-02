"""DivisaStage: detect horizontal panel dividers → state.panels (F4-AG-04).

A "divisa" is a horizontal white/light band spanning ≥ DIVISA_MIN_WIDTH_RATIO of the
page width with average luminance ≥ DIVISA_LUMA_THRESHOLD.  Each detected divisa is
stored as a PanelRegion in state.panels so that ReadingOrderStage can split the page
into tiers.

The stage also detects "blocos largos" (wide text blocks > WIDE_BLOCK_RATIO of the
page width) from the existing dialogues and appends them to state.panels with a
``wide_block=True`` marker via a thin BBox so ReadingOrderStage can treat them as
sub-tier boundaries.

Environment variable:
    DIVISA_MIN_WIDTH_RATIO   minimum fraction of page width a white band must span
                             to be considered a divisa  (default: 0.80)
    DIVISA_LUMA_THRESHOLD    minimum per-pixel mean luminance [0–255] of the band
                             (default: 230)
    WIDE_BLOCK_RATIO         fraction of page width above which a text block is
                             treated as a sub-tier  (default: 0.60)
"""

from __future__ import annotations

import asyncio
import logging
import os

from agent.stage import Stage
from agent.state import BBox, PageAnalysisState, PanelRegion

logger = logging.getLogger(__name__)

_DIVISA_MIN_WIDTH_RATIO: float = float(os.environ.get("DIVISA_MIN_WIDTH_RATIO", "0.80"))
_DIVISA_LUMA_THRESHOLD: float = float(os.environ.get("DIVISA_LUMA_THRESHOLD", "230"))
_WIDE_BLOCK_RATIO: float = float(os.environ.get("WIDE_BLOCK_RATIO", "0.60"))

# Minimum height of a white band (in pixels) to be a divisa
_DIVISA_MIN_HEIGHT_PX: int = 3


def _detect_divisas_in_image(
    image_path: str,
    page_width: int,
    page_height: int,
    min_width_ratio: float = _DIVISA_MIN_WIDTH_RATIO,
    luma_threshold: float = _DIVISA_LUMA_THRESHOLD,
) -> list[int]:
    """Return sorted list of y-midpoints of horizontal white bands.

    Scans the image row by row; consecutive bright rows that span the required
    minimum width are collapsed into a single divisa y-midpoint.
    """
    try:
        import numpy as np  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415
    except ImportError:
        logger.warning("numpy/Pillow not available; skipping image-based divisa detection")
        return []

    img = Image.open(image_path).convert("L")  # grayscale
    arr = np.array(img, dtype=np.float32)

    h, w = arr.shape
    min_w = int(w * min_width_ratio)

    divisas: list[int] = []
    band_start: int | None = None

    for row_y in range(h):
        row = arr[row_y, :]
        bright_count = int(np.sum(row >= luma_threshold))
        is_divisa_row = bright_count >= min_w

        if is_divisa_row:
            if band_start is None:
                band_start = row_y
        else:
            if band_start is not None:
                band_end = row_y - 1
                if (band_end - band_start + 1) >= _DIVISA_MIN_HEIGHT_PX:
                    divisas.append((band_start + band_end) // 2)
                band_start = None

    if band_start is not None:
        band_end = h - 1
        if (band_end - band_start + 1) >= _DIVISA_MIN_HEIGHT_PX:
            divisas.append((band_start + band_end) // 2)

    logger.debug(
        "divisa_stage: image=%s detected %d divisa(s) at y=%s",
        image_path,
        len(divisas),
        divisas,
    )
    return divisas


def _detect_wide_blocks(
    state: PageAnalysisState,
    wide_block_ratio: float = _WIDE_BLOCK_RATIO,
) -> list[int]:
    """Return sorted list of y-midpoints of wide text blocks (sub-tier boundaries)."""
    if not state.page_width:
        return []

    threshold = state.page_width * wide_block_ratio
    midpoints: list[int] = []

    for d in state.dialogues:
        if d.bbox.width >= threshold:
            mid_y = d.bbox.y + d.bbox.height // 2
            midpoints.append(mid_y)
            logger.debug(
                "divisa_stage: wide block id=%s width=%d (threshold=%.0f) y_mid=%d",
                d.id,
                d.bbox.width,
                threshold,
                mid_y,
            )

    return sorted(midpoints)


def _detect(state: PageAnalysisState) -> list[int]:
    """Combine image-based divisa detection and bbox-based wide-block detection."""
    if not state.page_width or not state.page_height:
        return []

    image_ys = _detect_divisas_in_image(
        state.image_path,
        state.page_width,
        state.page_height,
    )
    wide_ys = _detect_wide_blocks(state)

    # Merge and deduplicate (within 10 px tolerance)
    all_ys = sorted(set(image_ys + wide_ys))
    merged: list[int] = []
    for y in all_ys:
        if merged and abs(y - merged[-1]) < 10:
            merged[-1] = (merged[-1] + y) // 2  # average nearby divisas
        else:
            merged.append(y)

    return merged


class DivisaStage(Stage):
    """Detect horizontal panel divisas and wide text blocks; populate state.panels.

    Must run after PreprocessStage (needs state.page_width/page_height and the
    preprocessed image) and after MergeBlocksStage (wide-block detection uses
    the final dialogue list).

    Each detected divisa is appended as a thin PanelRegion spanning the full
    page width at the divisa's y-midpoint.
    """

    @property
    def name(self) -> str:
        return "divisa"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        loop = asyncio.get_event_loop()
        divisa_ys = await loop.run_in_executor(None, _detect, state)

        page_w = state.page_width or 0
        for y in divisa_ys:
            state.panels.append(PanelRegion(bbox=BBox(x=0, y=y, width=page_w, height=1)))

        logger.debug("divisa_stage: page_id=%s found %d divisa(s)", state.page_id, len(divisa_ys))
        return state
