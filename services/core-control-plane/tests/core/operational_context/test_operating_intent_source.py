"""Fail-closed admission for the deployment-owned six-type operating-intent source."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fdai.core.operational_context.operating_intent_source import (
    OperatingIntentSourceBinding,
    OperatingIntentSourceError,
    validate_operating_intent_snapshot,
)
from fdai.shared.providers.ontology_instance import OntologyObjectRecord
from fdai.shared.providers.operating_model import (
    OperatingIntentSourceProvenance,
    OperatingModelSnapshot,
    operating_model_snapshot_digest,
)

_NOW = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
_EFFECTIVE_FROM = "2026-08-27T00:00:00+00:00"
_REVISION = "operating-intent-revision-1"


def _objective(
    object_id: str, object_type: str, *, effective_from: str = _EFFECTIVE_FROM
) -> OntologyObjectRecord:
    return OntologyObjectRecord(
        id=object_id,
        object_type=object_type,
        properties={
            "id": object_id,
            "objective_kind": "availability",
            "metric": "availability",
            "unit": "ratio",
            "target": 0.999,
            "window_seconds": 2592000,
            "measurement_source_ref": "source:service-objectives",
            "freshness_seconds": 86400,
            "effective_from": effective_from,
        },
    )


def _recovery_objective(effective_from: str = _EFFECTIVE_FROM) -> OntologyObjectRecord:
    return OntologyObjectRecord(
        id="recovery-objective-1",
        object_type="RecoveryObjective",
        properties={
            "id": "recovery-objective-1",
            "rto_seconds": 3600,
            "rpo_seconds": 300,
            "measurement_source_ref": "source:recovery-objectives",
            "freshness_seconds": 86400,
            "effective_from": effective_from,
        },
    )


def _cost_objective(effective_from: str = _EFFECTIVE_FROM) -> OntologyObjectRecord:
    return OntologyObjectRecord(
        id="cost-objective-1",
        object_type="CostObjective",
        properties={
            "id": "cost-objective-1",
            "objective_kind": "monthly_budget",
            "currency": "USD",
            "target": 1000,
            "period_seconds": 2592000,
            "measurement_source_ref": "source:cost-objectives",
            "freshness_seconds": 86400,
            "effective_from": effective_from,
        },
    )


def _architecture_constraint(effective_from: str = _EFFECTIVE_FROM) -> OntologyObjectRecord:
    return OntologyObjectRecord(
        id="architecture-constraint-1",
        object_type="ArchitectureConstraint",
        properties={
            "id": "architecture-constraint-1",
            "constraint_kind": "network_isolation",
            "expression_ref": "policy:network-isolation",
            "severity": "high",
            "effective_from": effective_from,
        },
    )


def _ownership(effective_from: str = _EFFECTIVE_FROM) -> OntologyObjectRecord:
    return OntologyObjectRecord(
        id="ownership-1",
        object_type="Ownership",
        properties={
            "id": "ownership-1",
            "owner_ref": "group:operations-owner",
            "escalation_ref": "route:on-call",
            "effective_from": effective_from,
            "source_ref": "source:service-catalog",
        },
    )


def _change_window(
    effective_from: str = _EFFECTIVE_FROM,
    effective_to: str = "2026-09-30T00:00:00+00:00",
) -> OntologyObjectRecord:
    return OntologyObjectRecord(
        id="change-window-1",
        object_type="ChangeWindow",
        properties={
            "id": "change-window-1",
            "window_kind": "maintenance",
            "scope_ref": "scope:example",
            "status": "approved",
            "effective_from": effective_from,
            "effective_to": effective_to,
            "policy_ref": "policy:change-window",
        },
    )


def _complete_objects() -> tuple[OntologyObjectRecord, ...]:
    return (
        _objective("service-objective-1", "ServiceObjective"),
        _recovery_objective(),
        _cost_objective(),
        _architecture_constraint(),
        _ownership(),
        _change_window(),
    )


def _snapshot(objects: tuple[OntologyObjectRecord, ...]) -> OperatingModelSnapshot:
    return OperatingModelSnapshot(source_revision=_REVISION, objects=objects, links=())


def _provenance(resolved_ref: str = _REVISION) -> OperatingIntentSourceProvenance:
    return OperatingIntentSourceProvenance(
        source_url="https://example.invalid/operating-intent-source",
        resolved_ref=resolved_ref,
        retrieved_at=_NOW,
    )


def _binding(
    snapshot: OperatingModelSnapshot, *, expected_revision: str = _REVISION
) -> OperatingIntentSourceBinding:
    return OperatingIntentSourceBinding(
        expected_revision=expected_revision,
        expected_sha256=operating_model_snapshot_digest(snapshot),
    )


def test_complete_current_source_passes() -> None:
    snapshot = _snapshot(_complete_objects())
    validate_operating_intent_snapshot(
        snapshot,
        provenance=_provenance(),
        binding=_binding(snapshot),
        now=_NOW,
    )


def test_missing_required_type_fails_closed() -> None:
    objects = _complete_objects()[:-1]  # drop ChangeWindow
    snapshot = _snapshot(objects)
    binding = OperatingIntentSourceBinding(
        expected_revision=_REVISION,
        expected_sha256=operating_model_snapshot_digest(snapshot),
    )
    with pytest.raises(OperatingIntentSourceError, match="missing required type 'ChangeWindow'"):
        validate_operating_intent_snapshot(
            snapshot, provenance=_provenance(), binding=binding, now=_NOW
        )


def test_duplicate_required_type_fails_closed() -> None:
    extra = _objective("service-objective-2", "ServiceObjective")
    objects = (*_complete_objects(), extra)
    snapshot = _snapshot(objects)
    binding = _binding(snapshot)
    with pytest.raises(OperatingIntentSourceError, match="duplicate"):
        validate_operating_intent_snapshot(
            snapshot, provenance=_provenance(), binding=binding, now=_NOW
        )


def test_stale_change_window_fails_closed() -> None:
    objects = (
        *_complete_objects()[:-1],
        _change_window(effective_to="2026-08-27T06:00:00+00:00"),
    )
    snapshot = _snapshot(objects)
    binding = _binding(snapshot)
    with pytest.raises(OperatingIntentSourceError, match="not currently effective"):
        validate_operating_intent_snapshot(
            snapshot, provenance=_provenance(), binding=binding, now=_NOW
        )


def test_stale_freshness_exceeded_fails_closed() -> None:
    objects = (
        _objective(
            "service-objective-1", "ServiceObjective", effective_from="2026-01-01T00:00:00+00:00"
        ),
        _recovery_objective(),
        _cost_objective(),
        _architecture_constraint(),
        _ownership(),
        _change_window(),
    )
    snapshot = _snapshot(objects)
    binding = _binding(snapshot)
    with pytest.raises(OperatingIntentSourceError, match="freshness_seconds"):
        validate_operating_intent_snapshot(
            snapshot, provenance=_provenance(), binding=binding, now=_NOW
        )


def test_not_yet_effective_fails_closed() -> None:
    objects = (
        *_complete_objects()[:-1],
        _change_window(
            effective_from="2026-12-01T00:00:00+00:00", effective_to="2026-12-02T00:00:00+00:00"
        ),
    )
    snapshot = _snapshot(objects)
    binding = _binding(snapshot)
    with pytest.raises(OperatingIntentSourceError, match="not currently effective"):
        validate_operating_intent_snapshot(
            snapshot, provenance=_provenance(), binding=binding, now=_NOW
        )


def test_cross_release_revision_mismatch_fails_closed() -> None:
    snapshot = _snapshot(_complete_objects())
    binding = _binding(snapshot, expected_revision="operating-intent-revision-2")
    with pytest.raises(OperatingIntentSourceError, match="revision does not match"):
        validate_operating_intent_snapshot(
            snapshot, provenance=_provenance(), binding=binding, now=_NOW
        )


def test_cross_release_provenance_mismatch_fails_closed() -> None:
    snapshot = _snapshot(_complete_objects())
    binding = _binding(snapshot)
    with pytest.raises(OperatingIntentSourceError, match="resolved_ref does not match"):
        validate_operating_intent_snapshot(
            snapshot,
            provenance=_provenance(resolved_ref="operating-intent-revision-2"),
            binding=binding,
            now=_NOW,
        )


def test_cross_release_digest_mismatch_fails_closed() -> None:
    snapshot = _snapshot(_complete_objects())
    tampered = _snapshot(_complete_objects()[:-1])
    binding = OperatingIntentSourceBinding(
        expected_revision=_REVISION,
        expected_sha256=operating_model_snapshot_digest(tampered),
    )
    with pytest.raises(OperatingIntentSourceError, match="content digest does not match"):
        validate_operating_intent_snapshot(
            snapshot, provenance=_provenance(), binding=binding, now=_NOW
        )


def test_binding_rejects_malformed_sha256() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        OperatingIntentSourceBinding(expected_revision=_REVISION, expected_sha256="not-a-digest")


def test_binding_rejects_empty_revision() -> None:
    with pytest.raises(ValueError, match="expected_revision"):
        OperatingIntentSourceBinding(
            expected_revision="   ",
            expected_sha256=f"sha256:{'0' * 64}",
        )


def test_binding_rejects_unknown_expected_count_type() -> None:
    with pytest.raises(ValueError, match="not a required"):
        OperatingIntentSourceBinding(
            expected_revision=_REVISION,
            expected_sha256=f"sha256:{'0' * 64}",
            expected_instance_counts={"Resource": 1},
        )


def test_binding_rejects_non_positive_expected_count() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        OperatingIntentSourceBinding(
            expected_revision=_REVISION,
            expected_sha256=f"sha256:{'0' * 64}",
            expected_instance_counts={"ServiceObjective": 0},
        )


def test_binding_rejects_non_integer_expected_count() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        OperatingIntentSourceBinding(
            expected_revision=_REVISION,
            expected_sha256=f"sha256:{'0' * 64}",
            expected_instance_counts={"ServiceObjective": "1"},  # type: ignore[dict-item]
        )


def test_expected_instance_counts_permit_a_reviewed_extra_instance() -> None:
    extra = _objective("service-objective-2", "ServiceObjective")
    objects = (*_complete_objects(), extra)
    snapshot = _snapshot(objects)
    binding = OperatingIntentSourceBinding(
        expected_revision=_REVISION,
        expected_sha256=operating_model_snapshot_digest(snapshot),
        expected_instance_counts={"ServiceObjective": 2},
    )
    validate_operating_intent_snapshot(
        snapshot, provenance=_provenance(), binding=binding, now=_NOW
    )
