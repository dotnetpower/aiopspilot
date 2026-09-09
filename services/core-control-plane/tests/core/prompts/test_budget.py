"""Conservative prompt request-budget tests."""

from __future__ import annotations

from fdai.core.prompts import estimate_chat_request_tokens, estimate_prompt_tokens


def test_chat_request_estimate_counts_envelope_multibyte_text_and_output() -> None:
    messages = (
        {"role": "system", "content": "시스템"},
        {"role": "user", "content": "질문"},
    )

    estimate = estimate_chat_request_tokens(
        messages=messages,
        response_format={"type": "json_object"},
        reserved_output_tokens=128,
    )

    bare_text = estimate_prompt_tokens("시스템질문")
    assert estimate > bare_text + 128
