"""ClassificationStage: assign type (#/$) to each dialogue region (F4-AG-02).

PRD §7 and §17.3.

Runs after ReadingOrderStage (order is already set) and before TranslationStage
(translation uses type for context).

For each dialogue, opens the page image, crops the region with an expanded
margin and calls the injected ClassificationProvider.  The result is stored in
``dialogue.type`` and ``dialogue.type_confidence``.
"""

from __future__ import annotations

import asyncio
import logging

from PIL import Image

from agent.providers.classification import ClassificationProvider, HeuristicClassificationProvider
from agent.stage import Stage
from agent.state import PageAnalysisState

logger = logging.getLogger(__name__)


class ClassificationStage(Stage):
    """Classify each text region as speech-bubble (#) or non-bubble ($).

    The image is opened once per page and reused for all regions.
    Existing ``dialogue.type`` values are preserved when they were set
    manually (i.e. not None at entry — reserved for future manual override).
    """

    def __init__(self, provider: ClassificationProvider | None = None) -> None:
        self._provider: ClassificationProvider = (
            provider if provider is not None else HeuristicClassificationProvider()
        )

    @property
    def name(self) -> str:
        return "classification"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        if not state.dialogues:
            return state

        loop = asyncio.get_event_loop()
        img = await loop.run_in_executor(None, Image.open, state.image_path)
        img_rgb = img.convert("RGB")

        for dialogue in state.dialogues:
            result = await loop.run_in_executor(
                None, self._provider.classify, img_rgb, dialogue.bbox
            )
            dialogue.type = result.type
            dialogue.type_confidence = result.confidence
            logger.debug(
                "classification: id=%s type=%s confidence=%.3f",
                dialogue.id,
                result.type,
                result.confidence,
            )

        return state
