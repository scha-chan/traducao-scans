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

    Stages F3-AG-04 through F3-AG-07 are wired here as they are implemented.
    """
    import os  # noqa: PLC0415

    from agent.providers.detection import ComicTextDetectorProvider  # noqa: PLC0415
    from agent.stages.detection import DetectionStage  # noqa: PLC0415
    from agent.stages.preprocess import PreprocessStage  # noqa: PLC0415

    detection = DetectionStage(
        provider=ComicTextDetectorProvider(model_path=os.environ.get("CTD_MODEL_PATH"))
    )
    return Orchestrator(stages=[PreprocessStage(), detection])
