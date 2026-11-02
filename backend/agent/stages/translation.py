"""TranslationStage: JA→PT translation per dialogue region (F3-AG-08)."""

from __future__ import annotations

import logging

from agent.providers.translation import TranslationProvider
from agent.stage import Stage
from agent.state import PageAnalysisState, TranslationCandidate

logger = logging.getLogger(__name__)


class TranslationStage(Stage):
    """Translate each dialogue's OCR text from Japanese to Portuguese.

    For each ``DialogueState`` in ``state.dialogues`` with a non-empty
    ``original`` field, calls the injected ``TranslationProvider`` and
    appends a ``TranslationCandidate`` to ``DialogueState.translations``.

    A translation failure for a single dialogue sets ``needs_review=True``
    on that dialogue and logs a warning instead of aborting the pipeline.
    """

    def __init__(self, provider: TranslationProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return "translation"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        for dialogue in state.dialogues:
            if not dialogue.original:
                continue
            try:
                result = self._provider.translate(dialogue.original)
                dialogue.translations.append(
                    TranslationCandidate(
                        translation=result.translation,
                        observation=result.observation,
                        relevance=result.relevance,
                    )
                )
            except Exception:
                logger.warning(
                    "translation failed for dialogue=%s page_id=%s",
                    dialogue.id,
                    state.page_id,
                    exc_info=True,
                )
                dialogue.needs_review = True
                dialogue.review_reason = "translation_failed"
        return state
