"""DetectionStage: text region detection → DialogueState with bbox (F3-AG-03)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from agent.providers.detection import DetectionProvider
from agent.stage import Stage
from agent.state import DialogueState, PageAnalysisState


class DetectionStage(Stage):
    """Detect text regions in the preprocessed image and populate state.dialogues.

    Delegates the actual detection to an injectable ``DetectionProvider`` so the
    stage is testable without a real model.  Wire ``ComicTextDetectorProvider``
    in production via ``build_pipeline()``.
    """

    def __init__(self, provider: DetectionProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return "detection"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        loop = asyncio.get_event_loop()
        bboxes = await loop.run_in_executor(None, self._provider.detect, state.image_path)
        state.dialogues = [DialogueState(id=str(uuid4()), bbox=bbox) for bbox in bboxes]
        return state
