"""Stub stage — placeholder until F3-AG-02+ stages are implemented."""

from __future__ import annotations

from agent.stage import Stage
from agent.state import PageAnalysisState


class StubStage(Stage):
    """No-op stage that passes state through unchanged.

    Replaced by real detection/OCR/translation stages in F3-AG-02 – F3-AG-07.
    """

    @property
    def name(self) -> str:
        return "stub"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        return state
