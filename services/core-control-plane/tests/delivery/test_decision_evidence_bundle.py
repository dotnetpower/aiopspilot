"""Protected decision-evidence bundle builder tests."""

from __future__ import annotations

import importlib.util
import sys
from datetime import timedelta
from pathlib import Path
from types import ModuleType

import pytest
from fdai_service_contracts.decision_evidence_verification import (
    EvidenceVerificationProofKind,
)

from tests.core.readiness.test_decision_evidence import (
    _NOW,
    _bundle,
    _receipt,
    _requirement,
)

_SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "scripts"
    / "deployment"
    / "azure"
    / "decision_evidence_bundle.py"
)


@pytest.fixture(scope="module")
def builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("decision_evidence_bundle_script", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


async def test_builds_bundle_and_content_addressed_admission_record(
    builder: ModuleType,
) -> None:
    receipt = _receipt()
    candidate = _bundle(receipt)
    authentication = next(
        proof
        for proof in candidate.proofs
        if proof.kind is EvidenceVerificationProofKind.AUTHENTICATION
    )
    readback = tuple(
        proof
        for proof in candidate.proofs
        if proof.kind is not EvidenceVerificationProofKind.AUTHENTICATION
    )

    bundle, record = await builder.build_decision_evidence_artifacts(
        receipt=receipt,
        requirement=_requirement(),
        authentication_proof=authentication,
        readback_proofs=readback,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert bundle == candidate
    assert record["receipt"]["receipt_digest"] == receipt.receipt_digest
    assert record["admission"]["execution_authority"] is False
    assert record["admission"]["promotion_authority"] is False


async def test_rejects_a_missing_readback_proof(builder: ModuleType) -> None:
    receipt = _receipt()
    candidate = _bundle(receipt)
    authentication = next(
        proof
        for proof in candidate.proofs
        if proof.kind is EvidenceVerificationProofKind.AUTHENTICATION
    )
    readback = tuple(
        proof
        for proof in candidate.proofs
        if proof.kind is not EvidenceVerificationProofKind.AUTHENTICATION
    )

    with pytest.raises(builder.DecisionEvidenceBundleError, match="requires one"):
        await builder.build_decision_evidence_artifacts(
            receipt=receipt,
            requirement=_requirement(),
            authentication_proof=authentication,
            readback_proofs=readback[:-1],
            evaluated_at=_NOW + timedelta(minutes=3),
        )


async def test_rejects_expired_proof_window(builder: ModuleType) -> None:
    receipt = _receipt()
    candidate = _bundle(receipt)
    authentication = next(
        proof
        for proof in candidate.proofs
        if proof.kind is EvidenceVerificationProofKind.AUTHENTICATION
    )
    readback = tuple(
        proof
        for proof in candidate.proofs
        if proof.kind is not EvidenceVerificationProofKind.AUTHENTICATION
    )

    with pytest.raises(builder.DecisionEvidenceBundleError, match="untrusted_verifier"):
        await builder.build_decision_evidence_artifacts(
            receipt=receipt,
            requirement=_requirement(),
            authentication_proof=authentication,
            readback_proofs=readback,
            evaluated_at=_NOW + timedelta(minutes=9),
        )
