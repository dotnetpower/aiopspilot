"""Assurance Twin - compose the durable ledger and, for posture reports only,
the bus activity tip.

The one call site a future trusted producer binding uses to persist a
computed report/review, and - for a posture report - announce it on the
schema-validated event bus. Wires two existing seams:

- ``fdai.delivery.persistence.state_store_assurance_twin_posture`` owns the
  durable read model (authoritative content Operator API reads).
- ``fdai.delivery.operational_activity.EventBusOperationalActivityPublisher``
  owns the bounded, schema-validated bus tip (already used for every other
  observation domain).
- ``fdai.core.assurance_twin.posture_activity`` builds the tip payload from
  the report/review, pure and CSP-neutral.

**Change-review activity publication is disabled.** A same-``review_key``
redelivery's durable outcome (completed vs. conflict-tombstoned) is decided
by the ledger's compare-and-set write, but the bus publish that would
announce that outcome is a *separate*, unordered async call after the fact:
nothing pins the publish to happen before, or atomically with, a concurrent
redelivery's own compare-and-set. A completed tip built from this call's own
result can therefore reach the bus after a concurrent redelivery has already
durably tombstoned the same identity - or a conflict tip can reach the bus
out of order relative to a sibling's completed tip - so either published tip
can misrepresent the row's durable truth by the time a subscriber sees it,
permanently (the tombstone never reverts, and each tip carries its own
``activity_id``/``idempotency_key`` per status, so nothing supersedes an
already-published stale tip). No trusted producer is bound to this recorder
yet, so nothing depends on the change-review tip today; rather than add a
speculative lock or an unshipped transactional outbox to make that ordering
safe, ``record_change_review`` still persists durably (and still returns the
built ``activity`` value, for the caller's own audit/logging use) but never
calls ``publisher.publish`` for it. The durable ledger, the Operator API, and
the Console panel remain the source of truth for change-review state; a
durable conflict stays durably unavailable there regardless. See
[assurance-twin.md](../../../../../docs/roadmap/operations/assurance-twin.md#implementation-status).

**Posture-report publication remains.** A posture report has no conflict
tombstone: each write is a plain latest-wins overwrite for its ``scope``, and
a published completed tip only asserts "this report was recorded," which
stays true even after a later report supersedes it - matching every other
observation domain's activity feed. There is no durable marker a posture
report's publish could contradict after the fact, so the same hazard does
not apply here.

**No shipped call site.** This recorder is deliberately unbound: no trusted
component computes twin findings yet, and an ambient ingress payload is not
trustworthy evidence, so nothing in the runtime invokes it. It stays a
read-only, authority-free surface for a future trusted producer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fdai_service_contracts import AgentOperationalActivity, OperationalFreshness

from fdai.core.assurance_twin.posture_activity import (
    build_change_review_activity,
    build_posture_report_activity,
)
from fdai.core.assurance_twin.report import PostureAssessmentReport
from fdai.delivery.operational_activity import EventBusOperationalActivityPublisher
from fdai.delivery.persistence.state_store_assurance_twin_posture import (
    REVIEW_CONFLICT_REASON_CODE,
    StateStoreAssuranceTwinPostureLedger,
)
from fdai.shared.providers.iac_review import IacReview


@dataclass(frozen=True, slots=True)
class AssuranceTwinPostureRecord:
    """Combined durable-write and live-tip outcome for one record call."""

    activity: AgentOperationalActivity
    durable_write_created: bool
    """Mirrors :class:`AssuranceTwinLedgerWrite.created` for the caller's audit trail."""
    published: bool
    """For a posture report: ``False`` only when the bus publish itself
    failed; the durable write already landed regardless, so a broker outage
    never loses the report. For a change review: always ``False`` - the
    change-review activity tip is never published (see module docstring),
    so this never reflects a publish attempt or its outcome."""
    evidence_digest: str
    """SHA-256 digest of the evidence body this call carried."""
    conflict: bool = False
    """``True`` when an existing row under the same ``review_key`` holds a
    different body. The durable row was left untouched and ``activity``
    describes the unavailable outcome, but it is never published (see
    module docstring)."""
    stored_evidence_digest: str | None = None
    """Digest that remains durable when ``conflict`` is ``True``."""


