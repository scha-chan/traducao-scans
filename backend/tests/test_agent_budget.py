"""Tests for budget guard and ProviderSpan cost estimation (F5-BE-03)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

from agent.cost import estimate_cost_usd
from agent.providers.llm_translation import ClaudeTranslationProvider
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


def _make_response(input_tokens: int = 1000, output_tokens: int = 200) -> MagicMock:
    candidates = [{"traducao": "Decidi", "observacao": "", "relevancia": 5}]
    content_block = MagicMock()
    content_block.text = json.dumps({"candidates": candidates})
    mock_response = MagicMock()
    mock_response.content = [content_block]
    mock_response.usage.input_tokens = input_tokens
    mock_response.usage.output_tokens = output_tokens
    return mock_response


def _make_provider(tmp_path: Any) -> ClaudeTranslationProvider:  # noqa: ANN401
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "translate_page.v1.txt").write_text("Translate:", encoding="utf-8")
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        return ClaudeTranslationProvider(prompts_dir=str(prompts_dir))


# ---------------------------------------------------------------------------
# cost.py unit tests
# ---------------------------------------------------------------------------


def test_cost_estimation_haiku() -> None:
    # 1000 input * 0.80/1M + 200 output * 4.00/1M = 0.0008 + 0.0008 = 0.0016
    result = estimate_cost_usd("claude-haiku-5-5", 1000, 200)
    assert abs(result - 0.0016) < 1e-10


def test_cost_estimation_unknown_model() -> None:
    # fallback: (1.00, 5.00) → 1000*1/1M + 200*5/1M = 0.001 + 0.001 = 0.002
    result = estimate_cost_usd("claude-unknown-99", 1000, 200)
    assert abs(result - 0.002) < 1e-10


# ---------------------------------------------------------------------------
# ProviderSpan populated with real cost
# ---------------------------------------------------------------------------


def test_provider_span_populated(tmp_path: Any) -> None:  # noqa: ANN401
    provider = _make_provider(tmp_path)
    state = _state()
    mock_resp = _make_response(input_tokens=1000, output_tokens=200)

    with patch("anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = mock_resp
        provider.translate_dialogue(_dialogue(), "v1", state=state)

    assert len(state.spans) == 1
    span = state.spans[0]
    assert span.cost_usd > 0
    assert span.input_tokens == 1000
    assert span.output_tokens == 200
    assert span.provider == "claude"
    assert span.stage == "translation"


# ---------------------------------------------------------------------------
# Budget guard alert
# ---------------------------------------------------------------------------


def test_budget_alert_logged(tmp_path: Any) -> None:  # noqa: ANN401
    """When cumulative cost exceeds the limit an alert is logged."""
    provider = _make_provider(tmp_path)
    state = _state()
    # Use large token counts so cost > 0.05 default limit
    mock_resp = _make_response(input_tokens=10_000, output_tokens=10_000)

    env = {"ANTHROPIC_API_KEY": "test-key", "MAX_COST_PER_PAGE_USD": "0.00001"}
    with patch.dict("os.environ", env), patch("anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = mock_resp
        provider.translate_dialogue(_dialogue(), "v1", state=state)

    budget_entries = [e for e in state.agent_log if e.trigger == "cost_exceeded"]
    assert len(budget_entries) >= 1
    entry = budget_entries[0]
    assert entry.stage == "budget_guard"
    assert entry.action == "alert"
    assert entry.detail["cost_usd"] > entry.detail["limit_usd"]


def test_budget_no_alert_under_limit(tmp_path: Any) -> None:  # noqa: ANN401
    """When cost is below the limit no budget alert is logged."""
    provider = _make_provider(tmp_path)
    state = _state()
    # Small token counts → tiny cost, well under 0.05
    mock_resp = _make_response(input_tokens=10, output_tokens=5)

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
        patch("anthropic.Anthropic") as mock_client_cls,
    ):
        mock_client_cls.return_value.messages.create.return_value = mock_resp
        provider.translate_dialogue(_dialogue(), "v1", state=state)

    budget_entries = [e for e in state.agent_log if e.trigger == "cost_exceeded"]
    assert len(budget_entries) == 0
