"""Tests for ConsistencyStage (PRD §17.6)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent.stages.consistency import ConsistencyStage
from agent.state import BBox, DialogueState, PageAnalysisState, TranslationCandidate


def _state(**kwargs: object) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="dummy.jpg",
        **kwargs,  # type: ignore[arg-type]
    )


def _dialogue(original: str, translations: list[TranslationCandidate]) -> DialogueState:
    d = DialogueState(id=str(uuid4()), bbox=BBox(0, 0, 10, 10))
    d.original = original
    d.translations = translations
    return d


def _candidate(text: str, relevance: int = 1) -> TranslationCandidate:
    return TranslationCandidate(translation=text, observation="", relevance=relevance)


stage = ConsistencyStage()


# R1 — Japonês residual


@pytest.mark.asyncio
async def test_r1_japanese_residual() -> None:
    d = _dialogue("これ", [_candidate("「これ」 isso aqui")])
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].needs_review is True
    assert state.dialogues[0].review_reason == "japanese_in_translation"


@pytest.mark.asyncio
async def test_r1_clean_passes() -> None:
    d = _dialogue("これ", [_candidate("Isso aqui")])
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].needs_review is False


# R2 — Personagem desconhecido


@pytest.mark.asyncio
async def test_r2_unknown_character() -> None:
    d = _dialogue("やまもと", [_candidate("Yamamoto chegou")])
    state = await stage.run(_state(dialogues=[d], characters=["Tanaka"]))
    assert state.dialogues[0].needs_review is True
    assert state.dialogues[0].review_reason == "unknown_character_name"


@pytest.mark.asyncio
async def test_r2_known_character_passes() -> None:
    d = _dialogue("やまもと", [_candidate("Yamamoto chegou")])
    state = await stage.run(_state(dialogues=[d], characters=["Yamamoto"]))
    assert state.dialogues[0].needs_review is False


# R3 — Inconsistente com aprovada


@pytest.mark.asyncio
async def test_r3_inconsistent_approved() -> None:
    d = _dialogue("元気ですか", [_candidate("Como você está?")])
    approved = {"元気ですか": "Tudo bem?"}
    state = await stage.run(_state(dialogues=[d], approved_translations=approved))
    assert state.dialogues[0].needs_review is True
    assert state.dialogues[0].review_reason == "inconsistent_with_approved"


@pytest.mark.asyncio
async def test_r3_consistent_approved() -> None:
    d = _dialogue("元気ですか", [_candidate("Tudo bem?")])
    approved = {"元気ですか": "Tudo bem?"}
    state = await stage.run(_state(dialogues=[d], approved_translations=approved))
    assert state.dialogues[0].needs_review is False


# Edge case: sem traduções → sem crash


@pytest.mark.asyncio
async def test_no_translations_skipped() -> None:
    d = DialogueState(id=str(uuid4()), bbox=BBox(0, 0, 10, 10))
    d.original = "何か"
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].needs_review is False
