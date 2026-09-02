"""Assurance Twin - compose the durable ledger and the bus activity tip.

The one call site a future trusted producer binding uses to both persist a
computed report/review and announce it on the schema-validated event bus.
Splits cleanly along the two existing seams so each stays single-purpose:

- ``fdai.delivery.persistence.state_store_assurance_twin_posture`` owns the
  durable read model (authoritative content Operator API reads).
- ``fdai.delivery.operational_activity.EventBusOperationalActivityPublisher``
  owns the bounded, schema-validated bus tip (already used for every other
  observation domain).
- ``fdai.core.assurance_twin.posture_activity`` builds the tip payload from
  the report/review, pure and CSP-neutral.

This module only wires the three together; it computes nothing. The single
judgement it makes is fail-closed: when the durable ledger reports that the
same ``review_key`` already holds a *different* evidence body, the recorder
refuses to announce the incoming version and publishes an explicit
unavailable tip instead, so the bus and the ledger can never carry two
contradictory truths for one identity.

**No shipped call site.** This recorder is deliberately unbound: no trusted
component computes twin findings yet, and an ambient ingress payload is not
trustworthy evidence, so nothing in the runtime invokes it. It stays a
read-only, authority-free surface for a future trusted producer. See
[assurance-twin.md](../../../../../docs/roadmap/operations/assurance-twin.md#implementation-status).
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
    """``False`` only when the bus publish itself failed; the durable write
    already landed regardless, so a broker outage never loses the report."""
    evidence_digest: str
    """SHA-256 digest of the evidence body this call carried."""
    conflict: bool = False
    """``True`` when an existing row under the same ``review_key`` holds a
    different body. The durable row was left untouched and ``activity``
    carries the explicit unavailable tip."""
    stored_evidence_digest: str | None = None
    """Digest that remains durable when ``conflict`` is ``True``."""


class AssuranceTwinPostureRecorder:
    """Record a posture report or change review durably and announce it."""

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
        """Persist ``review`` (idempotent by ``review_key``) and publish its tip.

        A redelivery whose body matches the durable row republishes the same
        tip. A redelivery whose body differs is a conflict: the stored
        evidence body is preserved, the row is durably tombstoned, and the
        published tip is explicitly unavailable.
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
        published = await self._publisher.publish(activity)
        return AssuranceTwinPostureRecord(
            activity=activity,
            durable_write_created=write.created,
            published=published,
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
