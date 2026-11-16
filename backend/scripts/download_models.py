"""Download ML models to backend/models/ for offline use inside Docker.

Usage:
    python backend/scripts/download_models.py

Models downloaded:
    kha-white/manga-ocr-base  → backend/models/manga-ocr/
    Helsinki-NLP/opus-mt-ja-en          → backend/models/opus-mt-ja-en/
    Helsinki-NLP/opus-mt-tc-big-en-pt   → backend/models/opus-mt-tc-big-en-pt/
"""

from __future__ import annotations

import sys
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"

MODELS = [
    ("manga_ocr", "kha-white/manga-ocr-base", MODELS_DIR / "manga-ocr"),
    ("marian", "Helsinki-NLP/opus-mt-ja-en", MODELS_DIR / "opus-mt-ja-en"),
    ("marian", "Helsinki-NLP/opus-mt-tc-big-en-pt", MODELS_DIR / "opus-mt-tc-big-en-pt"),
]


def _download_marian(hf_id: str, dest: Path) -> None:
    from transformers import MarianMTModel, MarianTokenizer

    print("  tokenizer…")
    tok = MarianTokenizer.from_pretrained(hf_id)
    tok.save_pretrained(str(dest))

    print("  model…")
    mod = MarianMTModel.from_pretrained(hf_id)
    mod.save_pretrained(str(dest))


def _download_manga_ocr(hf_id: str, dest: Path) -> None:
    from transformers import AutoFeatureExtractor, AutoTokenizer, VisionEncoderDecoderModel

    print("  tokenizer…")
    tok = AutoTokenizer.from_pretrained(hf_id)
    tok.save_pretrained(str(dest))

    print("  feature extractor…")
    fe = AutoFeatureExtractor.from_pretrained(hf_id)
    fe.save_pretrained(str(dest))

    print("  model…")
    mod = VisionEncoderDecoderModel.from_pretrained(hf_id)
    mod.save_pretrained(str(dest))


def main() -> None:
    MODELS_DIR.mkdir(exist_ok=True)

    for kind, hf_id, dest in MODELS:
        if dest.exists():
            print(f"[skip] {hf_id} → {dest.name}/ (already exists)")
            continue

        print(f"[download] {hf_id} → {dest.name}/")
        dest.mkdir(parents=True, exist_ok=True)
        try:
            if kind == "marian":
                _download_marian(hf_id, dest)
            else:
                _download_manga_ocr(hf_id, dest)
            print(f"[ok] {dest.name}/")
        except Exception as exc:
            print(f"[error] {hf_id}: {exc}", file=sys.stderr)
            raise


if __name__ == "__main__":
    main()
