"""DetectionProvider protocol and ComicTextDetectorProvider (F3-AG-03).

Model: comic-text-detector ONNX (dmMaze/comic-text-detector on GitHub)
Download the model weights and set CTD_MODEL_PATH to point to the .onnx file.

Quick-start (Linux/Mac):
    pip install onnxruntime opencv-python-headless
    wget -P models/ https://github.com/dmMaze/comic-text-detector/releases/download/v2/comictextdetector.pt.onnx

Environment variable:
    CTD_MODEL_PATH   path to comictextdetector.pt.onnx  (default: models/comictextdetector.pt.onnx)
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from agent.state import BBox

# Input size expected by the comic-text-detector ONNX model
_CTD_INPUT_SIZE = 1024


@runtime_checkable
class DetectionProvider(Protocol):
    """Contract for a text-region detector."""

    def detect(self, image_path: str) -> list[BBox]:
        """Detect text regions and return bboxes in image pixel coordinates."""
        ...


class ComicTextDetectorProvider:
    """Text region detector backed by the comic-text-detector ONNX model.

    Raises ``RuntimeError`` on construction if the model file is not found so
    the error surfaces at startup rather than on the first inference call.
    """

    def __init__(self, model_path: str | None = None) -> None:
        import cv2  # noqa: PLC0415  (heavy import; kept lazy)
        import numpy as np  # noqa: PLC0415
        import onnxruntime as ort  # noqa: PLC0415

        self._cv2 = cv2
        self._np = np

        path = model_path or os.environ.get("CTD_MODEL_PATH", "models/comictextdetector.pt.onnx")
        if not os.path.isfile(path):
            raise RuntimeError(
                f"comic-text-detector model not found at '{path}'. "
                "Download comictextdetector.pt.onnx and set CTD_MODEL_PATH. "
                "See backend/agent/providers/detection.py for instructions."
            )
        self._session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        self._input_name: str = self._session.get_inputs()[0].name

    def detect(self, image_path: str) -> list[BBox]:
        cv2 = self._cv2
        np = self._np

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError(f"Could not read image: {image_path}")

        orig_h, orig_w = img_bgr.shape[:2]
        scale = _CTD_INPUT_SIZE / max(orig_h, orig_w)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)

        resized = cv2.resize(img_bgr, (new_w, new_h))
        # Pad to square
        canvas = np.zeros((_CTD_INPUT_SIZE, _CTD_INPUT_SIZE, 3), dtype=np.uint8)
        canvas[:new_h, :new_w] = resized

        # NCHW float32 normalised to [0, 1]
        inp = canvas.astype(np.float32) / 255.0
        inp = np.transpose(inp, (2, 0, 1))[np.newaxis]

        outputs = self._session.run(None, {self._input_name: inp})
        # outputs[0]: (1, N, 4) or (N, 4) xywh in [0, input_size] space
        boxes_raw = np.array(outputs[0]).reshape(-1, 4)

        bboxes: list[BBox] = []
        for row in boxes_raw:
            cx, cy, bw, bh = (float(v) for v in row)
            # Convert from input-space xywh-centre → original-image xywh-topleft
            x = int((cx - bw / 2) / scale)
            y = int((cy - bh / 2) / scale)
            w = int(bw / scale)
            h = int(bh / scale)
            # Clamp to image bounds
            x = max(0, min(x, orig_w - 1))
            y = max(0, min(y, orig_h - 1))
            w = max(1, min(w, orig_w - x))
            h = max(1, min(h, orig_h - y))
            bboxes.append(BBox(x=x, y=y, width=w, height=h))

        return bboxes
