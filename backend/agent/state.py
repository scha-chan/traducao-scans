"""Pipeline state dataclasses (PRD §17.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass
class BBox:
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> BBox:
        return cls(x=d["x"], y=d["y"], width=d["width"], height=d["height"])


@dataclass
class RubyPair:
    base: str
    reading: str


@dataclass
class TranslationCandidate:
    translation: str
    observation: str
    relevance: int


@dataclass
class PanelRegion:
    bbox: BBox


@dataclass
class AgentLogEntry:
    timestamp: datetime
    stage: str
    trigger: str
    action: str
    detail: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "stage": self.stage,
            "trigger": self.trigger,
            "action": self.action,
            "detail": self.detail,
        }


@dataclass
class ProviderSpan:
    """Telemetry record for a single provider call (PRD §17.8)."""

    span_id: str
    run_id: str
    stage: str
    provider: str
    model_version: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float
    success: bool
    fallback_used: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "span_id": self.span_id,
            "run_id": self.run_id,
            "stage": self.stage,
            "provider": self.provider,
            "model_version": self.model_version,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "success": self.success,
            "fallback_used": self.fallback_used,
        }


@dataclass
class DialogueState:
    """State for a single speech bubble / text region across pipeline stages."""

    id: str
    bbox: BBox
    original: str | None = None
    lines: list[str] = field(default_factory=list)
    ruby: list[RubyPair] = field(default_factory=list)
    handwritten: bool = False
    orientation: Literal["VERTICAL", "HORIZONTAL"] = "VERTICAL"
    type: Literal["#", "$"] | None = None
    location: str | None = None
    order: int | None = None
    ocr_confidence: float | None = None
    needs_review: bool = False
    review_reason: str | None = None
    translations: list[TranslationCandidate] = field(default_factory=list)


@dataclass
class PageAnalysisState:
    """Accumulated state passed through all pipeline stages (PRD §17.4)."""

    page_id: UUID
    run_id: UUID
    image_path: str
    reading_direction: Literal["rtl", "ltr"] = "rtl"
    panels: list[PanelRegion] = field(default_factory=list)
    dialogues: list[DialogueState] = field(default_factory=list)
    spans: list[ProviderSpan] = field(default_factory=list)
    agent_log: list[AgentLogEntry] = field(default_factory=list)
