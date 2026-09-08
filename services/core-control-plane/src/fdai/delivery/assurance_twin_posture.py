"""Assurance Twin - compose the durable ledger and bounded activity values.

The one call site a future trusted producer binding uses to persist a
computed report/review, and - for a posture report - announce it on the
schema-validated event bus. Wires two existing seams:

- ``fdai.delivery.persistence.state_store_assurance_twin_posture`` owns the
  durable read model (authoritative content Operator API reads).
- ``fdai.core.assurance_twin.posture_activity`` builds the tip payload from
  the report/review, pure and CSP-neutral.

**Activity publication is disabled.** A durable compare-and-set and an event
bus publish are separate async effects. A posture report can win its durable
advance, pause, and publish after a newer report has advanced the same scope;
a change review has the same ordering hazard against a conflict tombstone.
Re-reading before publish only moves the race window. Until a transactional
outbox can bind publication to the exact durable revision, both record methods
return the schema-valid activity for local audit use but never publish it. The
durable ledger, Operator API, and Console remain the source of truth. See
[assurance-twin.md](../../../../../docs/roadmap/operations/assurance-twin.md#implementation-status).

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
from fdai.delivery.persistence.state_store_assurance_twin_posture import (
    POSTURE_CONFLICT_REASON_CODE,
    REVIEW_CONFLICT_REASON_CODE,
    StateStoreAssuranceTwinPostureLedger,
)
from fdai.shared.providers.iac_review import IacReview


@dataclass(frozen=True, slots=True)
class AssuranceTwinPostureRecord:
    """Combined durable-write and unpublished activity outcome for one call."""

    activity: AgentOperationalActivity
    durable_write_created: bool
    """Mirrors :class:`AssuranceTwinLedgerWrite.created` for the caller's audit trail."""
    published: bool
    """Always ``False`` until a transactional outbox orders tips with the ledger."""
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
    """Record a posture report or change review without publishing a tip."""

    def __init__(
        self,
        *,
        ledger: StateStoreAssuranceTwinPostureLedger,
    ) -> None:
        self._ledger = ledger

    async def record_posture_report(
        self,
        report: PostureAssessmentReport,
        *,
        correlation_id: str,
        freshness: OperationalFreshness,
        reason_codes: tuple[str, ...] = (),
        evidence_source_revision: str,
    ) -> AssuranceTwinPostureRecord:
        """Persist ``report`` and return its bounded unpublished activity."""

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
        if write.conflict:
            conflicted = build_posture_report_activity(
                report,
                correlation_id=correlation_id,
                freshness=OperationalFreshness.UNAVAILABLE,
                reason_codes=(POSTURE_CONFLICT_REASON_CODE,),
            )
            return AssuranceTwinPostureRecord(
                activity=conflicted,
                durable_write_created=False,
                published=False,
                evidence_digest=write.evidence_digest,
                conflict=True,
                stored_evidence_digest=write.stored_evidence_digest,
            )
        if not write.created:
            superseded = build_posture_report_activity(
                report,
                correlation_id=correlation_id,
                freshness=freshness,
                reason_codes=reason_codes,
                superseded=True,
            )
            return AssuranceTwinPostureRecord(
                activity=superseded,
                durable_write_created=False,
                published=False,
                evidence_digest=write.evidence_digest,
                stored_evidence_digest=write.stored_evidence_digest,
            )
        return AssuranceTwinPostureRecord(
            activity=activity,
            durable_write_created=write.created,
            published=False,
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
