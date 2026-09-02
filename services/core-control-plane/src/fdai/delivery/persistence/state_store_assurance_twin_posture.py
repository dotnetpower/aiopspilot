"""Durable Assurance Twin posture/review projection over the shared StateStore.

Persists the twin's already-computed
:class:`~fdai.core.assurance_twin.report.PostureAssessmentReport` (latest
per scope) and ambient :class:`~fdai.shared.providers.iac_review.IacReview`
(one row per ``review_key``) through the generic key-value ``StateStore``
seam - the same durable contract
``fdai/core/readiness/detection.py`` and
``fdai/core/assurance_twin/trajectory_ledger.py`` already use. Operator API
reads these rows directly (same physical table, service-owned role); this
module never calls the Operator API or another service in-process.

Design invariants
------------------

- **Durable-first**: the report/review body is the authoritative record;
  the bus activity tip built in ``core/assurance_twin/posture_activity.py``
  only announces that this durable write happened.
- **Read-only surface**: this ledger never judges, approves, or executes;
  it stores exactly the report/review the twin already computed.
- **Idempotent by identity, fail-closed on conflict**: a posture report
  overwrites the prior snapshot for its ``scope`` (latest-wins, matching
  ``StateStore.write_state`` semantics). A change review is written once per
  ``review_key``. Redelivery of an identical review body is an idempotent
  no-op; a *different* body under the same ``review_key`` is a conflict -
  the stored body is never replaced and the caller MUST render the row as
  unavailable instead of publishing a second, contradictory truth.
- **Replayable provenance**: every row carries the bounded activity and
  correlation identity of the record call plus the SHA-256 digest of the
  exact evidence body, so an Operator API reader can verify that a
  published ``agent.operational-activity`` tip and a rendered report
  describe the same evidence. Digests and identifiers only - no finding
  text, resource value, or customer identifier is added here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fdai.core.assurance_twin.report import PostureAssessmentReport
from fdai.shared.providers.iac_review import IacReview
from fdai.shared.providers.state_store import StateStore

POSTURE_REPORT_STATE_PREFIX = "runtime:assurance-twin-posture:"
CHANGE_REVIEW_STATE_PREFIX = "runtime:assurance-twin-review:"

#: Provenance fields describe *this* write, not the twin's evidence body, so
#: they are excluded before the body digest is computed. A redelivery that
#: differs only in correlation identity therefore still compares equal.
_PROVENANCE_FIELDS = frozenset(
    {
        "activity_id",
        "correlation_id",
        "evidence_digest",
        "evidence_source_revision",
    }
)


def posture_report_state_key(scope: str) -> str:
    """Return the deterministic latest-report key for ``scope``."""

    if not scope.strip():
        raise ValueError("assurance twin posture scope MUST be non-empty")
    return f"{POSTURE_REPORT_STATE_PREFIX}{scope}"


def change_review_state_key(review_key: str) -> str:
    """Return the deterministic per-review key for ``review_key``."""

    if not review_key.strip():
        raise ValueError("assurance twin review key MUST be non-empty")
    return f"{CHANGE_REVIEW_STATE_PREFIX}{review_key}"


def evidence_body_digest(body: Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 digest of one evidence body."""

    material = {key: value for key, value in body.items() if key not in _PROVENANCE_FIELDS}
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True, slots=True)
class AssuranceTwinLedgerWrite:
    """Result of one durable posture/review write."""

    key: str
    created: bool
    """``True`` when this call wrote a new row.

    For a posture report this is always ``True`` (latest-wins overwrite);
    for a change review it is ``False`` on redelivery of an existing
    ``review_key``.
    """

    evidence_digest: str
    """SHA-256 digest of the evidence body this call carried."""

    conflict: bool = False
    """``True`` when an existing row under the same identity holds a
    different evidence body. The durable row is left untouched; the caller
    MUST fail closed rather than announce either version as authoritative.
    """

    stored_evidence_digest: str | None = None
    """Digest of the body that remains durable when it differs from
    ``evidence_digest``."""


