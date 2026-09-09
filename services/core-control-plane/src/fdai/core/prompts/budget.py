"""Conservative prompt and request token estimation primitives."""

from __future__ import annotations

_UNITS_PER_TOKEN = 4


def estimate_prompt_tokens(text: str) -> int:
    """Estimate tokens without undercounting multibyte UTF-8 text."""

    if not text:
        return 0
    units = max(len(text), len(text.encode("utf-8")))
    return max(1, (units + _UNITS_PER_TOKEN - 1) // _UNITS_PER_TOKEN)


__all__ = ["estimate_prompt_tokens"]
