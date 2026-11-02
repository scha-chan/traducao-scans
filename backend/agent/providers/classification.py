"""ClassificationProvider: classify text regions as speech-bubble (#) or non-bubble ($).

PRD §7 and §17.3.

Two providers are included:

  HeuristicClassificationProvider  (default, no ML dependencies)
      Crops an expanded region around each bbox and analyses pixel luminance
      to detect the bright interior + dark border pattern of a speech bubble.

      Algorithm:
        1. Expand the bbox by PADDING pixels on each side.
        2. Compute mean luminance of the interior (original bbox).
        3. Compute mean luminance of the annular ring (expanded − interior).
        4. Compute white-pixel ratio inside the interior (luma ≥ WHITE_THRESHOLD).
        5. If white_ratio ≥ WHITE_RATIO_MIN and interior_luma − annulus_luma ≥ CONTRAST_MIN
           → type = "#" with confidence proportional to the contrast gap.
           Otherwise → type = "$".

  LlmClassificationProvider  (optional, requires Claude API key)
      Sends the expanded crop as base64 image to the LLM with a structured
      prompt.  Used as a drop-in replacement when the heuristic confidence
      falls below HEURISTIC_FALLBACK_THRESHOLD.  Designed for F5+ integration.

Environment variables:
    CLASSIFICATION_PADDING          expand bbox by this many pixels (default: 20)
    CLASSIFICATION_WHITE_THRESHOLD  luma value above which a pixel counts as
                                    "white" (default: 200)
    CLASSIFICATION_WHITE_RATIO_MIN  minimum fraction of interior pixels that must
                                    be white for a bubble candidate (default: 0.65)
    CLASSIFICATION_CONTRAST_MIN     minimum difference (interior_luma − annulus_luma)
                                    required to call a region a bubble (default: 30)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from PIL import Image

from agent.state import BBox

_PADDING: int = int(os.environ.get("CLASSIFICATION_PADDING", "20"))
_WHITE_THRESHOLD: int = int(os.environ.get("CLASSIFICATION_WHITE_THRESHOLD", "200"))
_WHITE_RATIO_MIN: float = float(os.environ.get("CLASSIFICATION_WHITE_RATIO_MIN", "0.65"))
_CONTRAST_MIN: float = float(os.environ.get("CLASSIFICATION_CONTRAST_MIN", "30"))


@dataclass
class ClassificationResult:
    type: Literal["#", "$"]
    confidence: float  # 0.0 – 1.0


@runtime_checkable
class ClassificationProvider(Protocol):
    """Contract for a speech-bubble classifier."""

    def classify(self, image: Image.Image, bbox: BBox) -> ClassificationResult:
        """Classify a text region as speech-bubble (#) or non-bubble ($)."""
        ...


class HeuristicClassificationProvider:
    """Luminance-based speech-bubble detector; no ML dependencies required.

    Works well for standard manga with white-interior bubbles and dark borders.
    Confidence reflects how strongly the evidence matches the bubble pattern.
    Handwritten, stylised, or very small regions may be misclassified.
    """

    def __init__(
        self,
        padding: int = _PADDING,
        white_threshold: int = _WHITE_THRESHOLD,
        white_ratio_min: float = _WHITE_RATIO_MIN,
        contrast_min: float = _CONTRAST_MIN,
    ) -> None:
        self._padding = padding
        self._white_threshold = white_threshold
        self._white_ratio_min = white_ratio_min
        self._contrast_min = contrast_min

    def classify(self, image: Image.Image, bbox: BBox) -> ClassificationResult:
        img_w, img_h = image.size
        pad = self._padding

        # ── Expanded bbox (clamped to image bounds) ──────────────────────────
        ex1 = max(0, bbox.x - pad)
        ey1 = max(0, bbox.y - pad)
        ex2 = min(img_w, bbox.x + bbox.width + pad)
        ey2 = min(img_h, bbox.y + bbox.height + pad)

        # ── Interior crop (original bbox) ────────────────────────────────────
        ix1 = max(0, bbox.x)
        iy1 = max(0, bbox.y)
        ix2 = min(img_w, bbox.x + bbox.width)
        iy2 = min(img_h, bbox.y + bbox.height)

        if ix2 <= ix1 or iy2 <= iy1:
            return ClassificationResult(type="$", confidence=0.5)

        interior_gray = image.crop((ix1, iy1, ix2, iy2)).convert("L")
        expanded_gray = image.crop((ex1, ey1, ex2, ey2)).convert("L")

        # Mean luminance of the interior
        interior_pixels = list(interior_gray.getdata())
        interior_luma = sum(interior_pixels) / len(interior_pixels) if interior_pixels else 0.0

        # White-pixel ratio inside the interior
        white_count = sum(1 for p in interior_pixels if p >= self._white_threshold)
        white_ratio = white_count / len(interior_pixels) if interior_pixels else 0.0

        # Mean luminance of the annular ring (expanded minus interior)
        expanded_pixels = list(expanded_gray.getdata())
        expanded_luma = sum(expanded_pixels) / len(expanded_pixels) if expanded_pixels else 0.0

        # Annulus luma: weighted by area difference
        exp_area = max(1, (ex2 - ex1) * (ey2 - ey1))
        int_area = max(1, (ix2 - ix1) * (iy2 - iy1))
        ann_area = exp_area - int_area

        if ann_area > 0:
            annulus_luma = (expanded_luma * exp_area - interior_luma * int_area) / ann_area
        else:
            annulus_luma = expanded_luma

        contrast = interior_luma - annulus_luma

        # ── Decision ─────────────────────────────────────────────────────────
        is_bubble = white_ratio >= self._white_ratio_min and contrast >= self._contrast_min

        if is_bubble:
            # Confidence: scale contrast gain and white ratio onto [0.5, 1.0]
            contrast_score = min(1.0, contrast / (self._contrast_min * 2))
            ratio_score = min(1.0, white_ratio / max(self._white_ratio_min, 0.01))
            confidence = 0.5 + 0.5 * (contrast_score * 0.6 + ratio_score * 0.4)
            return ClassificationResult(type="#", confidence=round(confidence, 3))
        else:
            # Confidence: how far from the bubble threshold
            ratio_gap = max(0.0, self._white_ratio_min - white_ratio) / max(
                self._white_ratio_min, 0.01
            )
            confidence = 0.5 + 0.5 * min(1.0, ratio_gap + max(0.0, -contrast) / 50)
            return ClassificationResult(type="$", confidence=round(min(confidence, 1.0), 3))
