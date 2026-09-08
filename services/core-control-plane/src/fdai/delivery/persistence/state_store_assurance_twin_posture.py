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

- **Durable-first**: the report/review body is the authoritative record.
  ``core/assurance_twin/posture_activity.py`` builds a bounded activity value,
  but the recorder publishes neither posture nor review tips until a
  transactional outbox can order them with the exact durable revision (see
  ``fdai.delivery.assurance_twin_posture``).
- **Read-only surface**: this ledger never judges, approves, or executes;
  it stores exactly the report/review the twin already computed.
- **Idempotent by identity, fail-closed on conflict**: a posture report advances
  the prior snapshot for its ``scope`` only when its canonical
  ``generated_at`` is newer. The create-or-advance sequence is linearized
  through ``write_state_if_absent`` and revision-fenced compare-and-set, so a
  delayed older report can never overwrite newer evidence. A change review is written once per
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
  concurrent caller observes the conflict and none reports a
  completed/available result for a row another caller just tombstoned. A
  *matching*-body redelivery uses the same compare-and-set to confirm its
  read before returning non-conflict, rather than trusting the read alone:
  a redelivery that read the row before a concurrent conflicting write
  tombstoned it can therefore never report completed/available for the
  identity its sibling just marked unavailable - the whole persistence
  result is linearized per ``review_key`` through this one compare-and-set
  point. This linearizes the *durable* result only: a caller still cannot
  atomically order an activity-bus publish with this compare-and-set (a
  separate async call after the fact), which is why the recorder publishes
  neither posture nor review tips - see that module's docstring.
- **Bounded by identity and by size**: ``review_key`` is rejected above
  256 characters, provenance identities above 512 characters, ``findings``
  above 200 entries, ``reason_codes`` and any
  finding's ``evidence_refs`` above 200 entries or containing a blank,
  over-512-character, or duplicate entry, and ``evidence_source_revision``
  when blank or over 512 characters - all at write time, before any
  durable write or activity publication - the same bounds the Operator
  API's detail lookup and projection (``_strict_string_list``,
  ``_bounded_identity``) already enforce on read. A write this ledger
  accepts is therefore always reachable and fully renderable through the
  Operator API, never a row nobody can ever read back.
- **Replayable provenance**: every row carries the bounded activity and
  correlation identity of the record call plus the SHA-256 digest of the
  exact evidence body, so a future transactional publisher can bind a tip to
  the same rendered evidence. Digests and identifiers only - no finding text,
  resource value, or customer identifier is added here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fdai.core.assurance_twin.report import PostureAssessmentReport
from fdai.shared.providers.iac_review import IacReview
from fdai.shared.providers.state_store import StateStore

POSTURE_REPORT_STATE_PREFIX = "runtime:assurance-twin-posture:"
CHANGE_REVIEW_STATE_PREFIX = "runtime:assurance-twin-review:"

REVIEW_CONFLICT_REASON_CODE = "assurance_twin_review_key_conflict"
"""Reason code carried by the durable conflict marker and the unavailable tip."""

POSTURE_CONFLICT_REASON_CODE = "assurance_twin_posture_timestamp_conflict"
"""Reason code for different posture evidence generated at the same instant."""

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

_MAX_POSTURE_CAS_ATTEMPTS = 8
"""Bound on retrying a posture advance after a concurrent writer wins."""

_REVIEW_KEY_MAX_CHARS = 256
"""Upper bound on ``review_key`` length, enforced at write time.

Matches ``_ASSURANCE_TWIN_REVIEW_KEY_MAX_CHARS`` in
``fdai_operator_service.runtime_projection_reader`` - the bound the
Operator API's detail lookup already enforces on the same identity. The
two services stay independently packaged (see module docstring), so the
constant is restated here rather than imported across the service
boundary. Rejecting an over-long key at persistence time, instead of only
at read time, guarantees every row this ledger ever writes stays
reachable through the Operator API's list-then-detail round trip.
"""

