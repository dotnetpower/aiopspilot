"""Governed decision-evidence retention entry-point tests."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fdai.delivery.decision_evidence_admission_cli import (
    DecisionEvidenceRetentionError,
    retain_decision_evidence,
)
from fdai.delivery.persistence.state_store_decision_evidence import (
    StateStoreDecisionEvidenceAdmissionProvider,
)
from fdai.shared.providers.testing.state_store import InMemoryStateStore
from fdai_service_contracts.decision_evidence_verification import (
    DecisionEvidenceVerificationBundle,
)

from tests.core.readiness.test_decision_evidence import (
    _NOW,
    _bundle,
    _receipt,
    _requirement,
)


def _self_verified_bundle(receipt):
    original = _bundle(receipt)
    verifier_id = receipt.producer_id
    proofs = tuple(
        proof.model_copy(update={"verifier_id": verifier_id}) for proof in original.proofs
    )
    return DecisionEvidenceVerificationBundle.create(
        receipt_digest=receipt.receipt_digest,
        verifier_id=verifier_id,
        verifier_version=original.verifier_version,
        trust_anchor_id=original.trust_anchor_id,
        verified_at=original.verified_at,
        valid_until=original.valid_until,
        proofs=proofs,
    )


async def test_retention_entry_point_persists_an_eligible_bundle() -> None:
    store = InMemoryStateStore()
    receipt = _receipt()

    created = await retain_decision_evidence(
        receipt=receipt,
        requirement=_requirement(),
        bundle=_bundle(receipt),
        evaluated_at=_NOW + timedelta(minutes=3),
        store=store,
    )
    admission = await StateStoreDecisionEvidenceAdmissionProvider(
        store=store,
        clock=lambda: _NOW + timedelta(minutes=4),
    ).admit(
        evidence_digest=receipt.evidence_digest,
        scope_digest=receipt.scope_digest,
        purpose_id=receipt.purpose_id,
        source_revision=receipt.source_revision,
    )

    assert created is True
    assert admission is not None
    assert admission.execution_authority is admission.promotion_authority is False


async def test_retention_entry_point_rejects_self_verification() -> None:
    store = InMemoryStateStore()
    receipt = _receipt()

    with pytest.raises(DecisionEvidenceRetentionError, match="self_verification"):
        await retain_decision_evidence(
            receipt=receipt,
            requirement=_requirement(),
            bundle=_self_verified_bundle(receipt),
            evaluated_at=_NOW + timedelta(minutes=3),
            store=store,
        )


async def test_retention_entry_point_rejects_expired_bundle() -> None:
    store = InMemoryStateStore()
    receipt = _receipt()

    with pytest.raises(DecisionEvidenceRetentionError, match="untrusted_verifier"):
        await retain_decision_evidence(
            receipt=receipt,
            requirement=_requirement(),
            bundle=_bundle(receipt),
            evaluated_at=_NOW + timedelta(minutes=9),
            store=store,
        )
