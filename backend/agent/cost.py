"""Cost estimation for Claude API calls (PRD §17.8)."""

from __future__ import annotations

# Prices per 1M tokens (input, output) in USD
_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.80, 4.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-5-5": (15.00, 75.00),
}
_DEFAULT_PRICING: tuple[float, float] = (1.00, 5.00)


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return estimated cost in USD for one API call."""
    inp_price, out_price = _PRICING.get(model, _DEFAULT_PRICING)
    return (input_tokens * inp_price + output_tokens * out_price) / 1_000_000
