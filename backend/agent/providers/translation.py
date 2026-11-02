"""TranslationProvider protocol and concrete providers (F3-AG-08).

Translation pipeline: JA → EN → PT in two steps.

Providers:
    MarianTranslationProvider   — local inference, no API token needed
                                  Install: pip install transformers sentencepiece torch
                                  Models downloaded once (~900 MB) to ~/.cache/huggingface/

    HuggingFaceTranslationProvider — remote HF Inference API (requires HF_API_TOKEN)

Models (overridable via env vars):
    TRANSLATION_JA_EN_MODEL  (default: Helsinki-NLP/opus-mt-ja-en)
    TRANSLATION_EN_PT_MODEL  (default: Helsinki-NLP/opus-mt-tc-big-en-pt)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import httpx

_HF_INFERENCE_BASE = "https://api-inference.huggingface.co/models"

_DEFAULT_JA_EN_MODEL = "Helsinki-NLP/opus-mt-ja-en"
_DEFAULT_EN_PT_MODEL = "Helsinki-NLP/opus-mt-tc-big-en-pt"


@dataclass
class TranslationResult:
    translation: str
    observation: str = ""
    relevance: int = 3


@runtime_checkable
class TranslationProvider(Protocol):
    """Contract for a per-dialogue translation provider."""

    def translate(self, text: str) -> TranslationResult:
        """Translate *text* (Japanese) to Portuguese and return a TranslationResult."""
        ...


def _hf_translate(text: str, model: str, token: str) -> str:
    """Call the HuggingFace Inference API for a single translation step."""
    url = f"{_HF_INFERENCE_BASE}/{model}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = httpx.post(url, json={"inputs": text}, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # Response shape: [{"translation_text": "..."}]
    if isinstance(data, list) and data:
        return str(data[0].get("translation_text", ""))
    return ""


class HuggingFaceTranslationProvider:
    """Two-step JA→EN→PT translation using HuggingFace Inference API.

    Requires ``HF_API_TOKEN`` environment variable or explicit *api_token*.
    """

    def __init__(
        self,
        api_token: str | None = None,
        ja_en_model: str | None = None,
        en_pt_model: str | None = None,
    ) -> None:
        token = api_token or os.environ.get("HF_API_TOKEN", "")
        if not token:
            raise ValueError(
                "HuggingFace API token is required. "
                "Set the HF_API_TOKEN environment variable or pass api_token=."
            )
        self._token = token
        self._ja_en_model: str = (
            ja_en_model or os.environ.get("TRANSLATION_JA_EN_MODEL") or _DEFAULT_JA_EN_MODEL
        )
        self._en_pt_model: str = (
            en_pt_model or os.environ.get("TRANSLATION_EN_PT_MODEL") or _DEFAULT_EN_PT_MODEL
        )

    def translate(self, text: str) -> TranslationResult:
        en_text = _hf_translate(text, self._ja_en_model, self._token)
        pt_text = _hf_translate(en_text, self._en_pt_model, self._token)
        return TranslationResult(translation=pt_text, observation="", relevance=3)


class MarianTranslationProvider:
    """Two-step JA→EN→PT translation using local MarianMT models.

    Models are downloaded from HuggingFace on first use and cached in
    ``~/.cache/huggingface/``.  No API token required after download.

    Install: ``pip install transformers sentencepiece torch``
    """

    def __init__(
        self,
        ja_en_model: str | None = None,
        en_pt_model: str | None = None,
    ) -> None:
        try:
            from transformers import MarianMTModel, MarianTokenizer  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "transformers and sentencepiece are required for MarianTranslationProvider. "
                "Install them with: pip install transformers sentencepiece torch"
            ) from exc

        ja_en: str = (
            ja_en_model or os.environ.get("TRANSLATION_JA_EN_MODEL") or _DEFAULT_JA_EN_MODEL
        )
        en_pt: str = (
            en_pt_model or os.environ.get("TRANSLATION_EN_PT_MODEL") or _DEFAULT_EN_PT_MODEL
        )

        self._tok_ja_en: Any = MarianTokenizer.from_pretrained(ja_en)
        self._mod_ja_en: Any = MarianMTModel.from_pretrained(ja_en)
        self._tok_en_pt: Any = MarianTokenizer.from_pretrained(en_pt)
        self._mod_en_pt: Any = MarianMTModel.from_pretrained(en_pt)

    def _run(self, tok: Any, mod: Any, text: str) -> str:  # noqa: ANN401
        tokens = tok([text], return_tensors="pt", padding=True)
        ids = mod.generate(**tokens)
        return str(tok.decode(ids[0], skip_special_tokens=True))

    def translate(self, text: str) -> TranslationResult:
        en_text = self._run(self._tok_ja_en, self._mod_ja_en, text)
        pt_text = self._run(self._tok_en_pt, self._mod_en_pt, en_text)
        return TranslationResult(translation=pt_text, observation="", relevance=3)
