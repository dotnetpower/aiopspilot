"""Validate and normalize source-grounded semantic judgment candidates."""

from __future__ import annotations

import logging
from typing import Any

from fdai_service_contracts.semantic_judgment import (
    SemanticJudgmentProposal,
    SemanticTarget,
)

_LOGGER = logging.getLogger(__name__)


def ground_unique_source_spans(
    proposal: SemanticJudgmentProposal,
    *,
    utterance: str,
    capabilities: tuple[dict[str, Any], ...],
    allow_context_target_drop: bool = True,
) -> SemanticJudgmentProposal:
    """Correct only a unique exact current-turn value and retain legacy context omission."""

    canonical_targets = {
        (kind, name)
        for capability in capabilities
        if isinstance((kind := capability.get("kind")), str)
        if isinstance((name := capability.get("name")), str)
    }
    changed = False
    grounded_fields: dict[str, tuple[SemanticTarget, ...]] = {}
    for field_name, proposed_targets in (
        ("targets", proposal.targets),
        ("forbidden_actions", proposal.forbidden_actions),
    ):
        grounded_targets: list[SemanticTarget] = []
        for target_index, target in enumerate(proposed_targets):
            if utterance[target.source_start : target.source_end] == target.value:
                grounded_targets.append(target)
                continue
            source_start = utterance.find(target.value)
            second_start = (
                utterance.find(target.value, source_start + 1) if source_start >= 0 else -1
            )
            if source_start < 0 or second_start >= 0:
                _LOGGER.warning(
                    "semantic_judgment_target_span_unresolved",
                    extra={
                        "target_field": field_name,
                        "target_index": target_index,
                        "target_kind": target.kind,
                        "exact_occurrences": 0 if source_start < 0 else 2,
                    },
                )
                if (
                    allow_context_target_drop
                    and field_name == "targets"
                    and target.canonical_value is not None
                    and (target.kind, target.canonical_value) in canonical_targets
                ):
                    changed = True
                    continue
                grounded_targets.append(target)
                continue
            grounded_targets.append(
                target.model_copy(
                    update={
                        "source_start": source_start,
                        "source_end": source_start + len(target.value),
                    }
                )
            )
            changed = True
        grounded_fields[field_name] = tuple(grounded_targets)
    return proposal.model_copy(update=grounded_fields) if changed else proposal


def normalize_action_advice_identity_ambiguity(
    proposal: SemanticJudgmentProposal,
) -> SemanticJudgmentProposal:
    if (
        proposal.primary_intent != "action_requirements"
        or proposal.action_posture != "advise_only"
        or not any(target.kind == "resource_type" for target in proposal.targets)
        or not proposal.ambiguous
        or proposal.alternatives
        or proposal.unresolved_terms != ("resource_identity",)
    ):
        return proposal
    return _without_ambiguity(proposal)


def normalize_exact_resource_identity_ambiguity(
    proposal: SemanticJudgmentProposal,
) -> SemanticJudgmentProposal:
    """Remove only ambiguity contradicted by one typed exact Resource target."""

    exact_resources = tuple(target for target in proposal.targets if target.kind == "resource")
    if (
        proposal.primary_intent != "query.resource_current_state"
        or len(exact_resources) != 1
        or not proposal.ambiguous
        or proposal.alternatives
        or proposal.unresolved_terms != ("resource_identity",)
    ):
        return proposal
    return _without_ambiguity(proposal)


def normalize_overlapping_target_fragments(
    proposal: SemanticJudgmentProposal,
) -> SemanticJudgmentProposal:
    """Drop subtype fragments that occupy only part of one exact Resource target."""

    exact_resources = tuple(target for target in proposal.targets if target.kind == "resource")
    if len(exact_resources) != 1:
        return proposal
    resource = exact_resources[0]
    targets = tuple(
        target
        for target in proposal.targets
        if not (
            target.kind == "resource_type"
            and resource.source_start <= target.source_start
            and target.source_end <= resource.source_end
            and (target.source_start, target.source_end)
            != (resource.source_start, resource.source_end)
        )
    )
    return (
        proposal
        if targets == proposal.targets
        else proposal.model_copy(update={"targets": targets})
    )


def normalize_unsupplied_time_canonical_values(
    proposal: SemanticJudgmentProposal,
    *,
    capabilities: tuple[dict[str, Any], ...],
) -> SemanticJudgmentProposal:
    supplied = {
        value
        for capability in capabilities
        for field in ("measure_concepts", "canonical_values")
        if isinstance((values := capability.get(field)), (list, tuple))
        for value in values
        if isinstance(value, str)
    }
    targets = tuple(
        (
            target.model_copy(update={"canonical_value": None})
            if target.kind == "time_range"
            and target.canonical_value is not None
            and target.canonical_value not in supplied
            else target
        )
        for target in proposal.targets
    )
    return (
        proposal
        if targets == proposal.targets
        else proposal.model_copy(update={"targets": targets})
    )


