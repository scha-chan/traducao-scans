"""TranslationStage: JA→PT translation per dialogue region (F3-AG-08, F5-AG-03)."""

from __future__ import annotations

import logging

from agent.providers.translation import TranslationProvider
from agent.stage import Stage
from agent.state import PageAnalysisState, TranslationCandidate

logger = logging.getLogger(__name__)

# Either the classic sync provider or an LLM provider (detected at runtime via hasattr).
AnyTranslationProvider = TranslationProvider | object


class TranslationStage(Stage):
    """Translate each dialogue's OCR text from Japanese to Portuguese.

    Accepts both a classic ``TranslationProvider`` (sync, single-candidate) and
    an ``LLMTranslationProvider`` (multi-candidate, context-aware).  Detection is
    done via duck typing: if the injected provider exposes ``translate_dialogue``,
    it is treated as an LLM provider; otherwise ``translate`` is used.

    A translation failure for a single dialogue sets ``needs_review=True``
    on that dialogue and logs a warning instead of aborting the pipeline.
    """

    def __init__(self, provider: AnyTranslationProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return "translation"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        is_llm = hasattr(self._provider, "translate_dialogue")
        for dialogue in state.dialogues:
            if not dialogue.original:
                continue
            try:
                if is_llm:
                    candidates: list[TranslationCandidate] = self._provider.translate_dialogue(  # type: ignore[union-attr]
                        dialogue, state.prompt_version, state
                    )
                    dialogue.translations.extend(candidates)
                else:
                    result = self._provider.translate(dialogue.original)  # type: ignore[union-attr]
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
