"""Assurance Twin - compose the durable ledger and the bus activity tip.

The one call site an accountable-agent runtime binding uses to both persist
a computed report/review and announce it on the schema-validated event bus.
Splits cleanly along the two existing seams so each stays single-purpose:

- ``fdai.delivery.persistence.state_store_assurance_twin_posture`` owns the
  durable read model (authoritative content Operator API reads).
- ``fdai.delivery.operational_activity.EventBusOperationalActivityPublisher``
  owns the bounded, schema-validated bus tip (already used for every other
  observation domain).
- ``fdai.core.assurance_twin.posture_activity`` builds the tip payload from
  the report/review, pure and CSP-neutral.

This module only wires the three together; it computes nothing.
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
    ) -> AssuranceTwinPostureRecord:
        """Persist ``report`` and publish its bounded activity tip."""

        write = await self._ledger.record_posture_report(
            report,
            freshness=freshness.value,
            reason_codes=reason_codes,
        )
        activity = build_posture_report_activity(
            report,
            correlation_id=correlation_id,
            freshness=freshness,
            reason_codes=reason_codes,
        )
        published = await self._publisher.publish(activity)
        return AssuranceTwinPostureRecord(
            activity=activity,
            durable_write_created=write.created,
            published=published,
        )

    async def record_change_review(
        self,
        review: IacReview,
        *,
        correlation_id: str,
        freshness: OperationalFreshness,
        reason_codes: tuple[str, ...] = (),
    ) -> AssuranceTwinPostureRecord:
        """Persist ``review`` (idempotent by ``review_key``) and publish its tip."""

        write = await self._ledger.record_change_review(
            review,
            freshness=freshness.value,
            reason_codes=reason_codes,
        )
        activity = build_change_review_activity(
            review,
            correlation_id=correlation_id,
            freshness=freshness,
            reason_codes=reason_codes,
        )
        published = await self._publisher.publish(activity)
        return AssuranceTwinPostureRecord(
            activity=activity,
            durable_write_created=write.created,
            published=published,
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
    "AssuranceTwinPostureRecord",
    "AssuranceTwinPostureRecorder",
]
