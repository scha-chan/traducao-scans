"""LocationProvider: optional LLM refinement for location strings (PRD §8.1).

The default StubLocationProvider performs no refinement and always returns
an empty string, keeping the deterministic base from LocationStage.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from agent.state import BBox


@runtime_checkable
class LocationProvider(Protocol):
    """Optionally refine a deterministic location label with an LLM call."""

    def refine(self, base_location: str, bbox: BBox) -> str:
        """Return a refined label, or '' to keep the deterministic base."""
        ...


class StubLocationProvider:
    """No-op provider — keeps the deterministic base unchanged."""

    def refine(self, base_location: str, bbox: BBox) -> str:
        return ""
