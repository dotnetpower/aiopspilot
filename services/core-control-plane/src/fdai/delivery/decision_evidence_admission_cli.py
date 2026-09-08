"""Retain an independently verified decision-evidence bundle in durable state."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from fdai_service_contracts.decision_evidence import (
    DecisionCriticalEvidenceReceipt,
    LiveEvidenceClaimRequirement,
)
from fdai_service_contracts.decision_evidence_verification import (
    DecisionEvidenceVerificationBundle,
)

from fdai.core.readiness.decision_evidence import DecisionEvidenceReadinessGate
from fdai.delivery.persistence.postgres import PostgresStateStore, PostgresStateStoreConfig
from fdai.delivery.persistence.state_store_decision_evidence import (
    StateStoreDecisionEvidenceAdmissionRecorder,
)
from fdai.shared.providers.decision_evidence_verifier import (
    DecisionEvidenceVerifierBinding,
    DecisionEvidenceVerifierRegistry,
)
from fdai.shared.providers.state_store import StateStore

_DSN_ENV = "FDAI_STATE_STORE_DSN"


class DecisionEvidenceRetentionError(RuntimeError):
    """A supplied receipt and proof bundle cannot produce a trusted admission."""


class _RetainedBundleVerifier:
    def __init__(self, bundle: DecisionEvidenceVerificationBundle) -> None:
        self._bundle = bundle

    async def verify(
        self,
        receipt: DecisionCriticalEvidenceReceipt,
        *,
        trust_anchor_id: str,
    ) -> DecisionEvidenceVerificationBundle:
        del receipt, trust_anchor_id
        return self._bundle


async def retain_decision_evidence(
    *,
    receipt: DecisionCriticalEvidenceReceipt,
    requirement: LiveEvidenceClaimRequirement,
    bundle: DecisionEvidenceVerificationBundle,
    evaluated_at: datetime,
    store: StateStore,
) -> bool:
    """Validate one externally attested bundle and retain its admission once."""

    gate = DecisionEvidenceReadinessGate(
        registry=DecisionEvidenceVerifierRegistry(
            (
                DecisionEvidenceVerifierBinding(
                    authority_class=receipt.authority_class,
                    method_id=receipt.method_id,
                    verifier_id=bundle.verifier_id,
                    verifier_version=bundle.verifier_version,
                    trust_anchor_id=bundle.trust_anchor_id,
                    verifier=_RetainedBundleVerifier(bundle),
                    valid_from=bundle.verified_at,
                    valid_until=bundle.valid_until,
                ),
            )
        )
    )
    result = await gate.evaluate(
        receipt,
        requirement,
        evaluated_at=evaluated_at,
    )
    if not result.eligible:
        details = ",".join(result.rejection_details)
        suffix = f":{details}" if details else ""
        raise DecisionEvidenceRetentionError(
            f"decision evidence admission rejected:{result.reason.value}{suffix}"
        )
    return await StateStoreDecisionEvidenceAdmissionRecorder(store=store).retain(
        receipt,
        result,
    )


def _load(path: Path) -> object:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise DecisionEvidenceRetentionError(
            "decision evidence input MUST be a bounded regular file"
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DecisionEvidenceRetentionError("decision evidence input is invalid JSON") from exc


async def _run(args: argparse.Namespace) -> dict[str, object]:
    try:
        receipt = DecisionCriticalEvidenceReceipt.model_validate(_load(args.receipt))
        requirement = LiveEvidenceClaimRequirement.model_validate(_load(args.requirement))
        bundle = DecisionEvidenceVerificationBundle.model_validate(_load(args.bundle))
        evaluated_at = datetime.fromisoformat(args.evaluated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DecisionEvidenceRetentionError(
            "decision evidence input does not match its contract"
        ) from exc
    dsn = os.environ.get(_DSN_ENV, "").strip()
    if not dsn:
        raise DecisionEvidenceRetentionError(f"{_DSN_ENV} is required")
    created = await retain_decision_evidence(
        receipt=receipt,
        requirement=requirement,
        bundle=bundle,
        evaluated_at=evaluated_at,
        store=PostgresStateStore(
            config=PostgresStateStoreConfig(
                dsn=dsn.replace("postgresql+psycopg://", "postgresql://", 1)
            )
        ),
    )
    return {
        "schema_version": "fdai.decision-evidence-retention-result.v1",
        "created": created,
        "receipt_digest": receipt.receipt_digest,
        "verification_bundle_digest": bundle.bundle_digest,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    """Validate CLI inputs, retain one admission, and print a sanitized result."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--requirement", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--evaluated-at", required=True)
    args = parser.parse_args()
    try:
        result = asyncio.run(_run(args))
    except DecisionEvidenceRetentionError as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["DecisionEvidenceRetentionError", "retain_decision_evidence"]
