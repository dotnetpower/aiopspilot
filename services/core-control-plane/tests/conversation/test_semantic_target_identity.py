"""Unit coverage for the shared exact-runtime-target detector.

The detector distinguishes a specific Azure resource name mentioned in an
utterance from a generic descriptive phrase, without a model call. See
``fdai.core.conversation.semantic_target_identity`` for the grounding rule.
"""

from __future__ import annotations

from fdai.core.conversation.semantic_target_identity import (
    ExactResourceTarget,
    exact_resource_target_from_constraints,
    runtime_target_spans,
)

_RESOURCE_DESCRIPTOR = {
    "kind": "object",
    "name": "Resource",
    "properties": {"id": {}, "name": {}, "display_name": {}},
}


def test_three_segment_names_are_always_recognized() -> None:
    utterance = "What is the current power state of vm-web-01?"
    assert runtime_target_spans(utterance) == ((35, 44),)


def test_single_hyphen_digit_bearing_names_are_recognized() -> None:
    """A common Azure convention (`vm-01`, `web-02`) has one hyphen and a digit."""

    for name in ("vm-01", "web-02", "sql-prod01", "vnet-01"):
        utterance = f"Is {name} healthy right now?"
        spans = runtime_target_spans(utterance)
        assert len(spans) == 1, name
        start, end = spans[0]
        assert utterance[start:end] == name


def test_single_hyphen_generic_phrases_without_digits_are_not_targets() -> None:
    """Descriptive phrases such as `high-cpu` must not be treated as a resource."""

    for phrase in ("high-cpu", "read-only", "app-service"):
        utterance = f"Show me {phrase} details"
        assert runtime_target_spans(utterance) == ()


def test_exact_resource_target_resolves_single_hyphen_instance_name() -> None:
    utterance = "What is the current power state of vm-01?"
    target = exact_resource_target_from_constraints(
        (),
        utterance=utterance,
        descriptors=(_RESOURCE_DESCRIPTOR,),
    )
    assert target == ExactResourceTarget(property_name="name", value="vm-01")


def test_exact_resource_target_ignores_generic_digit_free_phrase() -> None:
    utterance = "Show me high-cpu virtual machines"
    target = exact_resource_target_from_constraints(
        (),
        utterance=utterance,
        descriptors=(_RESOURCE_DESCRIPTOR,),
    )
    assert target is None
