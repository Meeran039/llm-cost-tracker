"""
Counts tokens for Claude models using Anthropic's real /v1/messages/count_tokens
endpoint. Verified: this works with a REGULAR API key, no Admin key needed.
"""

import httpx

ANTHROPIC_COUNT_TOKENS_URL = "https://api.anthropic.com/v1/messages/count_tokens"
ANTHROPIC_API_VERSION = "2023-06-01"


class AnthropicTokenizerError(Exception):
    """Raised for any non-success response from the count_tokens endpoint."""


def count_anthropic_tokens(
    api_key: str,
    model: str,
    text: str,
    client: httpx.Client | None = None,
) -> int:
    owns_client = client is None
    client = client or httpx.Client(timeout=15.0)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": text}],
    }

    try:
        response = client.post(ANTHROPIC_COUNT_TOKENS_URL, json=body, headers=headers)
        if response.status_code != 200:
            raise AnthropicTokenizerError(
                f"Anthropic count_tokens returned {response.status_code}: {response.text}"
            )
        return response.json()["input_tokens"]
    finally:
        if owns_client:
            client.close()