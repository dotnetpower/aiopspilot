"""Compile declaration counts from a verified ontology manifest frame."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fdai_service_contracts.ontology_query import (
    OntologyQueryPlan,
    QueryNodeKind,
    SemanticOperation,
    SemanticProblemFrame,
)
from fdai_service_contracts.semantic_judgment import SemanticJudgmentProposal

from fdai.core.ontology_platform import OntologyQueryPlanVerifier, QueryManifest
from fdai.core.ontology_platform.declaration_queries import (
    ONTOLOGY_DECLARATION_FUNCTION_NAME,
)
from fdai.core.ontology_platform.manifest_queries import ONTOLOGY_MANIFEST_FUNCTION_NAME
from fdai.shared.contracts.models import OntologyDeclarationKind

from .semantic_planning_alignment import (
    DECLARATION_SECTIONS_BY_MEASURE,
    verify_frame_plan_alignment,
)
from .semantic_planning_frame import build_semantic_frame
from .semantic_planning_models import (
    QueryNodeProposal,
    QueryPlanProposal,
    SemanticFrameProposal,
    SemanticOutputShape,
)
from .semantic_planning_support import _build_plan
from .session import Principal


def build_ontology_schema_frame(
    judgment: SemanticJudgmentProposal | None,
    *,
    utterance: str,
    context: tuple[str, ...],
    descriptors: tuple[dict[str, Any], ...],
) -> tuple[SemanticFrameProposal, SemanticProblemFrame] | None:
    """Build an exact schema frame from one accepted no-authority judgment."""

    if (
        judgment is None
        or judgment.ambiguous
        or judgment.action_posture != "advise_only"
        or judgment.execution_authority
        or judgment.secondary_intents
    ):
        return None
    available_functions = {
        descriptor.get("name") for descriptor in descriptors if descriptor.get("kind") == "function"
    }
    if judgment.primary_intent == ONTOLOGY_MANIFEST_FUNCTION_NAME:
        if not any(
            facet == "count" or facet.endswith("_count") for facet in judgment.requested_facets
        ):
            return None
        declaration_kinds = {
            declaration_kind
            for target in judgment.targets
            if (declaration_kind := _as_declaration_kind(target.canonical_value)) is not None
        }
        if (
            ONTOLOGY_MANIFEST_FUNCTION_NAME not in available_functions
            or len(declaration_kinds) != 1
        ):
            return None
        proposal = SemanticFrameProposal(
            operation=SemanticOperation.AGGREGATE,
            subject_constraints=(next(iter(declaration_kinds)).value,),
            measure_concepts=("count",),
            temporal_scope={},
            output_shape=SemanticOutputShape.AGGREGATION_TABLE,
            evidence_requirements=(),
            unresolved_terms=(),
            clarification_requirements=(),
            clarification=None,
            investigation=None,
            confidence=judgment.confidence,
        )
        return proposal, build_semantic_frame(proposal, utterance=utterance, context=context)
    if judgment.primary_intent != ONTOLOGY_DECLARATION_FUNCTION_NAME:
        return None
    declared_subjects = {
        target.canonical_value
        for target in judgment.targets
        if target.canonical_value is not None
        and any(
            descriptor.get("kind") in {"action", "link", "object"}
            and descriptor.get("name") == target.canonical_value
            for descriptor in descriptors
        )
    }
    if ONTOLOGY_DECLARATION_FUNCTION_NAME not in available_functions or len(declared_subjects) != 1:
        return None
    measures = tuple(
        measure
        for measure in DECLARATION_SECTIONS_BY_MEASURE
        if measure in judgment.requested_facets
    )
    if not measures:
        measures = ("declaration_detail",)
    proposal = SemanticFrameProposal(
        operation=SemanticOperation.SELECT,
        subject_constraints=(next(iter(declared_subjects)),),
        measure_concepts=measures,
        temporal_scope={},
        output_shape=SemanticOutputShape.ONTOLOGY_DECLARATION,
        evidence_requirements=(),
        unresolved_terms=(),
        clarification_requirements=(),
        clarification=None,
        investigation=None,
        confidence=judgment.confidence,
    )
    return proposal, build_semantic_frame(proposal, utterance=utterance, context=context)


def normalize_ontology_manifest_count_frame(
    proposal: SemanticFrameProposal,
    frame: SemanticProblemFrame,
    *,
    judgment: SemanticJudgmentProposal | None,
    utterance: str,
    context: tuple[str, ...],
) -> tuple[SemanticFrameProposal, SemanticProblemFrame]:
    """Bind a validated declaration-count intent to its manifest declaration kind."""

    if (
        frame.operation is not SemanticOperation.AGGREGATE
        or frame.output_shape != SemanticOutputShape.AGGREGATION_TABLE
        or frame.unresolved_terms
        or proposal.clarification_requirements
    ):
        return proposal, frame
    declaration_kind = _declaration_kind(frame, judgment)
    if declaration_kind is None:
        return proposal, frame
    updates: dict[str, Any] = {}
    updates["subject_constraints"] = (declaration_kind.value,)
    updates["measure_concepts"] = ("count",)
    normalized = proposal.model_copy(update=updates)
    return normalized, build_semantic_frame(normalized, utterance=utterance, context=context)


def _declaration_kind(
    frame: SemanticProblemFrame,
    judgment: SemanticJudgmentProposal | None,
) -> OntologyDeclarationKind | None:
    canonical_kinds = {
        declaration_kind
        for target in (() if judgment is None else judgment.targets)
        if (declaration_kind := _as_declaration_kind(target.canonical_value)) is not None
    }
    if len(canonical_kinds) > 1:
        return None
    if canonical_kinds:
        return next(iter(canonical_kinds))
    frame_kinds = {
        declaration_kind
        for subject in frame.subject_constraints
        if (declaration_kind := _as_declaration_kind(subject)) is not None
    }
    return next(iter(frame_kinds)) if len(frame_kinds) == 1 else None


def _as_declaration_kind(value: str | None) -> OntologyDeclarationKind | None:
    if value is None:
        return None
    try:
        return OntologyDeclarationKind(value)
    except ValueError:
        if not value.endswith("Type"):
            return None
    try:
        return OntologyDeclarationKind(value.removesuffix("Type").casefold())
    except ValueError:
        return None


def compile_ontology_manifest_count_plan(
    *,
    frame: SemanticProblemFrame,
    manifest: QueryManifest,
    verifier: OntologyQueryPlanVerifier,
    principal: Principal,
    purpose: str,
    evaluation_time: datetime,
) -> OntologyQueryPlan | None:
    """Build a read-only declaration count without delegating plan shape to a model."""

    if (
        frame.operation is not SemanticOperation.AGGREGATE
        or frame.output_shape != SemanticOutputShape.AGGREGATION_TABLE
        or len(frame.measure_concepts) != 1
        or frame.measure_concepts[0] != "count"
        or not frame.subject_constraints
        or not _has_manifest_function(manifest)
    ):
        return None
    canonical_kinds = tuple(_as_declaration_kind(value) for value in frame.subject_constraints)
    if any(kind is None for kind in canonical_kinds):
        return None
    kinds = tuple(kind.value for kind in canonical_kinds if kind is not None)
    if len(kinds) != len(set(kinds)):
        return None

    function_arguments: dict[str, object] = {}
    function_arguments["kinds"] = list(kinds)
    function_arguments["limit"] = 1000
    node_arguments: dict[str, object] = {}
    node_arguments["function_name"] = ONTOLOGY_MANIFEST_FUNCTION_NAME
    node_arguments["arguments"] = function_arguments
    node_arguments["dependency_arguments"] = {}
    manifest_node = QueryNodeProposal(
        node_id="ontology-manifest",
        kind=QueryNodeKind.FUNCTION,
        arguments=node_arguments,
        output_kind="query.table",
    )

    aggregate_arguments: dict[str, object] = {}
    aggregate_arguments["operation"] = "count"
    aggregate_arguments["group_by"] = ["kind"]
    aggregate_arguments["limit"] = 10
    aggregate_node = QueryNodeProposal(
        node_id="declaration-count",
        kind=QueryNodeKind.AGGREGATE,
        depends_on=(manifest_node.node_id,),
        arguments=aggregate_arguments,
        output_kind="query.table",
    )
    nodes: list[QueryNodeProposal] = []
    nodes.append(manifest_node)
    nodes.append(aggregate_node)
    proposal = QueryPlanProposal(
        nodes=tuple(nodes),
        output_node_ids=(aggregate_node.node_id,),
    )
    plan = _build_plan(
        proposal,
        frame=frame,
        manifest=manifest,
        principal=principal,
        purpose=purpose,
        evaluation_time=evaluation_time,
    )
    verified = verifier.verify(plan, manifest=manifest)
    verify_frame_plan_alignment(frame, verified, descriptors=manifest.descriptors)
    return verified


def compile_ontology_declaration_plan(
    *,
    frame: SemanticProblemFrame,
    manifest: QueryManifest,
    verifier: OntologyQueryPlanVerifier,
    principal: Principal,
    purpose: str,
    evaluation_time: datetime,
) -> OntologyQueryPlan | None:
    """Build exact declaration reads without delegating closed arguments to a model."""

    if (
        frame.operation is not SemanticOperation.SELECT
        or frame.output_shape != SemanticOutputShape.ONTOLOGY_DECLARATION
        or len(frame.subject_constraints) != 1
        or not frame.measure_concepts
        or not _has_function(manifest, ONTOLOGY_DECLARATION_FUNCTION_NAME)
    ):
        return None
    subject = frame.subject_constraints[0]
    declaration_kinds = {
        descriptor.get("kind")
        for descriptor in manifest.descriptors
        if descriptor.get("name") == subject
        and descriptor.get("kind") in {"action", "link", "object"}
    }
    if len(declaration_kinds) != 1:
        return None
    sections = {DECLARATION_SECTIONS_BY_MEASURE.get(measure) for measure in frame.measure_concepts}
    if None in sections or not sections:
        return None
    declaration_kind = next(iter(declaration_kinds))
    nodes = tuple(
        QueryNodeProposal(
            node_id=f"ontology-declaration-{section}",
            kind=QueryNodeKind.FUNCTION,
            arguments={
                "function_name": ONTOLOGY_DECLARATION_FUNCTION_NAME,
                "arguments": {
                    "kind": declaration_kind,
                    "name": subject,
                    "section": section,
                    "limit": 100,
                },
                "dependency_arguments": {},
            },
            output_kind="query.table",
        )
        for section in sorted(value for value in sections if value is not None)
    )
    proposal = QueryPlanProposal(
        nodes=nodes,
        output_node_ids=tuple(node.node_id for node in nodes),
    )
    plan = _build_plan(
        proposal,
        frame=frame,
        manifest=manifest,
        principal=principal,
        purpose=purpose,
        evaluation_time=evaluation_time,
    )
    verified = verifier.verify(plan, manifest=manifest)
    verify_frame_plan_alignment(frame, verified, descriptors=manifest.descriptors)
    return verified


def _has_manifest_function(manifest: QueryManifest) -> bool:
    return _has_function(manifest, ONTOLOGY_MANIFEST_FUNCTION_NAME)


def _has_function(manifest: QueryManifest, function_name: str) -> bool:
    return any(
        descriptor.get("kind") == "function" and descriptor.get("name") == function_name
        for descriptor in manifest.descriptors
    )
