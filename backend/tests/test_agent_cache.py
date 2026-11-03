"""Tests for F5-AG-05: translation cache by hash(dialogue + prompt_version)."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from agent.cache import TranslationCache, dialogue_cache_key
from agent.providers.llm_translation import ClaudeTranslationProvider
from agent.state import BBox, DialogueState, PageAnalysisState, TranslationCandidate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dialogue(
    original: str = "こんにちは",
    dialogue_type: str | None = "#",
    location: str | None = "top",
    ocr_confidence: float | None = 0.95,
) -> DialogueState:
    return DialogueState(
        id=str(uuid4()),
        bbox=BBox(x=0, y=0, width=10, height=10),
        original=original,
        type=dialogue_type,  # type: ignore[arg-type]
        location=location,
        ocr_confidence=ocr_confidence,
    )


def _make_state(prompt_version: str = "v1") -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="/tmp/page.png",
        prompt_version=prompt_version,
    )


def _make_candidates() -> list[TranslationCandidate]:
    return [TranslationCandidate(translation="Olá", observation="", relevance=5)]


# ---------------------------------------------------------------------------
# cache_key tests
# ---------------------------------------------------------------------------


def test_cache_key_deterministic() -> None:
    dialogue = _make_dialogue()
    k1 = dialogue_cache_key(dialogue, "v1")
    k2 = dialogue_cache_key(dialogue, "v1")
    assert k1 == k2
    assert len(k1) == 64  # SHA-256 hex


def test_cache_key_differs_on_prompt_version() -> None:
    dialogue = _make_dialogue()
    k_v1 = dialogue_cache_key(dialogue, "v1")
    k_v2 = dialogue_cache_key(dialogue, "v2")
    assert k_v1 != k_v2


def test_cache_key_differs_on_original() -> None:
    d1 = _make_dialogue(original="こんにちは")
    d2 = _make_dialogue(original="さようなら")
    assert dialogue_cache_key(d1, "v1") != dialogue_cache_key(d2, "v1")


# ---------------------------------------------------------------------------
# TranslationCache unit tests
# ---------------------------------------------------------------------------


def test_cache_miss_returns_none() -> None:
    cache = TranslationCache()
    assert cache.get("nonexistent") is None


def test_cache_miss_stores_result() -> None:
    cache = TranslationCache()
    key = "abc123"
    candidates = _make_candidates()
    cache.set(key, candidates)
    result = cache.get(key)
    assert result == candidates


def test_cache_lru_evicts_oldest() -> None:
    cache = TranslationCache(max_size=2)
    c1 = [TranslationCandidate(translation="A", observation="", relevance=1)]
    c2 = [TranslationCandidate(translation="B", observation="", relevance=2)]
    c3 = [TranslationCandidate(translation="C", observation="", relevance=3)]

    cache.set("k1", c1)
    cache.set("k2", c2)
    cache.set("k3", c3)  # evicts k1

    assert cache.get("k1") is None
    assert cache.get("k2") == c2
    assert cache.get("k3") == c3


def test_cache_lru_refreshes_on_access() -> None:
    """Accessing k1 before inserting k3 keeps k1 and evicts k2."""
    cache = TranslationCache(max_size=2)
    c1 = [TranslationCandidate(translation="A", observation="", relevance=1)]
    c2 = [TranslationCandidate(translation="B", observation="", relevance=2)]
    c3 = [TranslationCandidate(translation="C", observation="", relevance=3)]

    cache.set("k1", c1)
    cache.set("k2", c2)
    cache.get("k1")  # refresh k1
    cache.set("k3", c3)  # evicts k2 (oldest after k1 was refreshed)

    assert cache.get("k1") == c1
    assert cache.get("k2") is None
    assert cache.get("k3") == c3


# ---------------------------------------------------------------------------
# ClaudeTranslationProvider integration with cache
# ---------------------------------------------------------------------------


def _build_provider_with_cache(
    cache: TranslationCache,
) -> ClaudeTranslationProvider:
    return ClaudeTranslationProvider(api_key="sk-test", cache=cache)


def _llm_response_json() -> str:
    return '{"candidates": [{"traducao": "Olá", "observacao": "", "relevancia": 5}]}'


def test_cache_hit_skips_llm_call() -> None:
    cache = TranslationCache()
    provider = _build_provider_with_cache(cache)
    dialogue = _make_dialogue()
    state = _make_state("v1")

    llm_json = _llm_response_json()

    with patch.object(provider, "_call_api", return_value=(llm_json, 10, 5)) as mock_api:
        # First call — goes to LLM
        result1 = provider.translate_dialogue(dialogue, "v1", state)
        assert len(result1) == 1
        assert mock_api.call_count == 1

        # Second call — served from cache, LLM not called again
        result2 = provider.translate_dialogue(dialogue, "v1", state)
        assert result2 == result1
        assert mock_api.call_count == 1  # still 1


def test_cache_miss_stores_result_via_provider() -> None:
    cache = TranslationCache()
    provider = _build_provider_with_cache(cache)
    dialogue = _make_dialogue()
    state = _make_state("v1")

    llm_json = _llm_response_json()

    with patch.object(provider, "_call_api", return_value=(llm_json, 10, 5)):
        provider.translate_dialogue(dialogue, "v1", state)

    from agent.cache import dialogue_cache_key  # noqa: PLC0415

    key = dialogue_cache_key(dialogue, "v1")
    cached = cache.get(key)
    assert cached is not None
    assert cached[0].translation == "Olá"


def test_cache_hit_logs_entry() -> None:
    """A cache hit appends an agent_log entry with cache_hit=True."""
    cache = TranslationCache()
    provider = _build_provider_with_cache(cache)
    dialogue = _make_dialogue()
    state = _make_state("v1")

    llm_json = _llm_response_json()

    with patch.object(provider, "_call_api", return_value=(llm_json, 10, 5)):
        provider.translate_dialogue(dialogue, "v1", state)  # populate cache
        initial_log_len = len(state.agent_log)
        provider.translate_dialogue(dialogue, "v1", state)  # cache hit

    new_entries = state.agent_log[initial_log_len:]
    assert any(e.action == "cache_hit" and e.detail.get("cache_hit") is True for e in new_entries)


def test_different_prompt_versions_have_separate_cache_entries() -> None:
    cache = TranslationCache()
    provider = _build_provider_with_cache(cache)
    dialogue = _make_dialogue()

    llm_json = _llm_response_json()
    call_count = 0

    def fake_call_api(system_prompt: str, messages: list[dict[str, str]]) -> tuple[str, int, int]:
        nonlocal call_count
        call_count += 1
        return llm_json, 10, 5

    with patch.object(provider, "_call_api", side_effect=fake_call_api):
        state_v1 = _make_state("v1")
        state_v2 = _make_state("v2")
        provider.translate_dialogue(dialogue, "v1", state_v1)
        provider.translate_dialogue(dialogue, "v2", state_v2)

    assert call_count == 2  # both versions hit the LLM independently
