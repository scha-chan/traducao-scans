"""Tests for GuardrailsStage (PRD §17.7)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent.stages.guardrails import GuardrailsStage
from agent.state import BBox, DialogueState, PageAnalysisState, TranslationCandidate


def _state(**kwargs: object) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="dummy.jpg",
        **kwargs,  # type: ignore[arg-type]
    )


def _dialogue(original: str | None = "テスト") -> DialogueState:
    d = DialogueState(id=str(uuid4()), bbox=BBox(0, 0, 10, 10))
    d.original = original
    return d


def _candidate(text: str, relevance: int = 3) -> TranslationCandidate:
    return TranslationCandidate(translation=text, observation="", relevance=relevance)


stage = GuardrailsStage()


# G1 — EMPTY_ORIGINAL


@pytest.mark.asyncio
async def test_g1_empty_original() -> None:
    d = _dialogue(original="")
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].needs_review is True
    assert state.dialogues[0].review_reason == "empty_original"
    g1_entries = [e for e in state.agent_log if e.trigger == "rule_G1"]
    assert len(g1_entries) == 1
    assert g1_entries[0].stage == "guardrails"
    assert g1_entries[0].action == "flagged"


@pytest.mark.asyncio
async def test_g1_none_original() -> None:
    d = _dialogue(original=None)
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].needs_review is True
    assert state.dialogues[0].review_reason == "empty_original"


@pytest.mark.asyncio
async def test_g1_whitespace_only_original() -> None:
    d = _dialogue(original="   ")
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].needs_review is True
    assert state.dialogues[0].review_reason == "empty_original"


# G2 — NO_TRANSLATIONS


@pytest.mark.asyncio
async def test_g2_no_translations() -> None:
    d = _dialogue()
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].needs_review is True
    assert state.dialogues[0].review_reason == "no_translations"
    g2_entries = [e for e in state.agent_log if e.trigger == "rule_G2"]
    assert len(g2_entries) == 1
    assert g2_entries[0].action == "flagged"


# G3 — TRANSLATION_TOO_LONG


@pytest.mark.asyncio
async def test_g3_truncates_long_translation() -> None:
    long_text = "A" * 600
    d = _dialogue()
    d.translations = [_candidate(long_text)]
    state = await stage.run(_state(dialogues=[d]))
    result = state.dialogues[0].translations[0].translation
    assert len(result) == 501  # 500 + "…"
    assert result.endswith("…")
    g3_entries = [e for e in state.agent_log if e.trigger == "rule_G3"]
    assert len(g3_entries) == 1
    assert g3_entries[0].action == "truncated"


@pytest.mark.asyncio
async def test_g3_exact_limit_passes() -> None:
    text = "A" * 500
    d = _dialogue()
    d.translations = [_candidate(text)]
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].translations[0].translation == text


# G4 — RELEVANCE_OUT_OF_RANGE


@pytest.mark.asyncio
async def test_g4_clamps_relevance_above() -> None:
    d = _dialogue()
    d.translations = [_candidate("Texto", relevance=7)]
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].translations[0].relevance == 5
    g4_entries = [e for e in state.agent_log if e.trigger == "rule_G4"]
    assert len(g4_entries) == 1
    assert g4_entries[0].action == "clamped"


@pytest.mark.asyncio
async def test_g4_clamps_relevance_below() -> None:
    d = _dialogue()
    d.translations = [_candidate("Texto", relevance=0)]
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].translations[0].relevance == 1
    g4_entries = [e for e in state.agent_log if e.trigger == "rule_G4"]
    assert len(g4_entries) == 1


@pytest.mark.asyncio
async def test_g4_valid_relevance_unchanged() -> None:
    d = _dialogue()
    d.translations = [_candidate("Texto", relevance=3)]
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].translations[0].relevance == 3
    assert not any(e.trigger == "rule_G4" for e in state.agent_log)


# G5 — DUPLICATE_TRANSLATIONS


@pytest.mark.asyncio
async def test_g5_removes_duplicates() -> None:
    d = _dialogue()
    d.translations = [
        _candidate("Olá mundo", relevance=2),
        _candidate("Olá mundo", relevance=4),
    ]
    state = await stage.run(_state(dialogues=[d]))
    assert len(state.dialogues[0].translations) == 1
    assert state.dialogues[0].translations[0].relevance == 2  # kept lower relevance
    g5_entries = [e for e in state.agent_log if e.trigger == "rule_G5"]
    assert len(g5_entries) == 1
    assert g5_entries[0].action == "deduplicated"


@pytest.mark.asyncio
async def test_g5_keeps_better_when_duplicate_has_lower_relevance() -> None:
    d = _dialogue()
    d.translations = [
        _candidate("Olá mundo", relevance=4),
        _candidate("Olá mundo", relevance=1),
    ]
    state = await stage.run(_state(dialogues=[d]))
    assert len(state.dialogues[0].translations) == 1
    assert state.dialogues[0].translations[0].relevance == 1


@pytest.mark.asyncio
async def test_g5_distinct_translations_kept() -> None:
    d = _dialogue()
    d.translations = [_candidate("Olá mundo"), _candidate("Tchau mundo")]
    state = await stage.run(_state(dialogues=[d]))
    assert len(state.dialogues[0].translations) == 2
    assert not any(e.trigger == "rule_G5" for e in state.agent_log)


# ENV var disabling


@pytest.mark.asyncio
async def test_guardrail_disabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUARDRAIL_EMPTY_ORIGINAL", "0")
    d = _dialogue(original="")
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].needs_review is False
    assert not any(e.trigger == "rule_G1" for e in state.agent_log)


# All clean


@pytest.mark.asyncio
async def test_all_clean_passes() -> None:
    d = _dialogue(original="テスト")
    d.translations = [_candidate("Teste", relevance=2)]
    state = await stage.run(_state(dialogues=[d]))
    assert state.dialogues[0].needs_review is False
    assert state.dialogues[0].review_reason is None
    assert not any(e.trigger.startswith("rule_G") for e in state.agent_log)
