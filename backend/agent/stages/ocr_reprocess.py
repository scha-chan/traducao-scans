"""OcrReprocessStage: re-runs OCR with image enhancement for low-confidence blocks (V2-AG-04).

Identifies dialogues flagged with review_reason="low_ocr_confidence" and applies
PIL-based contrast/binarization preprocessing before retrying OCR.  When the
re-processed confidence is higher than the original the new result is kept; otherwise
the original result is preserved.  Blocks whose confidence exceeds the threshold after
reprocessing have their needs_review flag cleared.

Must run after LowConfidenceStage (requires needs_review / review_reason) and
before TranslationStage (updates original text used as translation input).
"""

from __future__ import annotations

import asyncio
import logging

from PIL import Image, ImageEnhance, ImageFilter

from agent.providers.ocr import OcrProvider
from agent.stage import Stage
from agent.state import PageAnalysisState

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 0.80


def _enhance_region(region: Image.Image) -> Image.Image:
    """Apply contrast + binarisation to a region to improve manga OCR accuracy."""
    gray = region.convert("L")

    # Increase contrast so ink strokes stand out against background
    gray = ImageEnhance.Contrast(gray).enhance(2.0)

    # Sharpen edges to help the OCR model
    gray = gray.filter(ImageFilter.SHARPEN)

    # Simple threshold: pixels below mid-gray → 0 (black), above → 255 (white)
    threshold = 128
    binarised = gray.point(lambda p: 0 if p < threshold else 255)

    return binarised.convert("RGB")


class OcrReprocessStage(Stage):
    """Re-runs OCR with image enhancement on low-confidence blocks.

    Configuration:
        threshold    Confidence below which a block is considered low-quality.
                     Defaults to 0.80 (same as LowConfidenceStage).  Blocks that
                     reach this threshold after reprocessing have needs_review
                     cleared (review_reason preserved to signal they were
                     reprocessed).
    """

    def __init__(
        self,
        provider: OcrProvider,
        threshold: float = _DEFAULT_THRESHOLD,
    ) -> None:
        self._provider = provider
        self._threshold = threshold

    @property
    def name(self) -> str:
        return "ocr_reprocess"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        low_confidence = [
            d for d in state.dialogues if d.needs_review and d.review_reason == "low_ocr_confidence"
        ]

        if not low_confidence:
            return state

        loop = asyncio.get_event_loop()
        img = await loop.run_in_executor(None, Image.open, state.image_path)
        img_rgb = img.convert("RGB")

        improved = 0
        for dialogue in low_confidence:
            bbox = dialogue.bbox
            region = img_rgb.crop((bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height))
            enhanced = _enhance_region(region)
            result = await loop.run_in_executor(None, self._provider.ocr_region, enhanced, bbox)

            original_confidence = dialogue.ocr_confidence or 0.0
            if result.ocr_confidence > original_confidence:
                dialogue.original = result.original
                dialogue.lines = result.lines
                dialogue.ocr_confidence = result.ocr_confidence
                improved += 1

                if result.ocr_confidence >= self._threshold:
                    dialogue.needs_review = False

        logger.debug(
            "ocr_reprocess: page_id=%s reprocessed=%d improved=%d",
            state.page_id,
            len(low_confidence),
            improved,
        )
        return state