class AssuranceTwinPostureRecorder:
    """Record a posture report (durably, with a published tip) or a change
    review (durably, with no published tip - see module docstring)."""

    def __init__(
        self,
        *,
        ledger: StateStoreAssuranceTwinPostureLedger,
        publisher: EventBusOperationalActivityPublisher,
    ) -> None:
        self._ledger = ledger
        self._publisher = publisher

    async def record_posture_report(
        self,
        report: PostureAssessmentReport,
        *,
        correlation_id: str,
        freshness: OperationalFreshness,
        reason_codes: tuple[str, ...] = (),
        evidence_source_revision: str,
    ) -> AssuranceTwinPostureRecord:
        """Persist ``report`` and publish its bounded activity tip."""

        activity = build_posture_report_activity(
            report,
            correlation_id=correlation_id,
            freshness=freshness,
            reason_codes=reason_codes,
        )
        write = await self._ledger.record_posture_report(
            report,
            freshness=freshness.value,
            reason_codes=reason_codes,
            activity_id=activity.activity_id,
            correlation_id=correlation_id,
            evidence_source_revision=evidence_source_revision,
        )
        published = await self._publisher.publish(activity)
        return AssuranceTwinPostureRecord(
            activity=activity,
            durable_write_created=write.created,
            published=published,
            evidence_digest=write.evidence_digest,
        )

    async def record_change_review(
        self,
        review: IacReview,
        *,
        correlation_id: str,
        freshness: OperationalFreshness,
        reason_codes: tuple[str, ...] = (),
        evidence_source_revision: str,
    ) -> AssuranceTwinPostureRecord:
        """Persist ``review`` durably (idempotent by ``review_key``).

        A redelivery whose body matches the durable row is an idempotent
        no-op. A redelivery whose body differs is a conflict: the stored
        evidence body is preserved and the row is durably tombstoned, so
        every later read renders it unavailable. Neither outcome is
        published as an activity tip - see the module docstring for why
        change-review publication is disabled entirely.
        """

        activity = build_change_review_activity(
            review,
            correlation_id=correlation_id,
            freshness=freshness,
            reason_codes=reason_codes,
        )
        write = await self._ledger.record_change_review(
            review,
            freshness=freshness.value,
            reason_codes=reason_codes,
            activity_id=activity.activity_id,
            correlation_id=correlation_id,
            evidence_source_revision=evidence_source_revision,
        )
        if write.conflict:
            activity = build_change_review_activity(
                review,
                correlation_id=correlation_id,
                freshness=OperationalFreshness.UNAVAILABLE,
                reason_codes=(REVIEW_CONFLICT_REASON_CODE,),
            )
        return AssuranceTwinPostureRecord(
            activity=activity,
            durable_write_created=write.created,
            published=False,
            evidence_digest=write.evidence_digest,
            conflict=write.conflict,
            stored_evidence_digest=write.stored_evidence_digest,
        )

    async def read_latest_posture_report(self, scope: str) -> Mapping[str, Any] | None:
        """Return the latest durable posture report for ``scope``, if any."""

        return await self._ledger.read_latest_posture_report(scope)

    async def read_recent_change_reviews(
        self,
        *,
        limit: int = 100,
    ) -> tuple[Mapping[str, Any], ...]:
        """Return up to ``limit`` durable change reviews, newest first."""

        return await self._ledger.read_recent_change_reviews(limit=limit)


__all__ = [
    "REVIEW_CONFLICT_REASON_CODE",
    "AssuranceTwinPostureRecord",
    "AssuranceTwinPostureRecorder",
]
