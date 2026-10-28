"""Unit tests for PreprocessStage (F3-AG-02)."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from agent.stages.preprocess import PreprocessStage
from agent.state import PageAnalysisState


def _make_state(image_path: str) -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path=image_path,
    )


def _save_rgb_jpeg(path: Path, size: tuple[int, int] = (200, 100)) -> None:
    Image.new("RGB", size, color=(255, 0, 0)).save(str(path), "JPEG")


def _save_rgba_png(path: Path, size: tuple[int, int] = (100, 100)) -> None:
    Image.new("RGBA", size, color=(0, 255, 0, 128)).save(str(path), "PNG")


def _save_jpeg_with_orientation(path: Path, width: int, height: int, orientation: int) -> None:
    """Save a JPEG with the given EXIF orientation tag."""
    img = Image.new("RGB", (width, height), color=(0, 0, 255))
    exif = img.getexif()
    exif[0x0112] = orientation  # 0x0112 = Orientation tag
    data = io.BytesIO()
    img.save(data, "jpeg", exif=exif.tobytes())
    path.write_bytes(data.getvalue())


@pytest.mark.asyncio
async def test_rgb_image_passes_through(tmp_path: Path) -> None:
    src = tmp_path / "page.jpg"
    _save_rgb_jpeg(src, (200, 100))
    state = _make_state(str(src))

    stage = PreprocessStage()
    result = await stage.run(state)

    assert result.image_path != str(src)
    out = Image.open(result.image_path)
    assert out.mode == "RGB"
    assert out.size == (200, 100)


@pytest.mark.asyncio
async def test_rgba_converted_to_rgb(tmp_path: Path) -> None:
    src = tmp_path / "page.png"
    _save_rgba_png(src, (100, 100))
    state = _make_state(str(src))

    result = await PreprocessStage().run(state)

    out = Image.open(result.image_path)
    assert out.mode == "RGB"


@pytest.mark.asyncio
async def test_large_image_is_resized(tmp_path: Path) -> None:
    src = tmp_path / "big.jpg"
    Image.new("RGB", (6000, 4000)).save(str(src), "JPEG")
    state = _make_state(str(src))

    result = await PreprocessStage(max_side=4096).run(state)

    out = Image.open(result.image_path)
    assert max(out.size) == 4096
    # Aspect ratio preserved
    assert abs(out.size[0] / out.size[1] - 6000 / 4000) < 0.02


@pytest.mark.asyncio
async def test_small_image_not_upscaled(tmp_path: Path) -> None:
    src = tmp_path / "small.jpg"
    Image.new("RGB", (800, 600)).save(str(src), "JPEG")
    state = _make_state(str(src))

    result = await PreprocessStage(max_side=4096).run(state)

    out = Image.open(result.image_path)
    assert out.size == (800, 600)


@pytest.mark.asyncio
async def test_exif_orientation_6_rotates_image(tmp_path: Path) -> None:
    """Orientation 6 = 90° CW: a 200×100 landscape becomes 100×200 portrait."""
    src = tmp_path / "rotated.jpg"
    _save_jpeg_with_orientation(src, width=200, height=100, orientation=6)

    state = _make_state(str(src))
    result = await PreprocessStage().run(state)

    out = Image.open(result.image_path)
    # After EXIF transpose: width and height are swapped
    assert out.size == (100, 200)


@pytest.mark.asyncio
async def test_output_written_to_processed_subdir(tmp_path: Path) -> None:
    src = tmp_path / "page.jpg"
    _save_rgb_jpeg(src)
    state = _make_state(str(src))

    result = await PreprocessStage().run(state)

    out_path = Path(result.image_path)
    assert out_path.parent.name == "_processed"
    assert out_path.exists()


@pytest.mark.asyncio
async def test_image_path_updated_in_state(tmp_path: Path) -> None:
    src = tmp_path / "page.jpg"
    _save_rgb_jpeg(src)
    original_path = str(src)
    state = _make_state(original_path)

    result = await PreprocessStage().run(state)

    assert result.image_path != original_path
