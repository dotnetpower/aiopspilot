"""Conservative prompt and request token estimation primitives."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence


def estimate_prompt_tokens(text: str) -> int:
    """Return a tokenizer-free upper bound of one token per UTF-8 byte."""

    if not text:
        return 0
    return len(text.encode("utf-8"))


def estimate_chat_request_tokens(
    *,
    messages: Sequence[Mapping[str, object]],
    response_format: Mapping[str, object],
    reserved_output_tokens: int,
) -> int:
    """Estimate the complete serialized chat request plus reserved output."""

    encoded = json.dumps(
        {
            "messages": list(messages),
            "response_format": response_format,
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return estimate_prompt_tokens(encoded) + reserved_output_tokens


__all__ = ["estimate_chat_request_tokens", "estimate_prompt_tokens"]
