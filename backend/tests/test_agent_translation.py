"""Unit tests for TranslationStage (F3-AG-08)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent.providers.translation import TranslationProvider, TranslationResult
from agent.stages.translation import TranslationStage
from agent.state import BBox, DialogueState, PageAnalysisState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(dialogues: list[DialogueState] | None = None) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="/fake/page.png",
        dialogues=dialogues or [],
    )


def _dialogue(original: str | None = "きめたよ") -> DialogueState:
    return DialogueState(
        id=str(uuid4()), bbox=BBox(x=0, y=0, width=50, height=80), original=original
    )


class _FakeTranslationProvider:
    def __init__(self, translation: str = "Eu decidi!", relevance: int = 3) -> None:
        self._result = TranslationResult(
            translation=translation, observation="", relevance=relevance
        )

    def translate(self, text: str) -> TranslationResult:
        return self._result


class _FailingTranslationProvider:
    def translate(self, text: str) -> TranslationResult:
        raise RuntimeError("API unavailable")


# ---------------------------------------------------------------------------
# Tests — TranslationStage contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_dialogues_returns_state_unchanged() -> None:
    state = _make_state()
    result = await TranslationStage(provider=_FakeTranslationProvider()).run(state)
    assert result.dialogues == []


@pytest.mark.asyncio
async def test_dialogue_without_original_is_skipped() -> None:
    state = _make_state([_dialogue(original=None)])
    result = await TranslationStage(provider=_FakeTranslationProvider()).run(state)
    assert result.dialogues[0].translations == []


@pytest.mark.asyncio
async def test_dialogue_with_empty_original_is_skipped() -> None:
    state = _make_state([_dialogue(original="")])
    result = await TranslationStage(provider=_FakeTranslationProvider()).run(state)
    assert result.dialogues[0].translations == []


@pytest.mark.asyncio
async def test_translation_candidate_appended() -> None:
    state = _make_state([_dialogue(original="きめたよ")])
    result = await TranslationStage(
        provider=_FakeTranslationProvider(translation="Eu decidi!")
    ).run(state)
    assert len(result.dialogues[0].translations) == 1
    assert result.dialogues[0].translations[0].translation == "Eu decidi!"


@pytest.mark.asyncio
async def test_relevance_set_on_candidate() -> None:
    state = _make_state([_dialogue()])
    result = await TranslationStage(provider=_FakeTranslationProvider(relevance=4)).run(state)
    assert result.dialogues[0].translations[0].relevance == 4


@pytest.mark.asyncio
async def test_multiple_dialogues_all_translated() -> None:
    state = _make_state([_dialogue("きめたよ"), _dialogue("なんで？")])
    result = await TranslationStage(provider=_FakeTranslationProvider()).run(state)
    assert all(len(d.translations) == 1 for d in result.dialogues)


@pytest.mark.asyncio
async def test_translation_failure_sets_needs_review() -> None:
    state = _make_state([_dialogue()])
    result = await TranslationStage(provider=_FailingTranslationProvider()).run(state)
    assert result.dialogues[0].needs_review is True
    assert result.dialogues[0].review_reason == "translation_failed"
    assert result.dialogues[0].translations == []


@pytest.mark.asyncio
async def test_failure_does_not_abort_remaining_dialogues() -> None:
    """A failing dialogue must not prevent subsequent dialogues from being translated."""
    dialogues = [_dialogue("失敗"), _dialogue("成功")]
    state = _make_state(dialogues)

    call_count = 0

    class _PartialProvider:
        def translate(self, text: str) -> TranslationResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("first fails")
            return TranslationResult(translation="Sucesso", observation="", relevance=3)

    result = await TranslationStage(provider=_PartialProvider()).run(state)
    assert result.dialogues[0].needs_review is True
    assert len(result.dialogues[1].translations) == 1


@pytest.mark.asyncio
async def test_stage_name_is_translation() -> None:
    assert TranslationStage(provider=_FakeTranslationProvider()).name == "translation"


def test_fake_provider_satisfies_protocol() -> None:
    assert isinstance(_FakeTranslationProvider(), TranslationProvider)
