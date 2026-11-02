"""TranslationProvider protocol and HuggingFaceTranslationProvider (F3-AG-08).

Translation pipeline: JA → EN → PT via HuggingFace Inference API.

Models (overridable via env vars):
    TRANSLATION_JA_EN_MODEL  (default: Helsinki-NLP/opus-mt-ja-en)
    TRANSLATION_EN_PT_MODEL  (default: Helsinki-NLP/opus-mt-tc-big-en-pt)

Environment variable:
    HF_API_TOKEN  — HuggingFace API token (required for Inference API)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

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
        self._ja_en_model = ja_en_model or os.environ.get(
            "TRANSLATION_JA_EN_MODEL", _DEFAULT_JA_EN_MODEL
        )
        self._en_pt_model = en_pt_model or os.environ.get(
            "TRANSLATION_EN_PT_MODEL", _DEFAULT_EN_PT_MODEL
        )

    def translate(self, text: str) -> TranslationResult:
        en_text = _hf_translate(text, self._ja_en_model, self._token)
        pt_text = _hf_translate(en_text, self._en_pt_model, self._token)
        return TranslationResult(translation=pt_text, observation="", relevance=3)
