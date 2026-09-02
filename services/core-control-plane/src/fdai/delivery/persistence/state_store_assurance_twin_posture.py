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
  the stored evidence body is never replaced, and a durable conflict marker
  is written onto the row so every later read renders it unavailable rather
  than serving one of two contradictory truths. The marker is durable: once
  a ``review_key`` has conflicted, it stays conflicted until an operator
  removes the row, and a subsequent redelivery of either body cannot clear
  it.
- **Atomic tombstoning**: the read-compare-tombstone sequence a same-key
  redelivery runs is not a single ``StateStore`` call, so it uses the row's
  own ``revision`` counter with ``compare_and_set_state_with_audit`` (the
  same optimistic-concurrency primitive
  ``fdai/delivery/evidence_conflict.py`` and
  ``fdai/delivery/persistence/state_store_case_history.py`` already use)
  rather than a bare ``write_state``. A concurrent duplicate racing the
  tombstone write either loses the compare-and-set and re-reads the now-
  tombstoned row, or wins it and tombstones the row itself; either way every
  concurrent caller observes the conflict and none can publish a
  completed/available result for a row another caller just tombstoned.
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

REVIEW_CONFLICT_REASON_CODE = "assurance_twin_review_key_conflict"
"""Reason code carried by the durable conflict marker and the unavailable tip."""

CONFLICT_MARKER_FIELD = "conflict"
"""Row field that makes a same-key different-digest conflict durable."""

_REVISION_FIELD = "revision"
"""Optimistic-concurrency counter for ``compare_and_set_state_with_audit``.

Write history, like the conflict marker: excluded from the evidence digest
so it never changes evidence identity, and bumped only by the atomic
tombstone write so a racing duplicate's compare-and-set is checked against
the exact row it read.
"""

_MAX_CONFLICT_CAS_ATTEMPTS = 8
"""Bound on retrying a lost compare-and-set before failing loudly.

Each retry only happens when a concurrent writer just advanced the row
(either tombstoning it, or - impossible once created - replacing its
body), so the loop terminates within one extra attempt per concurrent
racer; the cap exists purely so a StateStore bug cannot spin forever.
"""

