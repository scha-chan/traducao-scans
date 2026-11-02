"""Pipeline orchestrator — runs Stage sequence and accumulates agent_log."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from agent.stage import Stage
from agent.state import AgentLogEntry, PageAnalysisState

logger = logging.getLogger(__name__)


class Orchestrator:
    """Runs a list of stages in order, recording an agent_log entry per stage."""

    def __init__(self, stages: list[Stage]) -> None:
        self._stages = stages

    async def run(self, initial_state: PageAnalysisState) -> PageAnalysisState:
        state = initial_state
        for stage in self._stages:
            t0 = datetime.now(UTC)
            logger.debug("stage=%s page_id=%s start", stage.name, state.page_id)
            state = await stage.run(state)
            elapsed_ms = int((datetime.now(UTC) - t0).total_seconds() * 1000)
            state.agent_log.append(
                AgentLogEntry(
                    timestamp=datetime.now(UTC),
                    stage=stage.name,
                    trigger="pipeline",
                    action="completed",
                    detail={"elapsed_ms": elapsed_ms},
                )
            )
            logger.debug(
                "stage=%s page_id=%s done elapsed_ms=%d", stage.name, state.page_id, elapsed_ms
            )
        return state


def build_pipeline() -> Orchestrator:
    """Construct the default full-analysis pipeline.

    Stages F3-AG-06 and F3-AG-07 are wired here as they are implemented.
    """
    import os  # noqa: PLC0415

    from agent.providers.detection import ComicTextDetectorProvider  # noqa: PLC0415
    from agent.providers.ocr import MangaOcrProvider  # noqa: PLC0415
    from agent.providers.translation import MarianTranslationProvider  # noqa: PLC0415
    from agent.stages.confidence import LowConfidenceStage  # noqa: PLC0415
    from agent.stages.detection import DetectionStage  # noqa: PLC0415
    from agent.stages.handwritten import HandwrittenStage  # noqa: PLC0415
    from agent.stages.merge_blocks import MergeBlocksStage  # noqa: PLC0415
    from agent.stages.ocr import OcrStage  # noqa: PLC0415
    from agent.stages.preprocess import PreprocessStage  # noqa: PLC0415
    from agent.stages.translation import TranslationStage  # noqa: PLC0415

    detection = DetectionStage(
        provider=ComicTextDetectorProvider(model_path=os.environ.get("CTD_MODEL_PATH"))
    )
    ocr = OcrStage(
        provider=MangaOcrProvider(pretrained_model_name_or_path=os.environ.get("MANGA_OCR_MODEL"))
    )
    merge = MergeBlocksStage()
    confidence = LowConfidenceStage(
        threshold=float(os.environ.get("OCR_LOW_CONFIDENCE_THRESHOLD", "0.80"))
    )
    translation = TranslationStage(
        provider=MarianTranslationProvider(
            ja_en_model=os.environ.get("TRANSLATION_JA_EN_MODEL"),
            en_pt_model=os.environ.get("TRANSLATION_EN_PT_MODEL"),
        )
    )
    handwritten = HandwrittenStage()
    return Orchestrator(
        stages=[PreprocessStage(), detection, ocr, merge, confidence, handwritten, translation]
    )
