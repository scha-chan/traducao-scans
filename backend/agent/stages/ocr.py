"""OcrStage: per-region OCR → original, lines, orientation, ocr_confidence (F3-AG-04)."""

from __future__ import annotations

import asyncio

from PIL import Image

from agent.providers.ocr import OcrProvider
from agent.stage import Stage
from agent.state import PageAnalysisState


class OcrStage(Stage):
    """Run OCR on each detected region and populate dialogue fields.

    For each ``DialogueState`` in ``state.dialogues`` the stage crops the
    region from ``state.image_path`` and calls the injected ``OcrProvider``.
    Fields updated per dialogue: ``original``, ``lines``, ``orientation``,
    ``ocr_confidence``.
    """

    def __init__(self, provider: OcrProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return "ocr"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        if not state.dialogues:
            return state
        loop = asyncio.get_event_loop()
        img = await loop.run_in_executor(None, Image.open, state.image_path)
        img_rgb = img.convert("RGB")

        for dialogue in state.dialogues:
            bbox = dialogue.bbox
            region = img_rgb.crop((bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height))
            result = await loop.run_in_executor(None, self._provider.ocr_region, region, bbox)
            dialogue.original = result.original
            dialogue.lines = result.lines
            dialogue.orientation = result.orientation
            dialogue.ocr_confidence = result.ocr_confidence

        return state
