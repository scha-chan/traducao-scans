"""Stage[In, Out] abstract interface (PRD §17.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent.state import PageAnalysisState


class Stage(ABC):
    """Pure, typed pipeline stage — testable in isolation.

    Each stage reads from ``state`` and returns a new state with its
    contribution appended.  Stages must not perform side-effects outside of
    their own model calls; DB persistence is the orchestrator's responsibility.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique stage identifier used in agent_log entries."""

    @abstractmethod
    async def run(self, state: PageAnalysisState) -> PageAnalysisState:
        """Execute the stage and return the updated state."""
