"""Unit tests for HandwrittenStage (F3-AG-07)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from agent.stages.handwritten import HandwrittenStage
from agent.state import BBox, DialogueState, PageAnalysisState


def _make_state(dialogues: list[DialogueState]) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="/fake/page.png",
        dialogues=dialogues,
    )


def _dialogue(handwritten: bool = False) -> DialogueState:
    d = DialogueState(id=str(uuid4()), bbox=BBox(x=0, y=0, width=50, height=80))
    d.handwritten = handwritten
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage_name() -> None:
    assert HandwrittenStage().name == "handwritten"


@pytest.mark.asyncio
async def test_empty_dialogues_unchanged() -> None:
    result = await HandwrittenStage().run(_make_state([]))
    assert result.dialogues == []


@pytest.mark.asyncio
async def test_non_handwritten_not_flagged() -> None:
    d = _dialogue(handwritten=False)
    result = await HandwrittenStage().run(_make_state([d]))
    assert result.dialogues[0].needs_review is False


@pytest.mark.asyncio
async def test_handwritten_sets_needs_review() -> None:
    d = _dialogue(handwritten=True)
    result = await HandwrittenStage().run(_make_state([d]))
    assert result.dialogues[0].needs_review is True


@pytest.mark.asyncio
async def test_handwritten_sets_review_reason() -> None:
    d = _dialogue(handwritten=True)
    result = await HandwrittenStage().run(_make_state([d]))
    assert result.dialogues[0].review_reason == "handwritten"


@pytest.mark.asyncio
async def test_handwritten_flag_preserved() -> None:
    """Stage must not clear or change the handwritten flag itself."""
    d = _dialogue(handwritten=True)
    result = await HandwrittenStage().run(_make_state([d]))
    assert result.dialogues[0].handwritten is True


@pytest.mark.asyncio
async def test_existing_review_reason_not_overwritten() -> None:
    """If review_reason is already set by a prior stage, it must be preserved."""
    d = _dialogue(handwritten=True)
    d.needs_review = True
    d.review_reason = "low_ocr_confidence"
    result = await HandwrittenStage().run(_make_state([d]))
    assert result.dialogues[0].review_reason == "low_ocr_confidence"


@pytest.mark.asyncio
async def test_existing_needs_review_true_preserved() -> None:
    """needs_review already True must stay True after the stage."""
    d = _dialogue(handwritten=False)
    d.needs_review = True
    d.review_reason = "some_prior_reason"
    result = await HandwrittenStage().run(_make_state([d]))
    assert result.dialogues[0].needs_review is True
    assert result.dialogues[0].review_reason == "some_prior_reason"


@pytest.mark.asyncio
async def test_only_handwritten_dialogues_flagged() -> None:
    """Mixed state: only handwritten ones get needs_review=True."""
    d1 = _dialogue(handwritten=True)
    d2 = _dialogue(handwritten=False)
    d3 = _dialogue(handwritten=True)
    result = await HandwrittenStage().run(_make_state([d1, d2, d3]))
    flagged = [d.needs_review for d in result.dialogues]
    assert flagged == [True, False, True]


@pytest.mark.asyncio
async def test_dialogues_count_unchanged() -> None:
    """Stage never adds or removes dialogues."""
    dialogues = [_dialogue(handwritten=i % 2 == 0) for i in range(5)]
    result = await HandwrittenStage().run(_make_state(dialogues))
    assert len(result.dialogues) == 5
