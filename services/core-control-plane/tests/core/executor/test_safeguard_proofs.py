"""Context-bound execution safeguard proof finalization tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import Literal, cast
from uuid import UUID

import pytest
from fdai.core.executor.safeguard_proofs import (
    AuditIntentProof,
    IdempotencyReservationProof,
    LogicalTargetLockProof,
    finalize_safeguard_proof_bundle,
    full_action_digest,
)
from fdai.core.executor.safeguards import SafeguardReceipt, evaluate_pre_dispatch
from fdai.shared.contracts.models import (
    Action,
    ActionStopCondition,
    BlastRadius,
    BlastRadiusScope,
    ExecutionPath,
    Mode,
    Operation,
    RollbackKind,
    RollbackRef,
    StopConditionKind,
)

_NOW = datetime(2026, 9, 10, 4, 0, tzinfo=UTC)
_SOURCE_REVISION = "commit:" + "a" * 40


def _action(**overrides: object) -> Action:
    values: dict[str, object] = {
        "schema_version": "1.0.0",
        "action_id": UUID(int=1),
        "idempotency_key": "example-idem",
        "event_id": UUID(int=2),
        "action_type": "ops.restart-service",
        "target_resource_ref": "resource/example",
        "operation": Operation.RESTART,
        "params": {"name": "example"},
        "stop_condition": StopConditionKind.TIME_BOX_EXCEEDED_SECONDS.value,
        "stop_conditions": [
            ActionStopCondition(
                kind=StopConditionKind.TIME_BOX_EXCEEDED_SECONDS,
                seconds=60,
            )
        ],
        "rollback_ref": RollbackRef(
            kind=RollbackKind.SCRIPTED,
            reference="rollback/example",
        ),
        "blast_radius": BlastRadius(scope=BlastRadiusScope.RESOURCE, count=1),
        "mode": Mode.SHADOW,
        "citing_rules": ["rule.example"],
        "created_at": _NOW,
    }
    values.update(overrides)
    return Action.model_validate(values)


def _receipt(action: Action, path: ExecutionPath = ExecutionPath.DIRECT_API) -> SafeguardReceipt:
    receipt = evaluate_pre_dispatch(
        action,
        execution_path=path,
        plan_digest="plan-digest",
        plan_kind="test-plan",
    )
    assert isinstance(receipt, SafeguardReceipt)
    return receipt


def _proofs(
    action: Action,
    receipt: SafeguardReceipt,
):
    context = {
        "action_digest": full_action_digest(action),
        "execution_path": receipt.execution_path,
        "execution_fingerprint": receipt.execution_fingerprint,
        "source_revision": _SOURCE_REVISION,
        "completed_at": _NOW,
    }
    return (
        LogicalTargetLockProof.create(
            **context,
            lock_key=receipt.resource_lock_key,
            operation_receipt_digest="sha256:" + "1" * 64,
        ),
        IdempotencyReservationProof.create(
            **context,
            idempotency_key=receipt.idempotency_key,
            reservation_outcome="reserved",
            store_receipt_digest="sha256:" + "2" * 64,
        ),
        AuditIntentProof.create(
            **context,
            audit_entry_digest="sha256:" + "3" * 64,
            append_receipt_digest="sha256:" + "4" * 64,
        ),
    )


@pytest.mark.parametrize("path", list(ExecutionPath))
def test_finalizer_emits_canonical_no_authority_bundle(path: ExecutionPath) -> None:
    action = _action()
    receipt = _receipt(action, path)
    lock, idempotency, audit = _proofs(action, receipt)

    bundle = finalize_safeguard_proof_bundle(
        action,
        receipt=receipt,
        source_revision=_SOURCE_REVISION,
        recorded_at=_NOW,
        lock_proof=lock,
        idempotency_proof=idempotency,
        audit_intent_proof=audit,
    )

    assert bundle.execution_path.value == path.value
    assert bundle.effect_verified is False
    assert bundle.execution_authority is False
    assert bundle.approval_authority is False
    assert bundle.promotion_authority is False
    assert len(bundle.proofs) == 7


def test_full_action_digest_covers_structured_and_lineage_fields() -> None:
    action = _action()
    changed_stop = action.model_copy(
        update={
            "stop_conditions": [
                ActionStopCondition(
                    kind=StopConditionKind.TIME_BOX_EXCEEDED_SECONDS,
                    seconds=120,
                )
            ]
        }
    )
    changed_time = action.model_copy(update={"created_at": _NOW + timedelta(seconds=1)})

    assert full_action_digest(changed_stop) != full_action_digest(action)
    assert full_action_digest(changed_time) != full_action_digest(action)


def test_finalizer_rejects_cross_action_path_lock_and_audit_proofs() -> None:
    action = _action()
    receipt = _receipt(action)
    lock, idempotency, audit = _proofs(action, receipt)

    with pytest.raises(ValueError, match="action digest"):
        finalize_safeguard_proof_bundle(
            _action(params={"name": "other"}),
            receipt=receipt,
            source_revision=_SOURCE_REVISION,
            recorded_at=_NOW,
            lock_proof=lock,
            idempotency_proof=idempotency,
            audit_intent_proof=audit,
        )
    with pytest.raises(ValueError, match="target lock"):
        finalize_safeguard_proof_bundle(
            action,
            receipt=receipt,
            source_revision=_SOURCE_REVISION,
            recorded_at=_NOW,
            lock_proof=replace(
                lock,
                lock_key="fdai:resource:other",
                proof_digest=LogicalTargetLockProof.create(
                    action_digest=lock.action_digest,
                    execution_path=lock.execution_path,
                    execution_fingerprint=lock.execution_fingerprint,
                    lock_key="fdai:resource:other",
                    source_revision=lock.source_revision,
                    completed_at=lock.completed_at,
                    operation_receipt_digest=lock.operation_receipt_digest,
                ).proof_digest,
            ),
            idempotency_proof=idempotency,
            audit_intent_proof=audit,
        )
    wrong_receipt = replace(
        receipt,
        resource_lock_key="fdai:resource:other",
    )
    wrong_lock = LogicalTargetLockProof.create(
        action_digest=lock.action_digest,
        execution_path=lock.execution_path,
        execution_fingerprint=lock.execution_fingerprint,
        lock_key=wrong_receipt.resource_lock_key,
        source_revision=lock.source_revision,
        completed_at=lock.completed_at,
        operation_receipt_digest=lock.operation_receipt_digest,
    )
    with pytest.raises(ValueError, match="target lock"):
        finalize_safeguard_proof_bundle(
            action,
            receipt=wrong_receipt,
            source_revision=_SOURCE_REVISION,
            recorded_at=_NOW,
            lock_proof=wrong_lock,
            idempotency_proof=idempotency,
            audit_intent_proof=audit,
        )
    with pytest.raises(ValueError, match="completion time"):
        AuditIntentProof.create(
            action_digest=full_action_digest(action),
            execution_path=receipt.execution_path,
            execution_fingerprint=receipt.execution_fingerprint,
            audit_entry_digest="sha256:" + "3" * 64,
            source_revision=_SOURCE_REVISION,
            completed_at=datetime(2026, 9, 10),
            append_receipt_digest="sha256:" + "4" * 64,
        )


def test_proof_and_bundle_tampering_fail_closed() -> None:
    action = _action()
    receipt = _receipt(action)
    lock, idempotency, audit = _proofs(action, receipt)

    with pytest.raises(ValueError, match="digest mismatched"):
        replace(lock, proof_digest="sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="dry-run receipt"):
        finalize_safeguard_proof_bundle(
            action,
            receipt=replace(receipt, dry_run_receipt="sha256:" + "f" * 64),
            source_revision=_SOURCE_REVISION,
            recorded_at=_NOW,
            lock_proof=lock,
            idempotency_proof=idempotency,
            audit_intent_proof=audit,
        )
    with pytest.raises(ValueError, match="operation_receipt_digest"):
        LogicalTargetLockProof.create(
            action_digest=lock.action_digest,
            execution_path=lock.execution_path,
            execution_fingerprint=lock.execution_fingerprint,
            lock_key=lock.lock_key,
            source_revision=lock.source_revision,
            completed_at=lock.completed_at,
            operation_receipt_digest="",
        )
    with pytest.raises(ValueError, match="durable success"):
        IdempotencyReservationProof(
            action_digest=idempotency.action_digest,
            execution_path=idempotency.execution_path,
            execution_fingerprint=idempotency.execution_fingerprint,
            idempotency_key=idempotency.idempotency_key,
            reservation_outcome=cast(Literal["reserved", "duplicate_same"], "failed"),
            source_revision=idempotency.source_revision,
            completed_at=idempotency.completed_at,
            store_receipt_digest=idempotency.store_receipt_digest,
            proof_digest=idempotency.proof_digest,
        )
    with pytest.raises(ValueError, match="source revision"):
        AuditIntentProof.create(
            action_digest=audit.action_digest,
            execution_path=audit.execution_path,
            execution_fingerprint=audit.execution_fingerprint,
            audit_entry_digest=audit.audit_entry_digest,
            source_revision=f" {_SOURCE_REVISION} ",
            completed_at=audit.completed_at,
            append_receipt_digest=audit.append_receipt_digest,
        )
    with pytest.raises(ValueError, match="recorded_at"):
        finalize_safeguard_proof_bundle(
            action,
            receipt=receipt,
            source_revision=_SOURCE_REVISION,
            recorded_at=_NOW - timedelta(seconds=1),
            lock_proof=lock,
            idempotency_proof=idempotency,
            audit_intent_proof=audit,
        )
    future_action = action.model_copy(update={"created_at": _NOW + timedelta(seconds=1)})
    future_receipt = _receipt(future_action)
    future_lock, future_idempotency, future_audit = _proofs(future_action, future_receipt)
    with pytest.raises(ValueError, match="recorded_at"):
        finalize_safeguard_proof_bundle(
            future_action,
            receipt=future_receipt,
            source_revision=_SOURCE_REVISION,
            recorded_at=_NOW,
            lock_proof=future_lock,
            idempotency_proof=future_idempotency,
            audit_intent_proof=future_audit,
        )

    offset = timezone(timedelta(hours=9))
    bundle = finalize_safeguard_proof_bundle(
        action,
        receipt=receipt,
        source_revision=_SOURCE_REVISION,
        recorded_at=_NOW.astimezone(offset),
        lock_proof=lock,
        idempotency_proof=idempotency,
        audit_intent_proof=audit,
    )
    assert bundle.recorded_at == _NOW
