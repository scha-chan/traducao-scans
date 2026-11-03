"""GuardrailsStage: guardrails determinísticos (PRD §17.7)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from agent.stage import Stage
from agent.state import AgentLogEntry, PageAnalysisState, TranslationCandidate

logger = logging.getLogger(__name__)

_DEFAULT_MAX_LEN = 500


def _enabled(rule: str) -> bool:
    return os.environ.get(f"GUARDRAIL_{rule}", "1") != "0"


@dataclass
class GuardrailViolation:
    rule: str
    dialogue_id: str
    detail: str


class GuardrailsStage(Stage):
    """Etapa 9: guardrails determinísticos (PRD §17.7).

    G1 — EMPTY_ORIGINAL: dialogue.original is None or empty after strip.
         Action: needs_review=True, review_reason="empty_original", log entry.

    G2 — NO_TRANSLATIONS: dialogue.translations is empty after TranslationStage.
         Action: needs_review=True, review_reason="no_translations".

    G3 — TRANSLATION_TOO_LONG: len(candidate.translation) > MAX_TRANSLATION_LEN
         (default 500, configurable via GUARDRAIL_MAX_TRANSLATION_LEN).
         Action: truncate to max_len + "…", log warning.

    G4 — RELEVANCE_OUT_OF_RANGE: candidate.relevance < 1 or > 5.
         Action: clamp to [1, 5], log warning.

    G5 — DUPLICATE_TRANSLATIONS: two candidates with identical translation (after strip).
         Action: remove duplicates keeping the one with lower relevance, log info.

    Each rule configurable via GUARDRAIL_<RULE>=0 env var to disable.
    """

    @property
    def name(self) -> str:
        return "guardrails"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        max_len = int(os.environ.get("GUARDRAIL_MAX_TRANSLATION_LEN", str(_DEFAULT_MAX_LEN)))

        for dialogue in state.dialogues:
            # G1 — EMPTY_ORIGINAL
            if _enabled("EMPTY_ORIGINAL") and (
                dialogue.original is None or not dialogue.original.strip()
            ):
                dialogue.needs_review = True
                dialogue.review_reason = "empty_original"
                state.agent_log.append(
                    AgentLogEntry(
                        timestamp=datetime.now(UTC),
                        stage="guardrails",
                        trigger="rule_G1",
                        action="flagged",
                        detail={"dialogue_id": dialogue.id},
                    )
                )

            # G2 — NO_TRANSLATIONS (only when original present; G1 covers empty original)
            if _enabled("NO_TRANSLATIONS"):
                has_original = dialogue.original is not None and bool(dialogue.original.strip())
                if has_original and not dialogue.translations:
                    dialogue.needs_review = True
                    dialogue.review_reason = "no_translations"
                    state.agent_log.append(
                        AgentLogEntry(
                            timestamp=datetime.now(UTC),
                            stage="guardrails",
                            trigger="rule_G2",
                            action="flagged",
                            detail={"dialogue_id": dialogue.id},
                        )
                    )

            for candidate in dialogue.translations:
                # G3 — TRANSLATION_TOO_LONG
                if _enabled("TRANSLATION_TOO_LONG") and len(candidate.translation) > max_len:
                    original_len = len(candidate.translation)
                    candidate.translation = candidate.translation[:max_len] + "…"
                    logger.warning(
                        "guardrail G3: truncated translation dialogue=%s len=%d->%d",
                        dialogue.id,
                        original_len,
                        len(candidate.translation),
                    )
                    state.agent_log.append(
                        AgentLogEntry(
                            timestamp=datetime.now(UTC),
                            stage="guardrails",
                            trigger="rule_G3",
                            action="truncated",
                            detail={"dialogue_id": dialogue.id, "original_len": original_len},
                        )
                    )

                # G4 — RELEVANCE_OUT_OF_RANGE
                if _enabled("RELEVANCE_OUT_OF_RANGE") and (
                    candidate.relevance < 1 or candidate.relevance > 5
                ):
                    original_rel = candidate.relevance
                    candidate.relevance = max(1, min(5, candidate.relevance))
                    logger.warning(
                        "guardrail G4: clamped relevance dialogue=%s %d->%d",
                        dialogue.id,
                        original_rel,
                        candidate.relevance,
                    )
                    state.agent_log.append(
                        AgentLogEntry(
                            timestamp=datetime.now(UTC),
                            stage="guardrails",
                            trigger="rule_G4",
                            action="clamped",
                            detail={
                                "dialogue_id": dialogue.id,
                                "original_relevance": original_rel,
                            },
                        )
                    )

            # G5 — DUPLICATE_TRANSLATIONS
            if _enabled("DUPLICATE_TRANSLATIONS") and len(dialogue.translations) > 1:
                unique: list[TranslationCandidate] = []
                seen: set[str] = set()
                removed = 0
                for candidate in dialogue.translations:
                    key = candidate.translation.strip()
                    if key in seen:
                        # keep the existing entry with lower (better) relevance
                        existing = next(c for c in unique if c.translation.strip() == key)
                        if candidate.relevance < existing.relevance:
                            idx = unique.index(existing)
                            unique[idx] = candidate
                        removed += 1
                    else:
                        seen.add(key)
                        unique.append(candidate)

                if removed:
                    dialogue.translations = unique
                    logger.info(
                        "guardrail G5: removed %d duplicate(s) dialogue=%s",
                        removed,
                        dialogue.id,
                    )
                    state.agent_log.append(
                        AgentLogEntry(
                            timestamp=datetime.now(UTC),
                            stage="guardrails",
                            trigger="rule_G5",
                            action="deduplicated",
                            detail={"dialogue_id": dialogue.id, "removed": removed},
                        )
                    )

        return state
