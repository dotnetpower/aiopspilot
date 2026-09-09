"""Failure-boundary and replay tests for shared WAF and CAF assessment."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fdai.core.framework_assessment import (
    FRAMEWORK_ASSESSMENT_TOPIC,
    FrameworkApplicabilityDecision,
    FrameworkApplicabilityStatus,
    FrameworkAssessmentProfile,
    FrameworkAssessmentRequest,
    FrameworkAssessmentRuntime,
    FrameworkAssessmentService,
    FrameworkEvaluationStatus,
    FrameworkEvidenceReceipt,
    FrameworkOwnerBinding,
    FrameworkSatisfactionStatus,
    FrameworkTradeoffRecord,
    replay_framework_assessment,
)
from fdai.rule_catalog.schema.framework_assessment import (
    FrameworkAssessmentCatalog,
    FrameworkEvidenceRole,
    FrameworkGenerationContract,
    FrameworkProcessPhase,
    FrameworkScopeKind,
    canonical_digest,
    load_framework_assessment_catalog,
)

ROOT = Path(__file__).resolve().parents[5]
GENERATED = ROOT / "rule-catalog/framework-assessments/generated"
NOW = datetime(2026, 9, 10, 1, 0, tzinfo=UTC)
SCOPE_DIGEST = canonical_digest({"scope": "example"})


def _catalog(framework_id: str) -> FrameworkAssessmentCatalog:
    return load_framework_assessment_catalog(GENERATED / f"{framework_id}.json")


def _profile(
    catalog: FrameworkAssessmentCatalog,
    *,
    not_applicable: str | None = None,
    na_expired: bool = False,
) -> FrameworkAssessmentProfile:
    decisions = []
    owners = []
    for control in catalog.controls:
        if control.control_id == not_applicable:
            decision = FrameworkApplicabilityDecision(
                control_id=control.control_id,
                status=FrameworkApplicabilityStatus.NOT_APPLICABLE,
                requested_by="requester@example.com",
                owner_slot=control.owner_slot,
                cadence_days=control.cadence_days,
                justification="The typed deployment profile excludes this area.",
                approved_by="approver@example.com",
                approved_at=NOW - timedelta(days=10),
                expires_at=NOW - timedelta(seconds=1) if na_expired else NOW + timedelta(days=30),
            )
        else:
            decision = FrameworkApplicabilityDecision(
                control_id=control.control_id,
                status=FrameworkApplicabilityStatus.APPLICABLE,
                requested_by="requester@example.com",
                owner_slot=control.owner_slot,
                cadence_days=control.cadence_days,
            )
        decisions.append(decision)
        owners.append(
            FrameworkOwnerBinding(
                control_id=control.control_id,
                owner_slot=control.owner_slot,
                owner_identity=f"{control.owner_slot}@example.com",
            )
        )
    is_waf = catalog.framework_id == "azure-waf"
    return FrameworkAssessmentProfile.create(
        profile_id=f"{catalog.framework_id}-profile",
        framework_id=catalog.framework_id,
        framework_version=catalog.framework_version,
        catalog_digest=catalog.catalog_digest,
        scope_kind=(FrameworkScopeKind.WORKLOAD if is_waf else FrameworkScopeKind.CLOUD_ESTATE),
        scope_digest=SCOPE_DIGEST,
        ontology_release="2026.09",
        applicability=tuple(decisions),
        owners=tuple(owners),
        reviewed_by="reviewer@example.com",
        reviewed_at=NOW - timedelta(days=1),
        inventory_generation="inventory-1" if is_waf else None,
        hierarchy_generation=None if is_waf else "hierarchy-1",
        operating_model=None if is_waf else "platform-operating-model",
        environment_classes=() if is_waf else ("development",),
        regulatory_context=(),
    )


def _receipt(
    catalog: FrameworkAssessmentCatalog,
    control_id: str,
    requirement_index: int,
) -> FrameworkEvidenceReceipt:
    control = next(item for item in catalog.controls if item.control_id == control_id)
    requirement = control.evidence[requirement_index]
    assert requirement.authoritative_producer is not None
    return FrameworkEvidenceReceipt(
        framework_id=catalog.framework_id,
        control_id=control_id,
        requirement_id=requirement.requirement_id,
        evidence_ref=f"evidence://{control_id}/{requirement_index}",
        evidence_kind=requirement.kind.value,
        producer=requirement.authoritative_producer,
        source_identity="observer@example.com",
        scope_digest=SCOPE_DIGEST,
        observed_at=NOW - timedelta(minutes=2),
        recorded_at=NOW - timedelta(minutes=1),
        evidence_digest=canonical_digest(
            {"control_id": control_id, "requirement": requirement_index}
        ),
        freshness_ceiling_seconds=requirement.freshness_ceiling_seconds,
        complete=True,
        truncated=False,
        conflicting=False,
        synthetic=False,
        provider_error=None,
        outcome=FrameworkSatisfactionStatus.SATISFIED,
        evidence_role=requirement.evidence_role,
        process_phase=requirement.process_phase,
        inventory_generation=(
            "inventory-1"
            if requirement.generation_contract is FrameworkGenerationContract.INVENTORY
            else None
        ),
        hierarchy_generation=(
            "hierarchy-1"
            if requirement.generation_contract is FrameworkGenerationContract.HIERARCHY
            else None
        ),
    )


def _control_receipts(
    catalog: FrameworkAssessmentCatalog,
    control_id: str,
) -> tuple[FrameworkEvidenceReceipt, ...]:
    control = next(item for item in catalog.controls if item.control_id == control_id)
    return tuple(_receipt(catalog, control_id, index) for index in range(len(control.evidence)))


def _request(
    catalog: FrameworkAssessmentCatalog,
    evidence: tuple[FrameworkEvidenceReceipt, ...] = (),
    *,
    profile: FrameworkAssessmentProfile | None = None,
    tradeoffs: tuple[FrameworkTradeoffRecord, ...] = (),
) -> FrameworkAssessmentRequest:
    return FrameworkAssessmentRequest(
        assessment_id=f"assessment-{catalog.framework_id}",
        profile=profile or _profile(catalog),
        evaluated_at=NOW,
        recorded_at=NOW,
        evidence=tuple(
            sorted(
                evidence,
                key=lambda item: (
                    item.control_id,
                    item.requirement_id,
                    item.evidence_ref,
                ),
            )
        ),
        tradeoffs=tradeoffs,
    )


def _result_control(result: Any, control_id: str):
    return next(item for item in result.controls if item.control_id == control_id)


def test_complete_exact_scope_waf_evidence_satisfies_one_control() -> None:
    catalog = _catalog("azure-waf")
    control_id = catalog.controls[0].control_id

    result = FrameworkAssessmentRuntime(catalog).assess(
        _request(catalog, _control_receipts(catalog, control_id))
    )

    control = _result_control(result, control_id)
    assert len(result.controls) == 59
    assert control.evaluation is FrameworkEvaluationStatus.EVALUATED
    assert control.satisfaction is FrameworkSatisfactionStatus.SATISFIED
    assert control.evidence_complete is True
    assert result.execution_authority is False


@pytest.mark.parametrize(
    ("change", "limitation"),
    [
        ({"complete": False}, "incomplete_evidence"),
        ({"truncated": True}, "truncated_evidence"),
        ({"conflicting": True}, "conflicting_evidence"),
        ({"synthetic": True}, "synthetic_evidence"),
        ({"provider_error": "unsupported_resource_type"}, "provider_error"),
        ({"scope_digest": canonical_digest({"scope": "wrong"})}, "wrong_scope"),
        ({"inventory_generation": "inventory-stale"}, "wrong_inventory_generation"),
    ],
)
def test_rule_evidence_failure_boundaries_remain_unknown(
    change: dict[str, object],
    limitation: str,
) -> None:
    catalog = _catalog("azure-waf")
    control = next(
        item
        for item in catalog.controls
        if any(requirement.kind.value == "rule" for requirement in item.evidence)
    )
    receipts = list(_control_receipts(catalog, control.control_id))
    index = next(
        index
        for index, requirement in enumerate(control.evidence)
        if requirement.kind.value == "rule"
    )
    receipts[index] = replace(receipts[index], **change)

    result = FrameworkAssessmentRuntime(catalog).assess(_request(catalog, tuple(receipts)))

    assessed = _result_control(result, control.control_id)
    assert assessed.evaluation is FrameworkEvaluationStatus.NOT_EVALUATED
    assert assessed.satisfaction is FrameworkSatisfactionStatus.UNKNOWN
    assert limitation in assessed.limitations


def test_stale_rule_evidence_remains_unknown() -> None:
    catalog = _catalog("azure-waf")
    control = next(
        item
        for item in catalog.controls
        if any(requirement.kind.value == "rule" for requirement in item.evidence)
    )
    receipts = list(_control_receipts(catalog, control.control_id))
    index = next(
        index
        for index, requirement in enumerate(control.evidence)
        if requirement.kind.value == "rule"
    )
    receipt = receipts[index]
    receipts[index] = replace(
        receipt,
        observed_at=NOW - timedelta(seconds=receipt.freshness_ceiling_seconds + 1),
        recorded_at=NOW - timedelta(seconds=receipt.freshness_ceiling_seconds),
    )

    result = FrameworkAssessmentRuntime(catalog).assess(_request(catalog, tuple(receipts)))

    assessed = _result_control(result, control.control_id)
    assert assessed.satisfaction is FrameworkSatisfactionStatus.UNKNOWN
    assert "stale_evidence" in assessed.limitations


def test_supporting_external_evidence_cannot_establish_satisfaction() -> None:
    catalog = _catalog("azure-waf")
    control_id = catalog.controls[0].control_id
    supporting = tuple(
        replace(item, evidence_role=FrameworkEvidenceRole.SUPPORTING_ONLY)
        for item in _control_receipts(catalog, control_id)
    )

    result = FrameworkAssessmentRuntime(catalog).assess(_request(catalog, supporting))

    control = _result_control(result, control_id)
    assert control.satisfaction is FrameworkSatisfactionStatus.UNKNOWN
    assert "supporting_evidence_only" in control.limitations


def test_approved_not_applicable_is_separate_from_missing_evidence() -> None:
    catalog = _catalog("azure-waf")
    control_id = catalog.controls[0].control_id

    result = FrameworkAssessmentRuntime(catalog).assess(
        _request(catalog, profile=_profile(catalog, not_applicable=control_id))
    )
    expired = FrameworkAssessmentRuntime(catalog).assess(
        _request(
            catalog,
            profile=_profile(catalog, not_applicable=control_id, na_expired=True),
        )
    )

    assert _result_control(result, control_id).satisfaction is (
        FrameworkSatisfactionStatus.NOT_APPLICABLE
    )
    assert _result_control(expired, control_id).satisfaction is (
        FrameworkSatisfactionStatus.UNKNOWN
    )


@pytest.mark.parametrize(
    "missing_phase",
    [FrameworkProcessPhase.PROCEDURE, FrameworkProcessPhase.EXECUTION],
)
def test_caf_process_controls_require_procedure_and_execution(
    missing_phase: FrameworkProcessPhase,
) -> None:
    catalog = _catalog("azure-caf")
    control_id = "strategy"
    complete = _control_receipts(catalog, control_id)
    missing = tuple(item for item in complete if item.process_phase is not missing_phase)

    satisfied = FrameworkAssessmentRuntime(catalog).assess(_request(catalog, complete))
    unknown = FrameworkAssessmentRuntime(catalog).assess(_request(catalog, missing))

    assert _result_control(satisfied, control_id).satisfaction is (
        FrameworkSatisfactionStatus.SATISFIED
    )
    assert _result_control(unknown, control_id).satisfaction is (
        FrameworkSatisfactionStatus.UNKNOWN
    )


def test_tradeoff_is_retained_without_downgrading_failed_control() -> None:
    catalog = _catalog("azure-waf")
    control_id = catalog.controls[0].control_id
    receipts = list(_control_receipts(catalog, control_id))
    receipts[0] = replace(
        receipts[0],
        outcome=FrameworkSatisfactionStatus.FAILED,
    )
    tradeoff = FrameworkTradeoffRecord(
        tradeoff_id="tradeoff-1",
        scope_digest=SCOPE_DIGEST,
        affected_control_ids=(control_id,),
        decision_owner="architecture-owner@example.com",
        rationale_digest=canonical_digest({"reason": "reviewed"}),
        approved_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=30),
    )

    result = FrameworkAssessmentRuntime(catalog).assess(
        _request(catalog, tuple(receipts), tradeoffs=(tradeoff,))
    )

    assert _result_control(result, control_id).satisfaction is (FrameworkSatisfactionStatus.FAILED)
    assert result.tradeoffs == (tradeoff,)


def test_assessment_replay_is_deterministic() -> None:
    catalog = _catalog("azure-caf")
    request = _request(catalog, _control_receipts(catalog, "ready"))
    runtime = FrameworkAssessmentRuntime(catalog)
    first = runtime.assess(request)

    second = replay_framework_assessment(runtime, request, first.result_digest)

    assert second == first
    with pytest.raises(ValueError, match="digest mismatch"):
        replay_framework_assessment(runtime, request, canonical_digest({"wrong": True}))


class _StateStore:
    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

    async def append_audit_entry(self, entry: Mapping[str, object]) -> None:
        self.entries.append(dict(entry))


class _EventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, dict[str, object]]] = []

    async def publish(
        self,
        topic: str,
        key: str,
        payload: Mapping[str, object],
    ) -> object:
        self.published.append((topic, key, dict(payload)))
        return object()


async def test_service_audits_before_publishing_no_authority_result() -> None:
    catalog = _catalog("azure-caf")
    state_store = _StateStore()
    event_bus = _EventBus()
    service = FrameworkAssessmentService(
        FrameworkAssessmentRuntime(catalog),
        state_store,
        event_bus,
    )

    result = await service.assess(_request(catalog))

    assert state_store.entries[0]["result_digest"] == result.result_digest
    assert event_bus.published[0][0] == FRAMEWORK_ASSESSMENT_TOPIC
    assert event_bus.published[0][2]["execution_authority"] is False
