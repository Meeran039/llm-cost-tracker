"""
Published per-model pricing, in USD per 1 million tokens.
Source: each provider's public pricing page. LAST UPDATED: 2026-08-31.
This table needs periodic manual upkeep as providers change pricing --
that maintenance burden is real and worth flagging, not hiding.
"""

PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00, "context_window": 128_000},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "context_window": 128_000},
    "claude-opus-5": {"input": 15.00, "output": 75.00, "context_window": 200_000},
    "claude-sonnet-5": {"input": 3.00, "output": 15.00, "context_window": 200_000},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00, "context_window": 200_000},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79, "context_window": 128_000},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08, "context_window": 128_000},
}


class UnknownModelError(Exception):
    """Raised when a model isn't in the pricing table."""


def get_model_info(model: str) -> dict:
    if model not in PRICING:
        raise UnknownModelError(
            f"'{model}' is not in the pricing table. "
            f"Known models: {sorted(PRICING.keys())}"
        )
    return PRICING[model]


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Returns cost in USD for the given token counts on the given model."""
    info = get_model_info(model)
    cost = (input_tokens / 1_000_000) * info["input"] + (output_tokens / 1_000_000) * info["output"]
    return round(cost, 8)


def fits_context_window(model: str, total_tokens: int) -> bool:
    info = get_model_info(model)
    return total_tokens <= info["context_window"]