_MAX_FINDINGS = 200
"""Upper bound on findings per report/review, enforced at write time.

Matches ``_MAX_ITEMS`` in
``fdai_operator_service.assurance_twin_posture_projection`` - the bound
the Operator API's projection already applies when rendering a row's
finding list (an over-long list makes the whole row ``evidence_malformed``
there). Rejecting the write here, rather than letting an unreadable row
land while the bus still announces it ``completed``, keeps every
successful write's evidence actually replayable.
"""

_MAX_LIST_ITEMS = 200
_MAX_TEXT_CHARS = 512
"""Bounds for a single bounded string list (``reason_codes``, one
finding's ``evidence_refs``), enforced at write time.

Matches ``_MAX_ITEMS``/``_MAX_TEXT_LEN`` and ``_strict_string_list`` in
``fdai_operator_service.assurance_twin_posture_projection``: at most
:data:`_MAX_LIST_ITEMS` entries, each a non-blank string of at most
:data:`_MAX_TEXT_CHARS` characters, with no duplicate entries. The
projection renders a list that breaks any of these rules as
``evidence_malformed`` for the whole row rather than a filtered,
truncated, or deduplicated one, so this ledger rejects the write outright
for the same reason :data:`_MAX_FINDINGS` does: a write this ledger
accepts must stay fully renderable, never a row nobody can ever read back.
"""

_MAX_EVIDENCE_SOURCE_REVISION_CHARS = 512
"""Upper bound on ``evidence_source_revision``, enforced at write time.

Matches :data:`_MAX_TEXT_CHARS` - the same bound the Operator API's
projection applies to every provenance identity string via
``_bounded_identity`` - so a revision this ledger accepts is always
rendered as usable provenance there too, never ``evidence_malformed``.
"""

_ALLOWED_FRESHNESS = frozenset({"fresh", "stale", "unavailable", "unknown"})
_ALLOWED_REVIEW_VERDICTS = frozenset({"clear", "needs_review", "blocked"})
_ALLOWED_FINDING_SEVERITIES = frozenset({"low", "medium", "high", "critical"})

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
    """Return the deterministic per-review key for ``review_key``.

    Raises:
        ValueError: when ``review_key`` is blank or exceeds
            :data:`_REVIEW_KEY_MAX_CHARS` - the same bound the Operator
            API's detail lookup enforces, so a key this function accepts
            is always fetchable there too.
    """

    if not review_key.strip():
        raise ValueError("assurance twin review key MUST be non-empty")
    if len(review_key) > _REVIEW_KEY_MAX_CHARS:
        raise ValueError(f"assurance twin review key MUST be <= {_REVIEW_KEY_MAX_CHARS} characters")
    return f"{CHANGE_REVIEW_STATE_PREFIX}{review_key}"


def _check_bounded_findings(findings: Sequence[Any]) -> None:
    """Reject a finding list before it is ever written or announced.

    Also validates each finding's ``evidence_refs`` with
    :func:`_check_bounded_string_list`, so a finding carrying an
    over-long, duplicate, or blank evidence ref is rejected here too,
    rather than landing as a row the Operator API's projection can only
    render ``evidence_malformed``.

    Raises:
        ValueError: when ``findings`` exceeds :data:`_MAX_FINDINGS`, or
            any finding's ``evidence_refs`` fails
            :func:`_check_bounded_string_list` - the same bounds the
            Operator API's projection applies when rendering a row, so a
            write this function accepts is always rendered as usable
            evidence there too.
    """

    if len(findings) > _MAX_FINDINGS:
        raise ValueError(
            f"assurance twin findings MUST number <= {_MAX_FINDINGS}, got {len(findings)}"
        )
    for finding in findings:
        _check_enum("finding severity", finding.severity, _ALLOWED_FINDING_SEVERITIES)
        _check_bounded_string_list(finding.evidence_refs, field="finding evidence_refs")


def _check_enum(name: str, value: str, allowed: frozenset[str]) -> None:
    if value not in allowed:
        raise ValueError(f"assurance twin {name} is not projectable: {value!r}")


