"""Token prices for the course models, in USD per 1M tokens.

Source: Portkey's pricing feed, https://api.portkey.ai/model-configs/pricing/openai/<model>
(it lists *cents* per token — e.g. luna input 0.00001¢ → $0.10 / 1M). Standard tier,
prompts up to 272k tokens; our per-call prompts are far below that.
"""

from __future__ import annotations

PRICES: dict[str, dict[str, float]] = {
    "gpt-6-luna": {"input": 0.10, "cached_input": 0.01, "output": 0.50},
    "gpt-6-astra": {"input": 10.00, "cached_input": 1.00, "output": 50.00},
}
DEFAULT_MODEL = "gpt-6-luna"


def cost_usd(model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
    """Dollar cost of one model call. `input_tokens` includes the cached ones."""
    p = PRICES[model]
    uncached = max(input_tokens - cached_tokens, 0)
    return (uncached * p["input"] + cached_tokens * p["cached_input"] + output_tokens * p["output"]) / 1_000_000


def fmt_usd(v: float) -> str:
    """Cheap runs need more digits to show up at all (mirrors the frontend's fmtUsd)."""
    if v == 0:
        return "$0"
    return f"${v:.5f}" if v < 0.01 else f"${v:.4f}" if v < 1 else f"${v:.2f}"
