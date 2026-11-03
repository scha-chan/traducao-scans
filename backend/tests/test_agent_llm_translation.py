"""Unit tests for ClaudeTranslationProvider (F5-AG-03)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agent.providers.llm_translation import ClaudeTranslationProvider, LLMTranslationResponse
from agent.state import BBox, DialogueState, PageAnalysisState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dialogue(original: str = "きめたよ") -> DialogueState:
    return DialogueState(
        id=str(uuid4()),
        bbox=BBox(x=0, y=0, width=50, height=80),
        original=original,
        type="#",
        location="center",
        ocr_confidence=0.95,
    )


def _state() -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="/fake/page.png",
    )


def _make_response(candidates: list[dict[str, Any]]) -> MagicMock:
    """Build a mock anthropic Message with the given candidates JSON."""
    content_block = MagicMock()
    content_block.text = json.dumps({"candidates": candidates})
    mock_response = MagicMock()
    mock_response.content = [content_block]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    return mock_response


def _make_provider(tmp_path: Any) -> ClaudeTranslationProvider:  # noqa: ANN401
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "translate_page.v1.txt").write_text("Translate the following:", encoding="utf-8")
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        return ClaudeTranslationProvider(prompts_dir=str(prompts_dir))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_raises_value_error_without_api_key(tmp_path: Any) -> None:  # noqa: ANN401
    """Missing ANTHROPIC_API_KEY must raise ValueError at construction time."""
    with patch.dict("os.environ", {}, clear=True):
        import os

        os.environ.pop("ANTHROPIC_API_KEY", None)
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            ClaudeTranslationProvider()


def test_valid_response_returns_candidates(tmp_path: Any) -> None:  # noqa: ANN401
    """A well-formed LLM response produces TranslationCandidates."""
    provider = _make_provider(tmp_path)
    candidates_payload = [
        {"traducao": "Eu decidi!", "observacao": "", "relevancia": 1},
        {"traducao": "Resolvi!", "observacao": "more emphatic", "relevancia": 2},
    ]
    mock_response = _make_response(candidates_payload)

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = mock_response
        result = provider.translate_dialogue(_dialogue(), "v1")

    assert len(result) == 2
    assert result[0].translation == "Eu decidi!"
    assert result[0].relevance == 1
    assert result[1].translation == "Resolvi!"
    assert result[1].observation == "more emphatic"


def test_invalid_json_retries_and_succeeds_on_second_attempt(tmp_path: Any) -> None:  # noqa: ANN401
    """Invalid JSON on attempt 1 triggers a retry; valid JSON on attempt 2 succeeds."""
    provider = _make_provider(tmp_path)
    bad_content = MagicMock()
    bad_content.text = "not valid json at all"
    bad_response = MagicMock()
    bad_response.content = [bad_content]
    bad_response.usage.input_tokens = 80
    bad_response.usage.output_tokens = 10

    good_response = _make_response([{"traducao": "Na segunda!", "observacao": "", "relevancia": 1}])

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.side_effect = [bad_response, good_response]
        result = provider.translate_dialogue(_dialogue(), "v1")

    assert len(result) == 1
    assert result[0].translation == "Na segunda!"
    # Two API calls were made
    assert mock_anthropic.return_value.messages.create.call_count == 2


def test_all_retries_exhausted_sets_needs_review(tmp_path: Any) -> None:  # noqa: ANN401
    """After max_retries+1 failures the dialogue is flagged needs_review and [] is returned."""
    provider = _make_provider(tmp_path)
    bad_content = MagicMock()
    bad_content.text = "{invalid"
    bad_response = MagicMock()
    bad_response.content = [bad_content]
    bad_response.usage.input_tokens = 50
    bad_response.usage.output_tokens = 5

    dialogue = _dialogue()

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = bad_response
        result = provider.translate_dialogue(dialogue, "v1")

    assert result == []
    assert dialogue.needs_review is True
    assert dialogue.review_reason == "llm_translation_failed"
    # 1 initial + 2 retries = 3 total calls
    assert mock_anthropic.return_value.messages.create.call_count == 3


def test_span_recorded_on_success(tmp_path: Any) -> None:  # noqa: ANN401
    """A ProviderSpan is appended to state.spans on a successful translation."""
    provider = _make_provider(tmp_path)
    good_response = _make_response([{"traducao": "Teste", "observacao": "", "relevancia": 1}])
    state = _state()

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = good_response
        provider.translate_dialogue(_dialogue(), "v1", state)

    assert len(state.spans) == 1
    span = state.spans[0]
    assert span.stage == "translation"
    assert span.provider == "claude"
    assert span.success is True
    assert span.input_tokens == 100
    assert span.output_tokens == 50


def test_pydantic_validation_rejects_out_of_range_relevance() -> None:
    """LLMTranslationResponse rejects relevancia outside 1–5."""
    with pytest.raises(ValidationError):
        LLMTranslationResponse.model_validate(
            {"candidates": [{"traducao": "x", "observacao": "", "relevancia": 0}]}
        )


def test_single_candidate_for_simple_text(tmp_path: Any) -> None:  # noqa: ANN401
    """A response with one candidate is accepted and returned correctly."""
    provider = _make_provider(tmp_path)
    response = _make_response(
        [{"traducao": "Boom!", "observacao": "sound effect", "relevancia": 1}]
    )

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = response
        result = provider.translate_dialogue(_dialogue("ドーン"), "v1")

    assert len(result) == 1
    assert result[0].translation == "Boom!"
