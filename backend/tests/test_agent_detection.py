"""Unit tests for DetectionStage (F3-AG-03)."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from agent.providers.detection import DetectionProvider
from agent.stages.detection import DetectionStage
from agent.state import BBox, DialogueState, PageAnalysisState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(image_path: str) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path=image_path,
    )


def _save_rgb_png(path: Path, size: tuple[int, int] = (200, 100)) -> None:
    Image.new("RGB", size, color=(200, 200, 200)).save(str(path), "PNG")


class _FakeProvider:
    """Returns a fixed list of bboxes regardless of the image."""

    def __init__(self, bboxes: list[BBox]) -> None:
        self._bboxes = bboxes

    def detect(self, image_path: str) -> list[BBox]:
        return list(self._bboxes)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_detection_leaves_dialogues_empty(tmp_path: Path) -> None:
    src = tmp_path / "page.png"
    _save_rgb_png(src)
    state = _make_state(str(src))

    stage = DetectionStage(provider=_FakeProvider([]))
    result = await stage.run(state)

    assert result.dialogues == []


@pytest.mark.asyncio
async def test_detected_bboxes_populate_dialogues(tmp_path: Path) -> None:
    src = tmp_path / "page.png"
    _save_rgb_png(src, (750, 1200))
    bboxes = [
        BBox(x=100, y=200, width=50, height=80),
        BBox(x=400, y=300, width=60, height=100),
    ]
    state = _make_state(str(src))

    stage = DetectionStage(provider=_FakeProvider(bboxes))
    result = await stage.run(state)

    assert len(result.dialogues) == 2
    assert result.dialogues[0].bbox == bboxes[0]
    assert result.dialogues[1].bbox == bboxes[1]


@pytest.mark.asyncio
async def test_each_dialogue_gets_unique_id(tmp_path: Path) -> None:
    src = tmp_path / "page.png"
    _save_rgb_png(src)
    bboxes = [BBox(x=0, y=0, width=10, height=10)] * 3
    state = _make_state(str(src))

    stage = DetectionStage(provider=_FakeProvider(bboxes))
    result = await stage.run(state)

    ids = [d.id for d in result.dialogues]
    assert len(set(ids)) == 3, "Each DialogueState must have a unique id"


@pytest.mark.asyncio
async def test_dialogues_have_no_original_text(tmp_path: Path) -> None:
    """original is populated by the OCR stage (F3-AG-04), not detection."""
    src = tmp_path / "page.png"
    _save_rgb_png(src)
    state = _make_state(str(src))

    stage = DetectionStage(provider=_FakeProvider([BBox(x=0, y=0, width=20, height=20)]))
    result = await stage.run(state)

    assert result.dialogues[0].original is None


@pytest.mark.asyncio
async def test_stage_name_is_detection() -> None:
    stage = DetectionStage(provider=_FakeProvider([]))
    assert stage.name == "detection"


@pytest.mark.asyncio
async def test_previous_dialogues_replaced(tmp_path: Path) -> None:
    """DetectionStage overwrites any pre-existing dialogues in the state."""
    src = tmp_path / "page.png"
    _save_rgb_png(src)
    state = _make_state(str(src))

    # Seed state with a stale dialogue
    state.dialogues = [DialogueState(id="old", bbox=BBox(x=0, y=0, width=5, height=5))]

    new_bbox = BBox(x=10, y=10, width=30, height=40)
    stage = DetectionStage(provider=_FakeProvider([new_bbox]))
    result = await stage.run(state)

    assert len(result.dialogues) == 1
    assert result.dialogues[0].bbox == new_bbox


def test_fake_provider_satisfies_protocol() -> None:
    """Smoke-test that _FakeProvider structurally matches DetectionProvider."""
    assert isinstance(_FakeProvider([]), DetectionProvider)
