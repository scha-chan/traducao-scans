"""GlossaryContextStage: injects glossary hints into each dialogue (V2-AG-01, PRD §30.2)."""

from __future__ import annotations

from agent.stage import Stage
from agent.state import PageAnalysisState


class GlossaryContextStage(Stage):
    """Annotates dialogues with matching glossary hints from state.work_glossary.

    Must run after OcrStage (needs dialogue.original) and before TranslationStage.
    The state.work_glossary list is pre-fetched by the orchestrator from the DB.
    """

    @property
    def name(self) -> str:
        return "glossary_context"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        if not state.work_glossary:
            return state

        for dialogue in state.dialogues:
            if not dialogue.original:
                continue
            dialogue.glossary_hints = [
                hint for hint in state.work_glossary if hint.source_term in dialogue.original
            ]

        return state