def validate_action_target_ambiguity(proposal: SemanticJudgmentProposal) -> None:
    if (
        proposal.action_posture == "draft_only"
        and proposal.action_subject == "ActionType"
        and not proposal.ambiguous
        and not any(target.kind in {"action_type", "resource"} for target in proposal.targets)
    ):
        raise ValueError("semantic draft action requires an exact target or clarification")


def validate_capability_grounding(
    proposal: SemanticJudgmentProposal,
    *,
    capabilities: tuple[dict[str, Any], ...],
) -> None:
    allowed_intents: set[str] = set()
    allowed_canonical_values: set[str] = set()
    names_by_kind: dict[str, set[str]] = {}
    for capability in capabilities:
        kind = capability.get("kind")
        name = capability.get("name")
        if isinstance(name, str):
            allowed_canonical_values.add(name)
            if isinstance(kind, str):
                names_by_kind.setdefault(kind, set()).add(name)
            if kind in {"action_type", "function_type", "intent", "question_domain"}:
                allowed_intents.add(name)
            if kind == "link_type":
                allowed_intents.add(f"query.{name}")
        intent = capability.get("intent")
        if isinstance(intent, str):
            allowed_intents.add(intent)
        for field in ("question_domains", "measure_concepts", "canonical_values"):
            values = capability.get(field)
            if isinstance(values, (list, tuple)) and all(
                isinstance(value, str) for value in values
            ):
                allowed_canonical_values.update(values)
                if field == "question_domains":
                    allowed_intents.update(values)
    if any(
        intent not in allowed_intents
        for intent in (proposal.primary_intent, *proposal.secondary_intents)
    ):
        raise ValueError("semantic intent is not supplied by capabilities")
    if any(
        target.canonical_value is not None
        and target.canonical_value not in allowed_canonical_values
        for target in (*proposal.targets, *proposal.forbidden_actions)
    ):
        raise ValueError("semantic target canonical identity is not supplied")
    capability_kind_by_target = {
        "action_type": "action_type",
        "object_type": "object_type",
        "resource_type": "resource_type",
    }
    instance_kinds = {"incident_id", "resource", "resource_group", "severity", "time_range"}
    for target in proposal.targets:
        canonical_value = target.canonical_value
        if canonical_value is None:
            continue
        if target.kind in instance_kinds:
            raise ValueError("semantic instance target MUST NOT carry a catalog type identity")
        capability_kind = capability_kind_by_target.get(target.kind)
        if capability_kind is not None and canonical_value not in names_by_kind.get(
            capability_kind, set()
        ):
            raise ValueError("semantic target canonical identity kind does not match")


def validate_forbidden_action_canonical_values(
    proposal: SemanticJudgmentProposal,
    *,
    capabilities: tuple[dict[str, Any], ...],
) -> None:
    supplied = {
        (kind, name)
        for capability in capabilities
        if isinstance((kind := capability.get("kind")), str)
        if isinstance((name := capability.get("name")), str)
    }
    if any(
        action.canonical_value is not None and (action.kind, action.canonical_value) not in supplied
        for action in proposal.forbidden_actions
    ):
        raise ValueError("semantic forbidden action canonical identity is not supplied")


def validate_source_spans(proposal: SemanticJudgmentProposal, *, utterance: str) -> None:
    for field, targets in (
        ("target", proposal.targets),
        ("forbidden action", proposal.forbidden_actions),
    ):
        for target in targets:
            if target.source_end > len(utterance):
                raise ValueError(f"semantic {field} source span exceeds the utterance")
            if utterance[target.source_start : target.source_end] != target.value:
                raise ValueError(f"semantic {field} source span does not match the utterance")


def _without_ambiguity(proposal: SemanticJudgmentProposal) -> SemanticJudgmentProposal:
    return proposal.model_copy(
        update={
            "ambiguous": False,
            "unresolved_terms": (),
            "clarification": None,
        }
    )


__all__ = [
    "ground_unique_source_spans",
    "normalize_action_advice_identity_ambiguity",
    "normalize_exact_resource_identity_ambiguity",
    "normalize_overlapping_target_fragments",
    "normalize_unsupplied_time_canonical_values",
    "validate_action_target_ambiguity",
    "validate_capability_grounding",
    "validate_forbidden_action_canonical_values",
    "validate_source_spans",
]
