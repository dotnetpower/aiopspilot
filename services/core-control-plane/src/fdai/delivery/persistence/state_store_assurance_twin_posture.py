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
- **Idempotent by identity**: a posture report overwrites the prior
  snapshot for its ``scope`` (latest-wins, matching ``StateStore.write_state``
  semantics); a change review is written once per ``review_key``
  (``write_state_if_absent``), so redelivery of the same review is a no-op.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fdai.core.assurance_twin.report import PostureAssessmentReport
from fdai.shared.providers.iac_review import IacReview
from fdai.shared.providers.state_store import StateStore

POSTURE_REPORT_STATE_PREFIX = "runtime:assurance-twin-posture:"
CHANGE_REVIEW_STATE_PREFIX = "runtime:assurance-twin-review:"


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
    ) -> AssuranceTwinLedgerWrite:
        """Persist ``report`` as the latest snapshot for its scope."""

        key = posture_report_state_key(report.scope)
        value: dict[str, Any] = {
            **report.to_dict(),
            "freshness": freshness,
            "reason_codes": list(reason_codes),
        }
        await self._store.write_state(key, value)
        return AssuranceTwinLedgerWrite(key=key, created=True)

    async def record_change_review(
        self,
        review: IacReview,
        *,
        freshness: str,
        reason_codes: tuple[str, ...] = (),
    ) -> AssuranceTwinLedgerWrite:
        """Persist ``review`` once per ``review_key`` (idempotent redelivery)."""

        key = change_review_state_key(review.review_key)
        value: dict[str, Any] = {
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
        created = await self._store.write_state_if_absent(key, value)
        return AssuranceTwinLedgerWrite(key=key, created=created)

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


__all__ = [
    "AssuranceTwinLedgerWrite",
    "CHANGE_REVIEW_STATE_PREFIX",
    "POSTURE_REPORT_STATE_PREFIX",
    "StateStoreAssuranceTwinPostureLedger",
    "change_review_state_key",
    "posture_report_state_key",
]
