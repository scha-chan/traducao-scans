"""ConsistencyStage: verificação de consistência das traduções (PRD §17.6)."""

from __future__ import annotations

import re

from agent.stage import Stage
from agent.state import PageAnalysisState

# CJK Unicode ranges: CJK Unified Ideographs, Hiragana, Katakana, Halfwidth/Fullwidth
_CJK_RE = re.compile(r"[一-鿿぀-ヿ＀-￯]")

# Capitalised name token: starts uppercase, followed by 1+ lowercase letters
_NAME_RE = re.compile(r"\b[A-Z][a-z]+\b")


class ConsistencyStage(Stage):
    """Etapa 8: verifica consistência das traduções geradas (PRD §17.6).

    R1 — Japonês residual: se qualquer candidate.translation contiver caracteres
         CJK, sets dialogue.needs_review=True, review_reason="japanese_in_translation".

    R2 — Personagem desconhecido: se um token capitalizado em candidate.translation
         NÃO estiver em state.characters, sets needs_review=True,
         review_reason="unknown_character_name".

    R3 — Duplicata de aprovada: se dialogue.original tiver tradução aprovada em
         state.approved_translations diferente do melhor candidato (relevance=1),
         sets needs_review=True, review_reason="inconsistent_with_approved".
    """

    @property
    def name(self) -> str:
        return "consistency"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        known: set[str] = {c.lower() for c in state.characters}

        for dialogue in state.dialogues:
            if not dialogue.translations:
                continue

            for candidate in dialogue.translations:
                text = candidate.translation

                # R1 — Japonês residual
                if _CJK_RE.search(text):
                    dialogue.needs_review = True
                    dialogue.review_reason = "japanese_in_translation"
                    break

                # R2 — Personagem desconhecido
                if state.characters:
                    for token in _NAME_RE.findall(text):
                        if token.lower() not in known:
                            dialogue.needs_review = True
                            dialogue.review_reason = "unknown_character_name"
                            break

            if dialogue.needs_review:
                continue

            # R3 — Inconsistente com aprovada (verifica apenas melhor candidato)
            if dialogue.original and dialogue.original in state.approved_translations:
                approved = state.approved_translations[dialogue.original]
                best = next(
                    (c for c in dialogue.translations if c.relevance == 1),
                    None,
                )
                if best is not None and best.translation != approved:
                    dialogue.needs_review = True
                    dialogue.review_reason = "inconsistent_with_approved"

        return state
