"""Tests for OcrReprocessStage (V2-AG-04)."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from PIL import Image

from agent.providers.ocr import OcrResult
from agent.stages.ocr_reprocess import OcrReprocessStage, _enhance_region
from agent.state import BBox, DialogueState, PageAnalysisState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    dialogues: list[DialogueState],
    tmp_path: pytest.TempPathFactory | None = None,
    img_path: str = "fake.png",
) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path=img_path,
        page_width=750,
        page_height=1200,
        dialogues=dialogues,
    )


def _make_dialogue(
    ocr_confidence: float | None = None,
    needs_review: bool = False,
    review_reason: str | None = None,
) -> DialogueState:
    d = DialogueState(id=str(uuid4()), bbox=BBox(x=0, y=0, width=100, height=100))
    d.original = "テスト"
    d.ocr_confidence = ocr_confidence
    d.needs_review = needs_review
    d.review_reason = review_reason
    return d


def _mock_provider(ocr_result: OcrResult) -> MagicMock:
    provider = MagicMock()
    provider.ocr_region.return_value = ocr_result
    return provider


def _write_white_image(path: pytest.Path) -> None:
    img = Image.new("RGB", (750, 1200), color=(255, 255, 255))
    img.save(str(path))


# ---------------------------------------------------------------------------
# Unit: _enhance_region
# ---------------------------------------------------------------------------


def test_enhance_region_returns_rgb_image() -> None:
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    result = _enhance_region(img)
    assert result.mode == "RGB"
    assert result.size == (100, 100)


def test_enhance_region_dark_pixel_becomes_black() -> None:
    img = Image.new("RGB", (10, 10), color=(50, 50, 50))
    result = _enhance_region(img)
    r, g, b = result.getpixel((5, 5))  # type: ignore[misc]
    assert r == 0 and g == 0 and b == 0


def test_enhance_region_light_pixel_becomes_white() -> None:
    img = Image.new("RGB", (10, 10), color=(250, 250, 250))
    result = _enhance_region(img)
    r, g, b = result.getpixel((5, 5))  # type: ignore[misc]
    assert r == 255 and g == 255 and b == 255


# ---------------------------------------------------------------------------
# Stage behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage_skips_high_confidence_dialogues(tmp_path: pytest.TempPathFactory) -> None:
    image_path = tmp_path / "page.png"  # type: ignore[operator]
    _write_white_image(image_path)

    high_conf = _make_dialogue(ocr_confidence=0.95, needs_review=False)
    provider = _mock_provider(OcrResult(original="高", ocr_confidence=0.99))

    stage = OcrReprocessStage(provider=provider, threshold=0.80)
    state = _make_state([high_conf], img_path=str(image_path))
    await stage.run(state)

    provider.ocr_region.assert_not_called()
    assert state.dialogues[0].original == "テスト"


@pytest.mark.asyncio
async def test_stage_updates_when_confidence_improves(tmp_path: pytest.TempPathFactory) -> None:
    image_path = tmp_path / "page.png"  # type: ignore[operator]
    _write_white_image(image_path)

    low_conf = _make_dialogue(
        ocr_confidence=0.50, needs_review=True, review_reason="low_ocr_confidence"
    )
    new_result = OcrResult(original="改善", ocr_confidence=0.90)
    provider = _mock_provider(new_result)

    stage = OcrReprocessStage(provider=provider, threshold=0.80)
    state = _make_state([low_conf], img_path=str(image_path))
    await stage.run(state)

    d = state.dialogues[0]
    assert d.original == "改善"
    assert d.ocr_confidence == 0.90
    assert d.needs_review is False


@pytest.mark.asyncio
async def test_stage_keeps_original_when_confidence_does_not_improve(
    tmp_path: pytest.TempPathFactory,
) -> None:
    image_path = tmp_path / "page.png"  # type: ignore[operator]
    _write_white_image(image_path)

    low_conf = _make_dialogue(
        ocr_confidence=0.60, needs_review=True, review_reason="low_ocr_confidence"
    )
    low_conf.original = "元テキスト"
    worse_result = OcrResult(original="悪化", ocr_confidence=0.50)
    provider = _mock_provider(worse_result)

    stage = OcrReprocessStage(provider=provider, threshold=0.80)
    state = _make_state([low_conf], img_path=str(image_path))
    await stage.run(state)

    d = state.dialogues[0]
    assert d.original == "元テキスト"
    assert d.ocr_confidence == 0.60
    assert d.needs_review is True


@pytest.mark.asyncio
async def test_stage_clears_needs_review_when_above_threshold(
    tmp_path: pytest.TempPathFactory,
) -> None:
    image_path = tmp_path / "page.png"  # type: ignore[operator]
    _write_white_image(image_path)

    d = _make_dialogue(ocr_confidence=0.65, needs_review=True, review_reason="low_ocr_confidence")
    provider = _mock_provider(OcrResult(original="OK", ocr_confidence=0.85))

    stage = OcrReprocessStage(provider=provider, threshold=0.80)
    state = _make_state([d], img_path=str(image_path))
    await stage.run(state)

    assert state.dialogues[0].needs_review is False


@pytest.mark.asyncio
async def test_stage_keeps_needs_review_when_still_below_threshold(
    tmp_path: pytest.TempPathFactory,
) -> None:
    image_path = tmp_path / "page.png"  # type: ignore[operator]
    _write_white_image(image_path)

    d = _make_dialogue(ocr_confidence=0.55, needs_review=True, review_reason="low_ocr_confidence")
    provider = _mock_provider(OcrResult(original="まだ低い", ocr_confidence=0.72))

    stage = OcrReprocessStage(provider=provider, threshold=0.80)
    state = _make_state([d], img_path=str(image_path))
    await stage.run(state)

    assert state.dialogues[0].needs_review is True


@pytest.mark.asyncio
async def test_stage_ignores_non_ocr_needs_review(tmp_path: pytest.TempPathFactory) -> None:
    image_path = tmp_path / "page.png"  # type: ignore[operator]
    _write_white_image(image_path)

    d = _make_dialogue(
        ocr_confidence=0.60, needs_review=True, review_reason="llm_translation_failed"
    )
    provider = _mock_provider(OcrResult(original="スキップ", ocr_confidence=0.99))

    stage = OcrReprocessStage(provider=provider, threshold=0.80)
    state = _make_state([d], img_path=str(image_path))
    await stage.run(state)

    provider.ocr_region.assert_not_called()
    assert state.dialogues[0].original == "テスト"


@pytest.mark.asyncio
async def test_stage_noop_on_empty_state(tmp_path: pytest.TempPathFactory) -> None:
    image_path = tmp_path / "page.png"  # type: ignore[operator]
    _write_white_image(image_path)
    provider = _mock_provider(OcrResult(original="", ocr_confidence=1.0))

    stage = OcrReprocessStage(provider=provider, threshold=0.80)
    state = _make_state([], img_path=str(image_path))
    result = await stage.run(state)

    assert result.dialogues == []
    provider.ocr_region.assert_not_called()


def test_stage_name() -> None:
    stage = OcrReprocessStage(provider=MagicMock(), threshold=0.80)
    assert stage.name == "ocr_reprocess"
