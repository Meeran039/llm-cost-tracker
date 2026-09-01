"""
Approximate token counter for Groq's Llama models.

IMPORTANT, and verified before building this (not assumed): there is no
official offline tokenizer for Llama models comparable to OpenAI's
tiktoken, and Groq exposes no token-counting endpoint at all (confirmed
via Groq's own community forum, where this exact question has no
official answer). The real options were: (1) an unverified, tiny
third-party PyPI package, (2) Meta's gated HuggingFace tokenizer
(requires license acceptance and auth, defeating the "no key needed"
goal), or (3) a clearly-labeled approximation.

We chose (3): Llama's tokenizer is architecturally similar (BPE) to
OpenAI's, so tiktoken's cl100k_base encoding gives a reasonable
estimate, typically within ~10-15% of the true count for English text.
This is NOT exact, and every response using it is explicitly marked
`approximate: true` so the frontend (and the user) never mistakes it
for a precise count the way OpenAI's and Anthropic's numbers are.

The encoding is lazy-loaded (only fetched on first actual use, not at
import time) so a transient network hiccup on tiktoken's one-time
download can't prevent the whole app from starting up.
"""

import tiktoken

_encoding = None


def _get_encoding():
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.get_encoding("cl100k_base")
    return _encoding


def count_llama_tokens_approximate(text: str) -> int:
    """Returns an APPROXIMATE token count. See module docstring for why."""
    return len(_get_encoding().encode(text))