def _check_bounded_string_list(items: Sequence[object], *, field: str) -> None:
    """Reject a bounded string list before it is ever written or announced.

    Mirrors ``_strict_string_list`` in
    ``fdai_operator_service.assurance_twin_posture_projection`` exactly:
    at most :data:`_MAX_LIST_ITEMS` entries, each a non-blank string of at
    most :data:`_MAX_TEXT_CHARS` characters, with no duplicate entries.
    Applies to ``reason_codes`` and to one finding's ``evidence_refs`` -
    every list field the projection validates with the same rule.

    Raises:
        ValueError: when ``items`` breaks any of the above rules, naming
            ``field`` so the caller can trace which write-side value
            failed.
    """

    if len(items) > _MAX_LIST_ITEMS:
        raise ValueError(
            f"assurance twin {field} MUST number <= {_MAX_LIST_ITEMS}, got {len(items)}"
        )
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"assurance twin {field} entries MUST be non-blank strings")
        if len(item) > _MAX_TEXT_CHARS:
            raise ValueError(
                f"assurance twin {field} entries MUST be <= {_MAX_TEXT_CHARS} characters"
            )
        if item in seen:
            raise ValueError(
                f"assurance twin {field} entries MUST be unique, got a duplicate {item!r}"
            )
        seen.add(item)


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
    """``True`` when this call created or advanced the durable row.

    For a posture report it is ``False`` when the same or a newer report is
    already durable; for a change review it is ``False`` on redelivery of an
    existing ``review_key``.
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
        """Persist ``report`` as the latest snapshot for its scope.

        Raises:
            ValueError: when ``report.findings`` exceeds
                :data:`_MAX_FINDINGS`, a finding's ``evidence_refs`` fails
                :func:`_check_bounded_string_list`, ``reason_codes`` fails
                :func:`_check_bounded_string_list`, or
                ``evidence_source_revision`` is blank or exceeds
                :data:`_MAX_EVIDENCE_SOURCE_REVISION_CHARS` - all rejected
                before any write so a report this call persists is always
                fully renderable by the Operator API's projection.
        """

        _check_enum("freshness", freshness, _ALLOWED_FRESHNESS)
        _check_bounded_findings(report.findings)
        _check_bounded_string_list(reason_codes, field="reason_codes")
        correlation_identity = _privacy_safe_identity(correlation_id)
        key = posture_report_state_key(report.scope)
        body: dict[str, Any] = {
            **report.to_dict(),
            "generated_at": _canonical_timestamp(report.generated_at),
            "freshness": freshness,
            "reason_codes": list(reason_codes),
        }
        digest = evidence_body_digest(body)
        value = {
            **_with_provenance(
                body,
                activity_id=activity_id,
                correlation_id=correlation_identity,
                digest=digest,
                evidence_source_revision=evidence_source_revision,
            ),
            _REVISION_FIELD: 1,
        }
        if await self._store.write_state_if_absent(key, value):
            return AssuranceTwinLedgerWrite(key=key, created=True, evidence_digest=digest)
        existing = await self._store.read_state(key)
        if existing is None:
            raise RuntimeError(
                "assurance twin posture row disappeared after losing its create race"
            )
        return await self._advance_posture_report(
            key=key,
            value=value,
            digest=digest,
            correlation_id=correlation_identity,
            attempts_remaining=_MAX_POSTURE_CAS_ATTEMPTS,
            existing=existing,
        )

    async def _advance_posture_report(
        self,
        *,
        key: str,
        value: Mapping[str, Any],
        digest: str,
        correlation_id: str,
        attempts_remaining: int,
        existing: Mapping[str, Any],
    ) -> AssuranceTwinLedgerWrite:
        """Atomically advance one scope only to a newer generated timestamp."""

        incoming_generated_at = str(value["generated_at"])
        existing_generated_at = _stored_canonical_timestamp(existing)
        stored_digest = _stored_digest(existing)
        if existing_generated_at is not None and existing_generated_at > incoming_generated_at:
            return AssuranceTwinLedgerWrite(
                key=key,
                created=False,
                evidence_digest=digest,
                conflict=_has_conflict_marker(existing),
                stored_evidence_digest=stored_digest,
            )
        if existing_generated_at == incoming_generated_at:
            if _has_conflict_marker(existing):
                return AssuranceTwinLedgerWrite(
                    key=key,
                    created=False,
                    evidence_digest=digest,
                    conflict=True,
                    stored_evidence_digest=stored_digest,
                )
            if _stored_comparison_digest(existing) == digest:
                return AssuranceTwinLedgerWrite(
                    key=key,
                    created=False,
                    evidence_digest=digest,
                    stored_evidence_digest=stored_digest,
                )
            return await self._mark_posture_conflict(
                key=key,
                value=value,
                digest=digest,
                correlation_id=correlation_id,
                attempts_remaining=attempts_remaining,
                existing=existing,
            )
        if attempts_remaining <= 0:
            raise RuntimeError("assurance twin posture compare-and-set exceeded its retry bound")
        current_revision = _stored_revision(existing)
        advanced = await self._store.compare_and_set_state_with_audit(
            key,
            {**value, _REVISION_FIELD: current_revision + 1},
            expected_revision=current_revision,
            audit_entry={
                "action_kind": "assurance_twin.posture_advanced",
                "actor": "fdai.system",
                "mode": "shadow",
                "correlation_id": correlation_id,
                "idempotency_key": (
                    f"assurance-twin-posture-advance:{_privacy_safe_identity(key)}:{digest}"
                ),
            },
        )
        if advanced:
            return AssuranceTwinLedgerWrite(key=key, created=True, evidence_digest=digest)
        replay = await self._store.read_state(key)
        if replay is None:
            raise RuntimeError(
                "assurance twin posture row disappeared during a compare-and-set race"
            )
        return await self._advance_posture_report(
            key=key,
            value=value,
            digest=digest,
            correlation_id=correlation_id,
            attempts_remaining=attempts_remaining - 1,
            existing=replay,
        )

    async def _mark_posture_conflict(
        self,
        *,
        key: str,
        value: Mapping[str, Any],
        digest: str,
        correlation_id: str,
        attempts_remaining: int,
        existing: Mapping[str, Any],
    ) -> AssuranceTwinLedgerWrite:
        """Tombstone different evidence generated for one scope at one instant."""

        if attempts_remaining <= 0:
            raise RuntimeError(
                "assurance twin posture conflict compare-and-set exceeded its retry bound"
            )
        stored_digest = _stored_digest(existing)
        current_revision = _stored_revision(existing)
        advanced = await self._store.compare_and_set_state_with_audit(
            key,
            {
                **_with_conflict_marker(
                    existing,
                    reason_code=POSTURE_CONFLICT_REASON_CODE,
                    stored_evidence_digest=stored_digest,
                    rejected_evidence_digest=digest,
                ),
                _REVISION_FIELD: current_revision + 1,
            },
            expected_revision=current_revision,
            audit_entry={
                "action_kind": "assurance_twin.posture_conflict_marked",
                "actor": "fdai.system",
                "mode": "shadow",
                "correlation_id": correlation_id,
                "idempotency_key": (
                    f"assurance-twin-posture-conflict:{_privacy_safe_identity(key)}:{digest}"
                ),
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
            raise RuntimeError("assurance twin posture row disappeared during a conflict race")
        return await self._advance_posture_report(
            key=key,
            value=value,
            digest=digest,
            correlation_id=correlation_id,
            attempts_remaining=attempts_remaining - 1,
            existing=replay,
        )

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
        ledger never holds one truth for one reader while serving another to
        a different reader.

        The redeliver-then-tombstone sequence is not one atomic
        ``StateStore`` call, so a same-key redelivery racing a concurrent
        duplicate (or the tombstone write it just triggered) is resolved
        with ``compare_and_set_state_with_audit`` against the row's own
        ``revision`` counter rather than a bare ``write_state``: a losing
        caller re-reads the row a concurrent write just advanced and never
        overwrites it, so a duplicate arriving after a tombstone lands can
        never report that identity as completed/available. This holds for
        a *matching*-body redelivery too: it never returns non-conflict
        from a bare read, only after confirming via the same compare-and-
        set that no concurrent tombstone landed on the row it read (see
        :meth:`_resolve_conflict`).

        Raises:
            ValueError: when ``review.review_key`` exceeds
                :data:`_REVIEW_KEY_MAX_CHARS`, ``review.findings`` exceeds
                :data:`_MAX_FINDINGS`, a finding's ``evidence_refs`` fails
                :func:`_check_bounded_string_list`, ``reason_codes`` fails
                :func:`_check_bounded_string_list`, or
                ``evidence_source_revision`` is blank or exceeds
                :data:`_MAX_EVIDENCE_SOURCE_REVISION_CHARS` - all rejected
                before any write so a review this call persists is always
                reachable and fully renderable by the Operator API.
        """

        _check_enum("freshness", freshness, _ALLOWED_FRESHNESS)
        _check_enum("review verdict", review.verdict, _ALLOWED_REVIEW_VERDICTS)
        _check_bounded_findings(review.findings)
        _check_bounded_string_list(reason_codes, field="reason_codes")
        correlation_identity = _privacy_safe_identity(correlation_id)
        key = change_review_state_key(review.review_key)
        body = _change_review_body(review, freshness=freshness, reason_codes=reason_codes)
        digest = evidence_body_digest(body)
        created = await self._store.write_state_if_absent(
            key,
            {
                **_with_provenance(
                    body,
                    activity_id=activity_id,
                    correlation_id=correlation_identity,
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
            correlation_id=correlation_identity,
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
        stored_comparison_digest = _stored_comparison_digest(existing)
        if _has_conflict_marker(existing):
            return AssuranceTwinLedgerWrite(
                key=key,
                created=False,
                evidence_digest=digest,
                conflict=True,
                stored_evidence_digest=stored_digest,
            )
        if stored_comparison_digest == digest:
            return await self._confirm_matching_replay(
                key=key,
                digest=digest,
                existing=existing,
                correlation_id=correlation_id,
                attempts_remaining=attempts_remaining,
            )
        if attempts_remaining <= 0:
            raise RuntimeError(
                "assurance twin review conflict compare-and-set exceeded its retry bound"
            )
        current_revision = _stored_revision(existing)
        tombstoned = {
            **_with_conflict_marker(
                existing,
                reason_code=REVIEW_CONFLICT_REASON_CODE,
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

    async def _confirm_matching_replay(
        self,
        *,
        key: str,
        digest: str,
        existing: Mapping[str, Any],
        correlation_id: str,
        attempts_remaining: int,
    ) -> AssuranceTwinLedgerWrite:
        """Confirm a matching-body redelivery against the row's live revision.

        ``existing`` is a snapshot from a plain read, not a linearization
        point: a concurrent conflicting redelivery could tombstone this
        exact row between that read and this call returning. Returning
        ``conflict=False`` straight from the stale read would let this
        caller announce a completed/available result for an identity
        another caller just marked unavailable.

        So this never trusts the read alone. It re-asserts the *unchanged*
        row through the same ``compare_and_set_state_with_audit`` primitive
        the tombstone write uses, against the exact revision ``existing``
        carries. Since the tombstone write is the only path that ever
        mutates a row after creation, and it always advances
        ``_REVISION_FIELD``, the two calls are linearized through the same
        expected-revision check:

        - The compare-and-set succeeds only when no tombstone has landed
          since ``existing`` was read, so returning non-conflict here is
          then provably still true at the moment of the durable write, not
          just at the moment of the earlier read.
        - The compare-and-set fails exactly when a concurrent tombstone won
          the race first; this caller re-reads the now-tombstoned row and
          recurses into :meth:`_resolve_conflict`, which reports the
          conflict its sibling just wrote instead of a stale match.
        """

        current_revision = _stored_revision(existing)
        confirmed = await self._store.compare_and_set_state_with_audit(
            key,
            dict(existing),
            expected_revision=current_revision,
            audit_entry={
                "action_kind": "assurance_twin.review_replay_confirmed",
                "actor": "fdai.system",
                "mode": "shadow",
                "correlation_id": correlation_id,
                "idempotency_key": f"assurance-twin-review-replay:{key}:{digest}",
            },
        )
        if confirmed:
            return AssuranceTwinLedgerWrite(key=key, created=False, evidence_digest=digest)
        if attempts_remaining <= 0:
            raise RuntimeError(
                "assurance twin review replay compare-and-set exceeded its retry bound"
            )
        replay = await self._store.read_state(key)
        if replay is None:
            raise RuntimeError(
                "assurance twin review row disappeared during a replay compare-and-set race"
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
    _check_provenance_identity("activity_id", activity_id)
    _check_provenance_identity("correlation_id", correlation_id)
    _check_provenance_identity("evidence_source_revision", evidence_source_revision)
    return {
        **body,
        "activity_id": activity_id,
        "correlation_id": correlation_id,
        "evidence_digest": digest,
        "evidence_source_revision": evidence_source_revision,
    }


def _check_provenance_identity(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"assurance twin {name} MUST be non-blank")
    if len(value) > _MAX_EVIDENCE_SOURCE_REVISION_CHARS:
        raise ValueError(
            f"assurance twin {name} MUST be <= {_MAX_EVIDENCE_SOURCE_REVISION_CHARS} characters"
        )


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
        "generated_at": _canonical_timestamp(review.generated_at),
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


def _canonical_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("assurance twin generated_at MUST be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("assurance twin generated_at MUST include a timezone")
    return parsed.astimezone(UTC).isoformat()


def _privacy_safe_identity(value: str) -> str:
    if not value.strip():
        raise ValueError("assurance twin correlation_id MUST be non-blank")
    if len(value) > _MAX_EVIDENCE_SOURCE_REVISION_CHARS:
        raise ValueError(
            "assurance twin correlation_id MUST be "
            f"<= {_MAX_EVIDENCE_SOURCE_REVISION_CHARS} characters"
        )
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


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


def _stored_comparison_digest(existing: Mapping[str, Any]) -> str:
    body = {key: value for key, value in existing.items() if key not in _PROVENANCE_FIELDS}
    generated_at = body.get("generated_at")
    if isinstance(generated_at, str):
        try:
            body["generated_at"] = _canonical_timestamp(generated_at)
        except ValueError:
            pass
    return evidence_body_digest(body)


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


def _stored_canonical_timestamp(existing: Mapping[str, Any]) -> str | None:
    generated_at = existing.get("generated_at")
    if not isinstance(generated_at, str):
        return None
    try:
        return _canonical_timestamp(generated_at)
    except ValueError:
        return None


def _has_conflict_marker(existing: Mapping[str, Any] | None) -> bool:
    return existing is not None and isinstance(existing.get(CONFLICT_MARKER_FIELD), Mapping)


def _with_conflict_marker(
    existing: Mapping[str, Any],
    *,
    reason_code: str,
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
            "reason_code": reason_code,
            "stored_evidence_digest": stored_evidence_digest,
            "rejected_evidence_digest": rejected_evidence_digest,
        },
    }


__all__ = [
    "CHANGE_REVIEW_STATE_PREFIX",
    "CONFLICT_MARKER_FIELD",
    "POSTURE_CONFLICT_REASON_CODE",
    "POSTURE_REPORT_STATE_PREFIX",
    "REVIEW_CONFLICT_REASON_CODE",
    "AssuranceTwinLedgerWrite",
    "StateStoreAssuranceTwinPostureLedger",
    "change_review_state_key",
    "evidence_body_digest",
    "posture_report_state_key",
]
