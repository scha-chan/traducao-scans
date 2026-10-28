"""Unit tests for Stage interface and Orchestrator (F3-AG-01)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from agent.orchestrator import Orchestrator
from agent.stage import Stage
from agent.stages.stub import StubStage
from agent.state import (
    AgentLogEntry,
    BBox,
    DialogueState,
    PageAnalysisState,
    ProviderSpan,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state() -> PageAnalysisState:
    return PageAnalysisState(
        page_id=uuid4(),
        run_id=uuid4(),
        image_path="/tmp/page.jpg",
    )


# ---------------------------------------------------------------------------
# Stage interface
# ---------------------------------------------------------------------------


class _AppendingStage(Stage):
    """Test stage that appends a dialogue to the state."""

    def __init__(self, stage_name: str) -> None:
        self._name = stage_name

    @property
    def name(self) -> str:
        return self._name

    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        state.dialogues.append(DialogueState(id=f"d-{self._name}", bbox=BBox(0, 0, 10, 10)))
        return state


# ---------------------------------------------------------------------------
# Tests: Stage isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stub_stage_is_noop() -> None:
    state = _make_state()
    result = await StubStage().run(state)
    assert result.dialogues == []
    assert result.agent_log == []


@pytest.mark.asyncio
async def test_stage_testable_in_isolation() -> None:
    stage = _AppendingStage("ocr")
    state = _make_state()
    result = await stage.run(state)
    assert len(result.dialogues) == 1
    assert result.dialogues[0].id == "d-ocr"


# ---------------------------------------------------------------------------
# Tests: Orchestrator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_runs_stages_in_order() -> None:
    stages = [_AppendingStage("a"), _AppendingStage("b"), _AppendingStage("c")]
    orchestrator = Orchestrator(stages=stages)
    state = _make_state()
    result = await orchestrator.run(state)

    assert [d.id for d in result.dialogues] == ["d-a", "d-b", "d-c"]


@pytest.mark.asyncio
async def test_orchestrator_accumulates_agent_log() -> None:
    stages = [_AppendingStage("stage1"), _AppendingStage("stage2")]
    orchestrator = Orchestrator(stages=stages)
    state = _make_state()
    result = await orchestrator.run(state)

    assert len(result.agent_log) == 2
    assert result.agent_log[0].stage == "stage1"
    assert result.agent_log[1].stage == "stage2"
    for entry in result.agent_log:
        assert entry.trigger == "pipeline"
        assert entry.action == "completed"
        assert "elapsed_ms" in entry.detail


@pytest.mark.asyncio
async def test_orchestrator_with_no_stages() -> None:
    orchestrator = Orchestrator(stages=[])
    state = _make_state()
    result = await orchestrator.run(state)
    assert result.agent_log == []
    assert result.dialogues == []


# ---------------------------------------------------------------------------
# Tests: State dataclasses
# ---------------------------------------------------------------------------


def test_bbox_roundtrip() -> None:
    bbox = BBox(x=10, y=20, width=100, height=200)
    assert BBox.from_dict(bbox.to_dict()) == bbox


def test_agent_log_entry_serialises() -> None:
    entry = AgentLogEntry(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        stage="ocr",
        trigger="pipeline",
        action="completed",
        detail={"elapsed_ms": 42},
    )
    d = entry.to_dict()
    assert d["stage"] == "ocr"
    assert d["detail"]["elapsed_ms"] == 42


def test_provider_span_serialises() -> None:
    span = ProviderSpan(
        span_id="s1",
        run_id="r1",
        stage="ocr",
        provider="google",
        model_version="v1",
        input_tokens=10,
        output_tokens=5,
        latency_ms=200,
        cost_usd=0.001,
        success=True,
        fallback_used=False,
    )
    d = span.to_dict()
    assert d["provider"] == "google"
    assert d["success"] is True
