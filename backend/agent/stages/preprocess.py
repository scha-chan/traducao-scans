"""PreprocessStage: EXIF normalization, resize and RGB conversion (F3-AG-02)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

from PIL import Image, ImageOps

from agent.stage import Stage
from agent.state import PageAnalysisState

_MAX_SIDE = 4096  # pixels; images larger than this are scaled down proportionally


class PreprocessStage(Stage):
    """Normalize EXIF orientation, resize to at most MAX_SIDE px and convert to RGB.

    Writes the preprocessed image to a ``_processed/`` folder beside the original
    and updates ``state.image_path`` so downstream stages see the corrected file.
    """

    def __init__(self, max_side: int = _MAX_SIDE) -> None:
        self._max_side = max_side

    @property
    def name(self) -> str:
        return "preprocess"

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        loop = asyncio.get_event_loop()
        new_path = await loop.run_in_executor(None, self._process, state.image_path, state.run_id)
        state.image_path = new_path
        return state

    def _process(self, image_path: str, run_id: UUID) -> str:
        src: Image.Image = Image.open(image_path)

        # Correct EXIF orientation (e.g. phone photos rotated 90°)
        # exif_transpose returns Image | None; fall back to src when no-op
        img: Image.Image = ImageOps.exif_transpose(src) or src

        # Ensure RGB (no alpha channel, no palette mode)
        img = img.convert("RGB")

        # Scale down if either dimension exceeds the limit
        w, h = img.size
        if max(w, h) > self._max_side:
            scale = self._max_side / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        out_dir = Path(image_path).parent / "_processed"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / f"{run_id}_pre.png"
        img.save(str(out_path), format="PNG")
        return str(out_path)
