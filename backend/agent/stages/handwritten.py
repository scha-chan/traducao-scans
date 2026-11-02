"""HandwrittenStage: força NEEDS_REVIEW em diálogos manuscritos (F3-AG-07).

PRD §9.3: texto manuscrito recebe handwritten=True e entra obrigatoriamente
como NEEDS_REVIEW, independentemente da confiança do OCR (§17.5).

A flag handwritten é setada por etapas anteriores ou por edição manual.
Esta stage aplica apenas a política de revisão obrigatória.
"""

from __future__ import annotations

import logging

from agent.stage import Stage
from agent.state import PageAnalysisState

logger = logging.getLogger(__name__)

_REVIEW_REASON = "handwritten"


class HandwrittenStage(Stage):
    """Seta needs_review=True em diálogos com handwritten=True.

    Deve rodar após MergeBlocksStage e LowConfidenceStage, antes de
    TranslationStage, para que o tradutor saiba que o texto pode ser ambíguo.
    """

    @property
    def name(self) -> str:
        return "handwritten"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        for dialogue in state.dialogues:
            if not dialogue.handwritten:
                continue
            dialogue.needs_review = True
            if not dialogue.review_reason:
                dialogue.review_reason = _REVIEW_REASON
            logger.debug(
                "handwritten: dialogue %s marked NEEDS_REVIEW (reason=%s)",
                dialogue.id,
                dialogue.review_reason,
            )
        return state
