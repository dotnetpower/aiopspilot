"""Normalize semantic judgment aliases only against supplied capability metadata."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from fdai_service_contracts.semantic_judgment import SemanticJudgmentProposal

from fdai.shared.contracts.models import OntologyDeclarationKind

_COLLECTION_FUNCTION_INTENTS = frozenset(
    {
        "query.governed_documents",
        "query.resource_event_history",
        "query.resource_health_inventory",
        "query.resource_state_inventory",
        "query.subscription_scope_identity",
        "query.subscription_service_health",
    }
)
_ONTOLOGY_COUNT_INTENT_KINDS = {
    f"query.ontology_{declaration_kind.value}_type_count": declaration_kind
    for declaration_kind in OntologyDeclarationKind
}


def normalize_primary_intent(
    proposal: SemanticJudgmentProposal,
    *,
    capabilities: Sequence[Mapping[str, Any]],
) -> SemanticJudgmentProposal:
    """Map a proposed alias only to an exact FunctionType or LinkType in the manifest."""

    function_names = {
        name
        for capability in capabilities
        if capability.get("kind") == "function_type"
        if isinstance((name := capability.get("name")), str)
    }
    count_kind = _ONTOLOGY_COUNT_INTENT_KINDS.get(proposal.primary_intent)
    if count_kind is not None:
        if "query.manifest" not in function_names:
            raise ValueError("semantic ontology count intent requires supplied manifest capability")
        count_facet = f"{count_kind.value}_type_count"
        requested_facets = (
            proposal.requested_facets
            if count_facet in proposal.requested_facets
            else (*proposal.requested_facets, count_facet)
        )
        return proposal.model_copy(
            update={
                "primary_intent": "query.manifest",
                "requested_facets": requested_facets,
            }
        )
    if (
        proposal.primary_intent in {"query.kubernetes_event_history", "query.kubernetes_events"}
        and "query.resource_event_history" in function_names
    ):
        return proposal.model_copy(update={"primary_intent": "query.resource_event_history"})
    link_names = {
        name
        for capability in capabilities
        if capability.get("kind") == "link_type"
        if isinstance((name := capability.get("name")), str)
    }
    if proposal.primary_intent not in link_names:
        return proposal
    namespaced_intent = f"query.{proposal.primary_intent}"
    if len(namespaced_intent) > 80:
        raise ValueError("semantic link intent MUST use query namespace")
    return proposal.model_copy(update={"primary_intent": namespaced_intent})


def normalize_collection_identity_ambiguity(
    proposal: SemanticJudgmentProposal,
    *,
    capabilities: Sequence[Mapping[str, Any]],
) -> SemanticJudgmentProposal:
    """Remove only a target ambiguity forbidden by an exact supplied collection function."""

    bound_functions = {
        capability.get("name")
        for capability in capabilities
        if capability.get("kind") == "function_type"
    }
    if (
        proposal.primary_intent not in _COLLECTION_FUNCTION_INTENTS
        or proposal.primary_intent not in bound_functions
        or any(target.kind in {"resource", "resource_group"} for target in proposal.targets)
        or not proposal.ambiguous
        or proposal.alternatives
        or proposal.unresolved_terms != ("resource_identity",)
    ):
        return proposal
    return proposal.model_copy(
        update={
            "ambiguous": False,
            "unresolved_terms": (),
            "clarification": None,
        }
    )


__all__ = ["normalize_collection_identity_ambiguity", "normalize_primary_intent"]
