"""Tests for ClassificationProvider (heuristic) and ClassificationStage (F4-AG-02)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from PIL import Image, ImageDraw

from agent.providers.classification import (
    ClassificationResult,
    HeuristicClassificationProvider,
)
from agent.stages.classification import ClassificationStage
from agent.state import BBox, DialogueState, PageAnalysisState

# ---------------------------------------------------------------------------
# Helpers — synthetic images
# ---------------------------------------------------------------------------


def _make_bubble_image(
    img_size: tuple[int, int] = (200, 200),
    bubble_bbox: tuple[int, int, int, int] = (60, 60, 120, 120),
    bg_color: int = 80,
    bubble_interior: int = 250,
    border_width: int = 3,
    border_color: int = 20,
) -> Image.Image:
    """Create a grayscale image with a white oval bubble on a dark background."""
    img = Image.new("L", img_size, color=bg_color)
    draw = ImageDraw.Draw(img)
    # Bubble border
    draw.ellipse(bubble_bbox, fill=border_color)
    # Bubble interior (shrink by border_width)
    x1, y1, x2, y2 = bubble_bbox
    inner = (x1 + border_width, y1 + border_width, x2 - border_width, y2 - border_width)
    draw.ellipse(inner, fill=bubble_interior)
    return img.convert("RGB")


def _make_plain_text_image(
    img_size: tuple[int, int] = (200, 200),
    text_bbox: tuple[int, int, int, int] = (60, 60, 120, 120),
    bg_color: int = 100,
) -> Image.Image:
    """Create an image with a non-white region (text on artwork background)."""
    img = Image.new("L", img_size, color=bg_color)
    return img.convert("RGB")


def _bbox_from_tuple(t: tuple[int, int, int, int]) -> BBox:
    x1, y1, x2, y2 = t
    return BBox(x=x1, y=y1, width=x2 - x1, height=y2 - y1)


# ---------------------------------------------------------------------------
# Unit tests: HeuristicClassificationProvider
# ---------------------------------------------------------------------------


def test_heuristic_classifies_bubble_as_hash() -> None:
    """Bright interior + dark border → '#'."""
    bbox_tuple = (50, 50, 150, 150)
    img = _make_bubble_image(bubble_bbox=bbox_tuple, bg_color=60, bubble_interior=245)
    provider = HeuristicClassificationProvider(padding=15)
    result = provider.classify(img, _bbox_from_tuple(bbox_tuple))
    assert result.type == "#", f"Expected '#', got '{result.type}' (confidence={result.confidence})"


def test_heuristic_classifies_dark_background_as_dollar() -> None:
    """Uniform dark background → '$'."""
    img = _make_plain_text_image(bg_color=80)
    bbox_tuple = (60, 60, 120, 120)
    provider = HeuristicClassificationProvider()
    result = provider.classify(img, _bbox_from_tuple(bbox_tuple))
    assert result.type == "$"


def test_heuristic_confidence_is_in_range() -> None:
    """Confidence must be in [0.0, 1.0]."""
    img = _make_bubble_image()
    bbox_tuple = (60, 60, 120, 120)
    provider = HeuristicClassificationProvider()
    result = provider.classify(img, _bbox_from_tuple(bbox_tuple))
    assert 0.0 <= result.confidence <= 1.0


def test_heuristic_returns_classification_result() -> None:
    img = _make_bubble_image()
    provider = HeuristicClassificationProvider()
    result = provider.classify(img, BBox(x=60, y=60, width=60, height=60))
    assert isinstance(result, ClassificationResult)
    assert result.type in ("#", "$")


def test_heuristic_uniform_white_is_ambiguous_dollar() -> None:
    """A fully white image has no contrast — should be '$' (no bubble border detected)."""
    img = Image.new("RGB", (200, 200), (255, 255, 255))
    provider = HeuristicClassificationProvider()
    result = provider.classify(img, BBox(x=60, y=60, width=80, height=80))
    # All white: no border contrast → $
    assert result.type == "$"


def test_heuristic_out_of_bounds_bbox_does_not_crash() -> None:
    img = Image.new("RGB", (100, 100), (200, 200, 200))
    provider = HeuristicClassificationProvider(padding=30)
    result = provider.classify(img, BBox(x=90, y=90, width=50, height=50))
    assert result.type in ("#", "$")


# ---------------------------------------------------------------------------
# Integration: ClassificationStage
# ---------------------------------------------------------------------------


def _make_state_with_image(
    image: Image.Image,
    bbox: BBox,
    tmp_path: str,
) -> tuple[PageAnalysisState, str]:
    import os  # noqa: PLC0415

    path = os.path.join(tmp_path, "test_page.png")
    image.save(path)
    d = DialogueState(id=str(uuid4()), bbox=bbox)
    state = PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path=path,
        dialogues=[d],
    )
    return state, path


@pytest.mark.asyncio
async def test_stage_sets_type_on_all_dialogues(tmp_path: str) -> None:
    bbox = BBox(x=50, y=50, width=100, height=100)
    img = _make_bubble_image(bubble_bbox=(50, 50, 150, 150), bg_color=60)
    state, _ = _make_state_with_image(img, bbox, str(tmp_path))

    stage = ClassificationStage()
    result = await stage.run(state)

    assert all(d.type is not None for d in result.dialogues)
    assert all(d.type_confidence is not None for d in result.dialogues)


@pytest.mark.asyncio
async def test_stage_bubble_image_classified_as_hash(tmp_path: str) -> None:
    bbox = BBox(x=40, y=40, width=120, height=120)
    img = _make_bubble_image(
        img_size=(200, 200),
        bubble_bbox=(40, 40, 160, 160),
        bg_color=50,
        bubble_interior=248,
        border_width=4,
    )
    state, _ = _make_state_with_image(img, bbox, str(tmp_path))

    stage = ClassificationStage()
    result = await stage.run(state)

    assert result.dialogues[0].type == "#"


@pytest.mark.asyncio
async def test_stage_noop_on_empty(tmp_path: str) -> None:
    state = PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path=str(tmp_path / "noop.png"),  # type: ignore[operator]
        dialogues=[],
    )
    result = await ClassificationStage().run(state)
    assert result.dialogues == []
