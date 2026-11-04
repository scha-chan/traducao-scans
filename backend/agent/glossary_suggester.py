"""V2-AG-02: Sugestão automática de entradas para o glossário da obra.

Detecta termos recorrentes (nomes próprios, honoríficos, onomatopeias) no
conjunto de blocos aprovados de uma obra e sugere novas entradas de glossário
que ainda não foram registradas.

Estratégia (sem LLM, determinística):
  1. Coleta todos os originais de blocos REVIEWED da obra.
  2. Extrai candidatos por padrões heurísticos:
     - Sequências de katakana (nomes estrangeiros/empréstimos)
     - Sequências de kanji terminadas em honorífico (先生, 様, 君, ちゃん, くん)
     - Tokens que aparecem em ≥ MIN_OCCURRENCES páginas distintas
  3. Filtra termos já presentes no glossário.
  4. Retorna lista de sugestões ordenadas por frequência de página.

Uso:
    suggester = GlossarySuggester(session)
    suggestions = await suggester.suggest(work_id)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Folder, GlossaryEntry, Page, ReviewStatus, TextBlock

# Minimum number of distinct pages a term must appear in to be suggested
_MIN_OCCURRENCES = 2

# Katakana block + voiced/semi-voiced marks
_RE_KATAKANA = re.compile(r"[ァ-ヶヷ-ヺー]{2,}")

# Common honorifics / address forms that may follow names
_HONORIFICS = ("先生", "様", "さま", "くん", "君", "ちゃん", "さん", "姫", "王", "殿")

# Kanji range (CJK Unified Ideographs)
_RE_KANJI_SEQ = re.compile(r"[一-鿿]{2,}")


@dataclass
class GlossarySuggestion:
    """A candidate glossary entry."""

    source_term: str
    page_count: int  # number of distinct pages where it appears
    category: str  # "katakana" | "honorific" | "kanji"
    sample_context: str  # a short excerpt of one of the original texts


def _extract_candidates(text: str) -> list[tuple[str, str]]:
    """Return (term, category) pairs from a Japanese text string."""
    candidates: list[tuple[str, str]] = []

    # Katakana sequences (foreign names/loanwords)
    for m in _RE_KATAKANA.finditer(text):
        candidates.append((m.group(), "katakana"))

    # Kanji sequences followed by honorific
    for honorific in _HONORIFICS:
        idx = 0
        while True:
            pos = text.find(honorific, idx)
            if pos == -1:
                break
            # Look back for a kanji/kana name fragment (up to 6 chars)
            start = max(0, pos - 6)
            prefix = text[start:pos]
            # keep only the last continuous run of kanji/kana chars
            name_match = re.search(r"[぀-鿿]+$", prefix)
            if name_match and len(name_match.group()) >= 1:
                full_term = name_match.group() + honorific
                candidates.append((full_term, "honorific"))
            idx = pos + len(honorific)

    # Standalone kanji sequences (names, special terms)
    for m in _RE_KANJI_SEQ.finditer(text):
        candidates.append((m.group(), "kanji"))

    return candidates


async def _existing_terms(work_id: UUID, session: AsyncSession) -> set[str]:
    result = await session.execute(
        select(GlossaryEntry.source_term).where(GlossaryEntry.work_id == work_id)
    )
    return {row[0] for row in result.all()}


class GlossarySuggester:
    """Suggests new glossary entries by scanning reviewed blocks of a work."""

    def __init__(self, session: AsyncSession, min_occurrences: int = _MIN_OCCURRENCES) -> None:
        self._session = session
        self._min_occurrences = min_occurrences

    async def suggest(self, work_id: UUID) -> list[GlossarySuggestion]:
        """Return suggested new glossary entries for the given work."""
        existing = await _existing_terms(work_id, self._session)

        # Fetch all reviewed text blocks for the work
        stmt = (
            select(TextBlock.original, Page.page_number)
            .join(Page, Page.id == TextBlock.page_id)
            .join(Folder, Folder.id == Page.folder_id)
            .where(
                Folder.work_id == work_id,
                TextBlock.review_status == ReviewStatus.REVIEWED,
                TextBlock.original.isnot(None),
            )
        )
        rows = (await self._session.execute(stmt)).all()

        # Build term → {pages, contexts}
        term_pages: dict[str, set[int]] = {}
        term_category: dict[str, str] = {}
        term_context: dict[str, str] = {}

        for original, page_number in rows:
            if not original:
                continue
            for term, category in _extract_candidates(original):
                if term in existing:
                    continue
                if term not in term_pages:
                    term_pages[term] = set()
                    term_category[term] = category
                    term_context[term] = original[:80]
                term_pages[term].add(page_number)

        suggestions = [
            GlossarySuggestion(
                source_term=term,
                page_count=len(pages),
                category=term_category[term],
                sample_context=term_context[term],
            )
            for term, pages in term_pages.items()
            if len(pages) >= self._min_occurrences
        ]
        suggestions.sort(key=lambda s: s.page_count, reverse=True)
        return suggestions