#: Provenance fields describe *this* write, not the twin's evidence body, so
#: they are excluded before the body digest is computed. A redelivery that
#: differs only in correlation identity therefore still compares equal. The
#: conflict marker and revision counter are write history too: excluding
#: them keeps the preserved evidence body's digest verifiable after the row
#: is tombstoned or its revision is bumped.
_PROVENANCE_FIELDS = frozenset(
    {
        "activity_id",
        "correlation_id",
        "evidence_digest",
        "evidence_source_revision",
        CONFLICT_MARKER_FIELD,
        _REVISION_FIELD,
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
    different evidence body, or already carries a durable conflict marker.
    The stored evidence body is preserved and the row is tombstoned; the
    caller MUST fail closed rather than announce either version as
    authoritative.
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
        the same ``review_key`` returns ``conflict=True``: the stored
        evidence body is preserved, a durable conflict marker is written
        onto the row, and every later read renders it unavailable, so the
        ledger never holds one truth while the bus announces another.

        The redeliver-then-tombstone sequence is not one atomic
        ``StateStore`` call, so a same-key redelivery racing a concurrent
        duplicate (or the tombstone write it just triggered) is resolved
        with ``compare_and_set_state_with_audit`` against the row's own
        ``revision`` counter rather than a bare ``write_state``: a losing
        caller re-reads the row a concurrent write just advanced and never
        overwrites it, so a duplicate arriving after a tombstone lands can
        never publish that identity as completed/available.
        """

        key = change_review_state_key(review.review_key)
        body = _change_review_body(review, freshness=freshness, reason_codes=reason_codes)
        digest = evidence_body_digest(body)
        created = await self._store.write_state_if_absent(
            key,
            {
                **_with_provenance(
                    body,
                    activity_id=activity_id,
                    correlation_id=correlation_id,
                    digest=digest,
                    evidence_source_revision=evidence_source_revision,
                ),
                _REVISION_FIELD: 1,
            },
        )
        if created:
            return AssuranceTwinLedgerWrite(key=key, created=True, evidence_digest=digest)
        existing = await self._store.read_state(key)
        if existing is None:
            raise RuntimeError("assurance twin review row disappeared after losing its create race")
        return await self._resolve_conflict(
            key=key,
            digest=digest,
            existing=existing,
            correlation_id=correlation_id,
            attempts_remaining=_MAX_CONFLICT_CAS_ATTEMPTS,
        )

    async def _resolve_conflict(
        self,
        *,
        key: str,
        digest: str,
        existing: Mapping[str, Any],
        correlation_id: str,
        attempts_remaining: int,
    ) -> AssuranceTwinLedgerWrite:
        """Reconcile a same-key redelivery against ``existing`` atomically.

        Only one path ever mutates a row after creation: the atomic
        tombstone write below. So a lost compare-and-set means a concurrent
        caller just tombstoned the row (or is about to be observed as
        having done so); re-reading and recursing here always terminates in
        the branch that returns ``conflict=True`` without writing again.
        """

        stored_digest = _stored_digest(existing)
        if _has_conflict_marker(existing):
            return AssuranceTwinLedgerWrite(
                key=key,
                created=False,
                evidence_digest=digest,
                conflict=True,
                stored_evidence_digest=stored_digest,
            )
        if stored_digest == digest:
            return AssuranceTwinLedgerWrite(key=key, created=False, evidence_digest=digest)
        if attempts_remaining <= 0:
            raise RuntimeError(
                "assurance twin review conflict compare-and-set exceeded its retry bound"
            )
        current_revision = _stored_revision(existing)
        tombstoned = {
            **_with_conflict_marker(
                existing,
                stored_evidence_digest=stored_digest,
                rejected_evidence_digest=digest,
            ),
            _REVISION_FIELD: current_revision + 1,
        }
        advanced = await self._store.compare_and_set_state_with_audit(
            key,
            tombstoned,
            expected_revision=current_revision,
            audit_entry={
                "action_kind": "assurance_twin.review_conflict_marked",
                "actor": "fdai.system",
                "mode": "shadow",
                "correlation_id": correlation_id,
                "idempotency_key": f"assurance-twin-review-conflict:{key}:{digest}",
            },
        )
        if advanced:
            return AssuranceTwinLedgerWrite(
                key=key,
                created=False,
                evidence_digest=digest,
                conflict=True,
                stored_evidence_digest=stored_digest,
            )
        replay = await self._store.read_state(key)
        if replay is None:
            raise RuntimeError(
                "assurance twin review row disappeared during a conflict compare-and-set race"
            )
        return await self._resolve_conflict(
            key=key,
            digest=digest,
            existing=replay,
            correlation_id=correlation_id,
            attempts_remaining=attempts_remaining - 1,
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


def _stored_revision(existing: Mapping[str, Any]) -> int:
    """Return the durable row's CAS revision, defaulting a legacy row to ``0``.

    Mirrors the Postgres adapter's own
    ``COALESCE(value ->> 'revision', '0')`` fallback, so a row written
    before this counter existed compares equal against the same expected
    revision the real backend would accept.
    """

    revision = existing.get(_REVISION_FIELD)
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        return 0
    return revision


def _has_conflict_marker(existing: Mapping[str, Any] | None) -> bool:
    return existing is not None and isinstance(existing.get(CONFLICT_MARKER_FIELD), Mapping)


def _with_conflict_marker(
    existing: Mapping[str, Any],
    *,
    stored_evidence_digest: str | None,
    rejected_evidence_digest: str,
) -> dict[str, Any]:
    """Return the stored row tombstoned with a content-free conflict marker.

    The preserved evidence body and its provenance are untouched; only the
    excluded-from-digest marker is added, so a reader can still verify the
    stored body while being forced to render the row unavailable.
    """

    return {
        **existing,
        CONFLICT_MARKER_FIELD: {
            "reason_code": REVIEW_CONFLICT_REASON_CODE,
            "stored_evidence_digest": stored_evidence_digest,
            "rejected_evidence_digest": rejected_evidence_digest,
        },
    }


__all__ = [
    "CHANGE_REVIEW_STATE_PREFIX",
    "CONFLICT_MARKER_FIELD",
    "POSTURE_REPORT_STATE_PREFIX",
    "REVIEW_CONFLICT_REASON_CODE",
    "AssuranceTwinLedgerWrite",
    "StateStoreAssuranceTwinPostureLedger",
    "change_review_state_key",
    "evidence_body_digest",
    "posture_report_state_key",
]
