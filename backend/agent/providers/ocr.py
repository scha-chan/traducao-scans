"""OcrProvider protocol and MangaOcrProvider (F3-AG-04).

Model: kha-white/manga-ocr-base (Hugging Face, ~400 MB, auto-downloaded on first use)
Install: pip install manga-ocr

Environment variable:
    MANGA_OCR_MODEL   HF model name or local path  (default: kha-white/manga-ocr-base)
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from PIL import Image

from agent.state import BBox


@dataclass
class OcrResult:
    original: str
    lines: list[str] = field(default_factory=list)
    orientation: Literal["VERTICAL", "HORIZONTAL"] = "VERTICAL"
    ocr_confidence: float = 1.0


@runtime_checkable
class OcrProvider(Protocol):
    """Contract for a per-region OCR provider."""

    def ocr_region(self, region: Image.Image, bbox: BBox) -> OcrResult:
        """Run OCR on an already-cropped image region."""
        ...


def _orientation_from_bbox(bbox: BBox) -> Literal["VERTICAL", "HORIZONTAL"]:
    """Heuristic: tall regions are vertical text, wide regions are horizontal."""
    if bbox.height > bbox.width * 1.2:
        return "VERTICAL"
    return "HORIZONTAL"


class MangaOcrProvider:
    """OCR provider backed by manga-ocr (kha-white/manga-ocr-base).

    Confidence is estimated as the geometric mean of per-token max softmax
    probabilities, a common proxy for sequence confidence in TrOCR-style models.
    Orientation is derived from the region's aspect ratio.
    """

    def __init__(self, pretrained_model_name_or_path: str | None = None) -> None:
        try:
            from manga_ocr import MangaOcr  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "manga-ocr is required for MangaOcrProvider. Install it with: pip install manga-ocr"
            ) from exc

        model_name = (
            pretrained_model_name_or_path
            if pretrained_model_name_or_path is not None
            else os.environ.get("MANGA_OCR_MODEL", "kha-white/manga-ocr-base")
        )
        self._mocr = MangaOcr(model_name)
        # In newer transformers, ViTImageProcessorPil has no .decode(); grab the
        # tokenizer explicitly so decoding works regardless of transformers version.
        try:
            self._tokenizer = self._mocr.processor.tokenizer
        except AttributeError:
            from transformers import AutoTokenizer  # noqa: PLC0415

            self._tokenizer = AutoTokenizer.from_pretrained(model_name)

    def ocr_region(self, region: Image.Image, bbox: BBox) -> OcrResult:
        import torch  # noqa: PLC0415

        region_rgb = region.convert("RGB")

        # Run model with scores to compute confidence
        pixel_values = self._mocr.processor(region_rgb, return_tensors="pt").pixel_values.squeeze()

        with torch.no_grad():
            out = self._mocr.model.generate(
                pixel_values[None].to(self._mocr.model.device),
                return_dict_in_generate=True,
                output_scores=True,
            )

        token_ids = out.sequences[0].cpu()
        text: str = self._tokenizer.decode(token_ids, skip_special_tokens=True)

        # Geometric mean of max token probabilities as confidence proxy
        scores = out.scores  # tuple of (1, vocab_size) tensors
        if scores:
            probs = [float(torch.softmax(s[0], dim=-1).max()) for s in scores]
            confidence = math.exp(sum(math.log(max(p, 1e-9)) for p in probs) / len(probs))
        else:
            confidence = 0.0

        orientation = _orientation_from_bbox(bbox)
        lines = [ln for ln in text.splitlines() if ln.strip()] or ([text] if text else [])

        return OcrResult(
            original=text,
            lines=lines,
            orientation=orientation,
            ocr_confidence=round(confidence, 4),
        )
