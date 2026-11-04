"""Tests for F5-BE-02: model fallback on transient API errors (PRD §17.8)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from agent.providers.llm_translation import ClaudeTranslationProvider
from agent.state import BBox, DialogueState, PageAnalysisState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_RESPONSE = json.dumps(
    {
        "candidates": [
            {"traducao": "Olá", "observacao": "", "relevancia": 5},
        ]
    }
)

_MOCK_USAGE = MagicMock(input_tokens=10, output_tokens=5)
_API_REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _http_response(status: int) -> httpx.Response:
    """Build an httpx.Response with a request set (required by APIStatusError)."""
    r = httpx.Response(status)
    r.request = _API_REQUEST
    return r


def _make_api_response(text: str = _VALID_RESPONSE) -> MagicMock:
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    resp.usage = _MOCK_USAGE
    return resp


def _make_dialogue(did: str = "d1") -> DialogueState:
    return DialogueState(
        id=did,
        bbox=BBox(x=0, y=0, width=10, height=10),
        original="こんにちは",
        type="#",
    )


def _make_state() -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="img.png",
    )


def _make_provider(
    prompts_dir: Path,
    fallback_model: str | None = None,
    primary_model: str | None = None,
) -> ClaudeTranslationProvider:
    return ClaudeTranslationProvider(
        api_key="test-key",
        primary_model=primary_model or "primary-model",
        fallback_model=fallback_model,
        prompts_dir=prompts_dir,
        max_retries=0,
    )


def _write_prompt(prompts_dir: Path) -> None:
    (prompts_dir / "translate_page.v1.txt").write_text("Translate.", encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def prompts_dir(tmp_path: Path) -> Path:
    _write_prompt(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFallbackOnStatusError:
    def test_fallback_on_status_error(self, prompts_dir: Path) -> None:
        """Primary raises APIStatusError (5xx) → fallback called → fallback_used=True."""
        from anthropic import APIStatusError

        provider = _make_provider(prompts_dir, fallback_model="fallback-model")
        dialogue = _make_dialogue()
        state = _make_state()

        err = APIStatusError("server error", response=_http_response(500), body={})

        with patch.object(provider, "_call_api") as mock_call:
            mock_call.side_effect = [
                err,
                (_VALID_RESPONSE, 10, 5),
            ]
            result = provider.translate_dialogue(dialogue, "v1", state)

        assert len(result) == 1
        assert result[0].translation == "Olá"
        assert len(state.spans) == 1
        span = state.spans[0]
        assert span.fallback_used is True
        assert span.model_version == "fallback-model"
        assert span.success is True

    def test_fallback_model_passed_to_second_call(self, prompts_dir: Path) -> None:
        """Verify second _call_api call uses the fallback model name."""
        from anthropic import APIStatusError

        provider = _make_provider(
            prompts_dir, primary_model="primary-model", fallback_model="fallback-model"
        )
        dialogue = _make_dialogue()
        state = _make_state()

        err = APIStatusError("err", response=_http_response(503), body={})

        with patch.object(provider, "_call_api") as mock_call:
            mock_call.side_effect = [err, (_VALID_RESPONSE, 10, 5)]
            provider.translate_dialogue(dialogue, "v1", state)

        calls = mock_call.call_args_list
        assert len(calls) == 2
        assert (
            calls[0].kwargs.get("model") == "primary-model" or calls[0].args[2] == "primary-model"
        )
        second_model = calls[1].kwargs.get("model") or calls[1].args[2]
        assert second_model == "fallback-model"


class TestFallbackOnTimeout:
    def test_fallback_on_timeout(self, prompts_dir: Path) -> None:
        """Primary raises APITimeoutError → fallback called → fallback_used=True."""
        from anthropic import APITimeoutError

        provider = _make_provider(prompts_dir, fallback_model="fallback-model")
        dialogue = _make_dialogue()
        state = _make_state()

        err = APITimeoutError(
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        )

        with patch.object(provider, "_call_api") as mock_call:
            mock_call.side_effect = [err, (_VALID_RESPONSE, 10, 5)]
            result = provider.translate_dialogue(dialogue, "v1", state)

        assert len(result) == 1
        assert state.spans[0].fallback_used is True


class TestNoFallbackConfigured:
    def test_no_fallback_configured_propagates(self, prompts_dir: Path) -> None:
        """Without fallback_model, transient error is propagated immediately."""
        from anthropic import APIStatusError

        provider = _make_provider(prompts_dir, fallback_model=None)
        dialogue = _make_dialogue()
        state = _make_state()

        err = APIStatusError("err", response=_http_response(500), body={})

        with patch.object(provider, "_call_api") as mock_call:
            mock_call.side_effect = err
            with pytest.raises(APIStatusError):
                provider.translate_dialogue(dialogue, "v1", state)

        # Only one call was made (no retry to fallback)
        assert mock_call.call_count == 1
        assert dialogue.needs_review is True
        assert len(state.spans) == 1
        assert state.spans[0].success is False
        assert state.spans[0].fallback_used is False


class TestNoFallbackNeeded:
    def test_no_fallback_needed(self, prompts_dir: Path) -> None:
        """Primary succeeds → fallback_used=False in span."""
        provider = _make_provider(prompts_dir, fallback_model="fallback-model")
        dialogue = _make_dialogue()
        state = _make_state()

        with patch.object(provider, "_call_api") as mock_call:
            mock_call.return_value = (_VALID_RESPONSE, 10, 5)
            result = provider.translate_dialogue(dialogue, "v1", state)

        assert len(result) == 1
        assert mock_call.call_count == 1
        assert state.spans[0].fallback_used is False


class TestFallbackAlsoFails:
    def test_fallback_also_fails(self, prompts_dir: Path) -> None:
        """Both primary and fallback fail → exception propagated, needs_review=True."""
        from anthropic import APIStatusError

        provider = _make_provider(prompts_dir, fallback_model="fallback-model")
        dialogue = _make_dialogue()
        state = _make_state()

        err_primary = APIStatusError("err", response=_http_response(500), body={})
        err_fallback = APIStatusError("err2", response=_http_response(503), body={})

        with patch.object(provider, "_call_api") as mock_call:
            mock_call.side_effect = [err_primary, err_fallback]
            with pytest.raises(APIStatusError):
                provider.translate_dialogue(dialogue, "v1", state)

        assert dialogue.needs_review is True
        assert len(state.spans) == 1
        span = state.spans[0]
        assert span.fallback_used is True
        assert span.success is False
