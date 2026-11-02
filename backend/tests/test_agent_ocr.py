"""Unit tests for OcrStage (F3-AG-04)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from uuid import uuid4

import pytest
from PIL import Image

from agent.providers.ocr import OcrProvider, OcrResult, _orientation_from_bbox
from agent.stages.ocr import OcrStage
from agent.state import BBox, DialogueState, PageAnalysisState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(image_path: str, dialogues: list[DialogueState] | None = None) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path=image_path,
        dialogues=dialogues or [],
    )


def _save_rgb_png(path: Path, size: tuple[int, int] = (200, 100)) -> None:
    Image.new("RGB", size, color=(200, 200, 200)).save(str(path), "PNG")


def _dialogue(
    x: int = 0, y: int = 0, w: int = 50, h: int = 80, *, text: str = "きめたよ"
) -> DialogueState:
    return DialogueState(id=str(uuid4()), bbox=BBox(x=x, y=y, width=w, height=h))


class _FakeOcrProvider:
    """Returns a fixed OcrResult for every region."""

    def __init__(
        self,
        text: str = "きめたよ!",
        lines: list[str] | None = None,
        orientation: Literal["VERTICAL", "HORIZONTAL"] = "VERTICAL",
        confidence: float = 0.95,
    ) -> None:
        self._result = OcrResult(
            original=text,
            lines=lines if lines is not None else [text],
            orientation=orientation,
            ocr_confidence=confidence,
        )

    def ocr_region(self, region: Image.Image, bbox: BBox) -> OcrResult:
        return self._result


# ---------------------------------------------------------------------------
# Tests — OcrStage contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_dialogues_returns_state_unchanged(tmp_path: Path) -> None:
    src = tmp_path / "page.png"
    _save_rgb_png(src, (200, 200))
    state = _make_state(str(src))

    result = await OcrStage(provider=_FakeOcrProvider()).run(state)

    assert result.dialogues == []


@pytest.mark.asyncio
async def test_original_populated_for_each_dialogue(tmp_path: Path) -> None:
    src = tmp_path / "page.png"
    _save_rgb_png(src, (200, 200))
    dialogues = [_dialogue(0, 0, 50, 80), _dialogue(100, 0, 50, 80)]
    state = _make_state(str(src), dialogues)

    result = await OcrStage(provider=_FakeOcrProvider(text="おれも")).run(state)

    assert all(d.original == "おれも" for d in result.dialogues)


@pytest.mark.asyncio
async def test_lines_populated(tmp_path: Path) -> None:
    src = tmp_path / "page.png"
    _save_rgb_png(src, (200, 200))
    state = _make_state(str(src), [_dialogue()])

    result = await OcrStage(
        provider=_FakeOcrProvider(text="誰よりも", lines=["誰よりも", "何よりも"])
    ).run(state)

    assert result.dialogues[0].lines == ["誰よりも", "何よりも"]


@pytest.mark.asyncio
async def test_orientation_set(tmp_path: Path) -> None:
    src = tmp_path / "page.png"
    _save_rgb_png(src, (200, 200))
    state = _make_state(str(src), [_dialogue()])

    result = await OcrStage(provider=_FakeOcrProvider(orientation="HORIZONTAL")).run(state)

    assert result.dialogues[0].orientation == "HORIZONTAL"


@pytest.mark.asyncio
async def test_ocr_confidence_set(tmp_path: Path) -> None:
    src = tmp_path / "page.png"
    _save_rgb_png(src, (200, 200))
    state = _make_state(str(src), [_dialogue()])

    result = await OcrStage(provider=_FakeOcrProvider(confidence=0.87)).run(state)

    assert result.dialogues[0].ocr_confidence == pytest.approx(0.87)


@pytest.mark.asyncio
async def test_stage_name_is_ocr() -> None:
    assert OcrStage(provider=_FakeOcrProvider()).name == "ocr"


@pytest.mark.asyncio
async def test_bbox_outside_image_is_clamped(tmp_path: Path) -> None:
    """PIL.crop silently clamps coords — stage must not raise for out-of-bounds bbox."""
    src = tmp_path / "page.png"
    _save_rgb_png(src, (100, 100))
    # bbox extends beyond the 100×100 image
    state = _make_state(
        str(src),
        [DialogueState(id=str(uuid4()), bbox=BBox(x=80, y=80, width=100, height=100))],
    )

    result = await OcrStage(provider=_FakeOcrProvider()).run(state)

    assert result.dialogues[0].original is not None


# ---------------------------------------------------------------------------
# Tests — _orientation_from_bbox helper
# ---------------------------------------------------------------------------


def test_tall_region_is_vertical() -> None:
    assert _orientation_from_bbox(BBox(x=0, y=0, width=40, height=120)) == "VERTICAL"


def test_wide_region_is_horizontal() -> None:
    assert _orientation_from_bbox(BBox(x=0, y=0, width=200, height=50)) == "HORIZONTAL"


def test_square_region_is_horizontal() -> None:
    assert _orientation_from_bbox(BBox(x=0, y=0, width=60, height=60)) == "HORIZONTAL"


def test_fake_provider_satisfies_protocol() -> None:
    assert isinstance(_FakeOcrProvider(), OcrProvider)
