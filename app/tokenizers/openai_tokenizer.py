"""
Counts tokens for OpenAI models using tiktoken, OpenAI's own open-source
tokenizer. Runs entirely offline -- no API call, no key, no cost.
(It downloads a small ~2-3MB encoding file from Microsoft's servers on
first use, then caches it locally -- one-time internet access, no key.)
"""

import tiktoken

_FALLBACK_ENCODING = "o200k_base"


def count_openai_tokens(model: str, text: str) -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding(_FALLBACK_ENCODING)
    return len(encoding.encode(text))