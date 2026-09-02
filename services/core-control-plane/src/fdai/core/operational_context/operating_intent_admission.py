"""Current-admission gate for deployment-owned operating-intent authority.

Admitting the six-type operating-intent source once, at startup, is not enough. A
source that was complete, pinned, and fresh when the process started can later fall
out of its effective interval, exceed its declared freshness, or disappear from the
deployment mount entirely. The projected graph objects survive that transition - they
are evidence and history - so an authority consumer that reads them directly would
keep granting maintenance authority from a source nothing currently vouches for.

This module is the read side of the bounded revalidation contract. The runtime
revalidation worker durably records what it most recently proved about the source;
every authority consumer resolves that record - status, pinned revision and digest,
and the age of the proof - instead of trusting a raw graph object. A quarantined,
unavailable, expired, or malformed record denies. An absent record means no
deployment-owned intent binding governs this graph at all, which is the pre-existing
generic ``FDAI_OPERATING_MODEL_PATH`` behavior and neither grants nor denies here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from fdai.shared.providers.state_store import StateStore

OPERATING_INTENT_SOURCE_ADMISSION_KEY = "operating-intent-source:admission"
"""Durable state key holding the most recent operating-intent source admission."""

MAX_OPERATING_INTENT_ADMISSION_AGE_SECONDS = 86_400
"""Upper bound on any writer-declared admission validity window (one day)."""


class OperatingIntentAdmissionStatus(StrEnum):
    """Resolved authority disposition of the deployment-owned intent source."""

    UNBOUND = "unbound"
    UNCONFIGURED = "unconfigured"
    ADMITTED = "admitted"
    EXPIRED = "expired"
    QUARANTINED = "quarantined"
    UNAVAILABLE = "unavailable"
    MALFORMED = "malformed"


_DENYING_RECORD_STATUSES = frozenset({"quarantined", "unavailable"})


@dataclass(frozen=True, slots=True)
class OperatingIntentAdmission:
    """One resolved judgement about whether intent authority is currently backed.

    ``grants_intent_authority`` is deliberately not the same as "the source is
    healthy": an unbound or unconfigured binding grants nothing of its own and
    simply does not withhold the pre-existing generic operating-model behavior.
    Only ``ADMITTED`` reflects a source that a bounded revalidation recently
    proved complete, pinned, and fresh.
    """

    status: OperatingIntentAdmissionStatus
    grants_intent_authority: bool
    reason: str | None = None
    source_revision: str | None = None
    snapshot_digest: str | None = None
    validated_at: datetime | None = None


def evaluate_operating_intent_admission(
    raw: Mapping[str, object] | None,
    *,
    now: datetime,
) -> OperatingIntentAdmission:
    """Resolve one durable admission record into a current authority judgement.

    ``now`` MUST be supplied by the caller - normally the exact decision instant an
    authority consumer is judging - so the age check stays deterministic and so
    authority is evaluated at the time it is claimed rather than at read time.

    Fails closed on anything it cannot fully verify: a record whose status, pinned
    identity, timestamp, or declared validity window is missing or malformed denies
    rather than being read optimistically. An absent record is the one exception,
    because it is indistinguishable from a deployment that never bound an
    operating-intent source; it withholds nothing and grants nothing.
    """

    if now.tzinfo is None:
        raise ValueError("operating intent admission 'now' MUST be timezone-aware")
    if raw is None:
        return OperatingIntentAdmission(
            status=OperatingIntentAdmissionStatus.UNBOUND,
            grants_intent_authority=True,
            reason="no deployment-owned operating-intent source is bound",
        )
    status = raw.get("status")
    reason = raw.get("reason")
    reason_text = reason if isinstance(reason, str) and reason else None
    if status == "unconfigured":
        return OperatingIntentAdmission(
            status=OperatingIntentAdmissionStatus.UNCONFIGURED,
            grants_intent_authority=True,
            reason="the deployment-owned operating-intent source binding is unconfigured",
        )
    if status in _DENYING_RECORD_STATUSES:
        return OperatingIntentAdmission(
            status=OperatingIntentAdmissionStatus(status),
            grants_intent_authority=False,
            reason=reason_text,
            validated_at=_optional_timestamp(raw.get("validated_at")),
        )
    if status != "admitted":
        return _malformed("operating intent admission status is missing or unrecognized")
    source_revision = raw.get("source_revision")
    snapshot_digest = raw.get("snapshot_digest")
    if not isinstance(source_revision, str) or not source_revision.strip():
        return _malformed("admitted operating intent admission is missing source_revision")
    if (
        not isinstance(snapshot_digest, str)
        or not snapshot_digest.startswith("sha256:")
        or len(snapshot_digest) != 71
    ):
        return _malformed("admitted operating intent admission is missing a SHA-256 digest")
    validated_at = _optional_timestamp(raw.get("validated_at"))
    if validated_at is None:
        return _malformed("admitted operating intent admission is missing validated_at")
    max_age_seconds = raw.get("max_age_seconds")
    if (
        isinstance(max_age_seconds, bool)
        or not isinstance(max_age_seconds, int)
        or max_age_seconds < 1
        or max_age_seconds > MAX_OPERATING_INTENT_ADMISSION_AGE_SECONDS
    ):
        return _malformed("admitted operating intent admission has an unusable max_age_seconds")
    age_seconds = (now - validated_at).total_seconds()
    if age_seconds > max_age_seconds:
        return OperatingIntentAdmission(
            status=OperatingIntentAdmissionStatus.EXPIRED,
            grants_intent_authority=False,
            reason=(
                "the deployment-owned operating-intent source has not been revalidated "
                "within its declared validity window"
            ),
            source_revision=source_revision,
            snapshot_digest=snapshot_digest,
            validated_at=validated_at,
        )
    return OperatingIntentAdmission(
        status=OperatingIntentAdmissionStatus.ADMITTED,
        grants_intent_authority=True,
        source_revision=source_revision,
        snapshot_digest=snapshot_digest,
        validated_at=validated_at,
    )


class StateStoreOperatingIntentAdmissionReader:
    """Read the durable operating-intent admission an authority consumer must gate on.

    Read-only by construction: it never projects, repairs, or re-admits a source. A
    state-store read failure is not swallowed into a permissive answer - it
    propagates to the caller, whose own fail-closed path denies.
    """

    def __init__(self, store: StateStore) -> None:
        self._store = store

    async def resolve(self, *, now: datetime) -> OperatingIntentAdmission:
        raw = await self._store.read_state(OPERATING_INTENT_SOURCE_ADMISSION_KEY)
        return evaluate_operating_intent_admission(raw, now=now)


def _malformed(reason: str) -> OperatingIntentAdmission:
    return OperatingIntentAdmission(
        status=OperatingIntentAdmissionStatus.MALFORMED,
        grants_intent_authority=False,
        reason=reason,
    )


def _optional_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


__all__ = [
    "MAX_OPERATING_INTENT_ADMISSION_AGE_SECONDS",
    "OPERATING_INTENT_SOURCE_ADMISSION_KEY",
    "OperatingIntentAdmission",
    "OperatingIntentAdmissionStatus",
    "StateStoreOperatingIntentAdmissionReader",
    "evaluate_operating_intent_admission",
]