class StateStoreAssuranceTwinPostureLedger:
    """Durable posture-report and change-review projection over ``StateStore``."""

    def __init__(self, *, store: StateStore) -> None:
        self._store = store

    async def record_posture_report(
        self,
        report: PostureAssessmentReport,
        *,
        freshness: str,
        reason_codes: tuple[str, ...] = (),
        activity_id: str,
        correlation_id: str,
        evidence_source_revision: str,
    ) -> AssuranceTwinLedgerWrite:
        """Persist ``report`` as the latest snapshot for its scope."""

        key = posture_report_state_key(report.scope)
        body: dict[str, Any] = {
            **report.to_dict(),
            "freshness": freshness,
            "reason_codes": list(reason_codes),
        }
        digest = evidence_body_digest(body)
        await self._store.write_state(
            key,
            _with_provenance(
                body,
                activity_id=activity_id,
                correlation_id=correlation_id,
                digest=digest,
                evidence_source_revision=evidence_source_revision,
            ),
        )
        return AssuranceTwinLedgerWrite(key=key, created=True, evidence_digest=digest)

    async def record_change_review(
        self,
        review: IacReview,
        *,
        freshness: str,
        reason_codes: tuple[str, ...] = (),
        activity_id: str,
        correlation_id: str,
        evidence_source_revision: str,
    ) -> AssuranceTwinLedgerWrite:
        """Persist ``review`` once per ``review_key``.

        Identical redelivery is an idempotent no-op. A different body under
        the same ``review_key`` returns ``conflict=True`` without replacing
        the durable row, so the ledger never holds one truth while the bus
        announces another.
        """

        key = change_review_state_key(review.review_key)
        body = _change_review_body(review, freshness=freshness, reason_codes=reason_codes)
        digest = evidence_body_digest(body)
        created = await self._store.write_state_if_absent(
            key,
            _with_provenance(
                body,
                activity_id=activity_id,
                correlation_id=correlation_id,
                digest=digest,
                evidence_source_revision=evidence_source_revision,
            ),
        )
        if created:
            return AssuranceTwinLedgerWrite(key=key, created=True, evidence_digest=digest)
        stored_digest = _stored_digest(await self._store.read_state(key))
        if stored_digest == digest:
            return AssuranceTwinLedgerWrite(key=key, created=False, evidence_digest=digest)
        return AssuranceTwinLedgerWrite(
            key=key,
            created=False,
            evidence_digest=digest,
            conflict=True,
            stored_evidence_digest=stored_digest,
        )

    async def read_latest_posture_report(self, scope: str) -> Mapping[str, Any] | None:
        """Return the latest durable posture report for ``scope``, if any."""

        return await self._store.read_state(posture_report_state_key(scope))

    async def read_recent_change_reviews(
        self,
        *,
        limit: int = 100,
    ) -> tuple[Mapping[str, Any], ...]:
        """Return up to ``limit`` durable change reviews, newest first."""

        if not 1 <= limit <= 1000:
            raise ValueError("assurance twin review read limit MUST be in [1, 1000]")
        return await self._store.read_states(CHANGE_REVIEW_STATE_PREFIX, limit=limit)


def _with_provenance(
    body: Mapping[str, Any],
    *,
    activity_id: str,
    correlation_id: str,
    digest: str,
    evidence_source_revision: str,
) -> dict[str, Any]:
    if not activity_id.strip() or not correlation_id.strip():
        raise ValueError("assurance twin provenance MUST carry activity and correlation identity")
    if not evidence_source_revision.strip():
        raise ValueError("assurance twin provenance MUST carry an evidence source revision")
    return {
        **body,
        "activity_id": activity_id,
        "correlation_id": correlation_id,
        "evidence_digest": digest,
        "evidence_source_revision": evidence_source_revision,
    }


def _change_review_body(
    review: IacReview,
    *,
    freshness: str,
    reason_codes: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "pr_ref": review.pr_ref,
        "review_key": review.review_key,
        "verdict": review.verdict,
        "mode": review.mode.value,
        "generated_at": review.generated_at,
        "freshness": freshness,
        "reason_codes": list(reason_codes),
        "metadata": dict(review.metadata),
        "findings": [
            {
                "rule_id": finding.rule_id,
                "resource_type": finding.resource.resource_type,
                "resource_ref": finding.resource.ref,
                "severity": finding.severity,
                "reason": finding.reason,
                "evidence_refs": list(finding.evidence_refs),
            }
            for finding in review.findings
        ],
    }


def _stored_digest(existing: Mapping[str, Any] | None) -> str | None:
    """Return the durable row's evidence digest, recomputing it when absent.

    A row written before provenance existed carries no ``evidence_digest``;
    recomputing it from the stored body keeps replay comparison honest
    instead of treating a missing field as a match.
    """

    if existing is None:
        return None
    recorded = existing.get("evidence_digest")
    if isinstance(recorded, str) and recorded:
        return recorded
    return evidence_body_digest(existing)


__all__ = [
    "AssuranceTwinLedgerWrite",
    "CHANGE_REVIEW_STATE_PREFIX",
    "POSTURE_REPORT_STATE_PREFIX",
    "StateStoreAssuranceTwinPostureLedger",
    "change_review_state_key",
    "evidence_body_digest",
    "posture_report_state_key",
]
