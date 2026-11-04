"""Translation cache keyed by hash(dialogue + prompt_version) (F5-AG-05)."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict

from agent.state import DialogueState, TranslationCandidate


def dialogue_cache_key(dialogue: DialogueState, prompt_version: str) -> str:
    """SHA-256 of (original, type, location, ocr_confidence, prompt_version)."""
    payload = {
        "original": dialogue.original or "",
        "type": dialogue.type,
        "location": dialogue.location,
        "ocr_confidence": dialogue.ocr_confidence,
        "prompt_version": prompt_version,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class TranslationCache:
    """In-memory LRU cache keyed by dialogue_cache_key."""

    def __init__(self, max_size: int = 512) -> None:
        self._max_size = max_size
        self._store: OrderedDict[str, list[TranslationCandidate]] = OrderedDict()

    def get(self, key: str) -> list[TranslationCandidate] | None:
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def set(self, key: str, candidates: list[TranslationCandidate]) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        else:
            if len(self._store) >= self._max_size:
                self._store.popitem(last=False)
            self._store[key] = candidates
