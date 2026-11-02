"""Unit tests for LowConfidenceStage (F3-AG-05)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent.stages.confidence import LowConfidenceStage
from agent.state import BBox, DialogueState, PageAnalysisState


def _make_state(dialogues: list[DialogueState] | None = None) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="/fake/page.png",
        dialogues=dialogues or [],
    )


def _dialogue(confidence: float | None = None) -> DialogueState:
    d = DialogueState(id=str(uuid4()), bbox=BBox(x=0, y=0, width=50, height=80))
    d.ocr_confidence = confidence
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_dialogues_unchanged() -> None:
    result = await LowConfidenceStage().run(_make_state())
    assert result.dialogues == []


@pytest.mark.asyncio
async def test_dialogue_without_confidence_ignored() -> None:
    state = _make_state([_dialogue(confidence=None)])
    result = await LowConfidenceStage(threshold=0.80).run(state)
    assert result.dialogues[0].needs_review is False


@pytest.mark.asyncio
async def test_below_threshold_sets_needs_review() -> None:
    state = _make_state([_dialogue(confidence=0.70)])
    result = await LowConfidenceStage(threshold=0.80).run(state)
    assert result.dialogues[0].needs_review is True


@pytest.mark.asyncio
async def test_below_threshold_sets_review_reason() -> None:
    state = _make_state([_dialogue(confidence=0.70)])
    result = await LowConfidenceStage(threshold=0.80).run(state)
    assert result.dialogues[0].review_reason == "low_ocr_confidence"


@pytest.mark.asyncio
async def test_equal_threshold_does_not_flag() -> None:
    state = _make_state([_dialogue(confidence=0.80)])
    result = await LowConfidenceStage(threshold=0.80).run(state)
    assert result.dialogues[0].needs_review is False


@pytest.mark.asyncio
async def test_above_threshold_does_not_flag() -> None:
    state = _make_state([_dialogue(confidence=0.95)])
    result = await LowConfidenceStage(threshold=0.80).run(state)
    assert result.dialogues[0].needs_review is False


@pytest.mark.asyncio
async def test_only_low_confidence_dialogues_flagged() -> None:
    state = _make_state([_dialogue(0.50), _dialogue(0.90), _dialogue(0.79)])
    result = await LowConfidenceStage(threshold=0.80).run(state)
    flagged = [d.needs_review for d in result.dialogues]
    assert flagged == [True, False, True]


@pytest.mark.asyncio
async def test_custom_threshold_respected() -> None:
    state = _make_state([_dialogue(0.60)])
    assert (await LowConfidenceStage(threshold=0.50).run(state)).dialogues[0].needs_review is False
    assert (await LowConfidenceStage(threshold=0.70).run(state)).dialogues[0].needs_review is True


@pytest.mark.asyncio
async def test_existing_needs_review_preserved() -> None:
    """Stage must not clear a needs_review already set by a prior stage."""
    d = _dialogue(confidence=0.95)
    d.needs_review = True
    d.review_reason = "prior_reason"
    result = await LowConfidenceStage(threshold=0.80).run(_make_state([d]))
    assert result.dialogues[0].needs_review is True
    assert result.dialogues[0].review_reason == "prior_reason"


@pytest.mark.asyncio
async def test_stage_name() -> None:
    assert LowConfidenceStage().name == "low_confidence"
