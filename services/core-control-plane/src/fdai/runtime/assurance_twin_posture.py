"""Runtime composition for the accountable Assurance Twin posture trigger.

Binds :class:`~fdai.delivery.assurance_twin_posture.AssuranceTwinPostureRecorder`
to Heimdall's **already declared** ``object.event`` subscription, so an
ambient change-review or posture candidate produced by the change ingress is
recorded and announced by an accountable agent rather than by an unbound
helper.

Why this shape
--------------

- **No new authority.** Heimdall owns observation. It publishes the bounded
  ``agent.operational-activity`` tip onto the shared activity stage topic
  (``execution_authority`` is the schema ``const`` ``False``) and never
  publishes onto another agent's owned topic. This mirrors the existing
  ``current-state.read`` tip that ``compose_resource_state_shadow_hook``
  publishes from Heimdall's read-investigation hook.
- **No new subscription.** The candidate arrives on ``object.event``, which
  Heimdall already subscribes to, using the same validate-a-candidate shape
  as the existing ``evidence.conflict.candidate.v1`` path: Huginn remains
  the sole ``Event`` writer, Heimdall validates and records.
- **Fail closed.** Every malformed, unbounded, or wrongly attributed payload
  is rejected without a durable write and without a bus tip. The twin never
  invents a verdict here: a posture verdict is derived deterministically by
  :func:`~fdai.core.assurance_twin.report.build_posture_assessment_report`.

Known gap (deliberately not papered over): upstream of this hook no
production ``Inventory``/``ScratchProjection`` binding computes twin
findings yet, so no shipped component publishes these candidate events. The
trigger, the durable ledger, and the tip are implemented and tested; the
production evidence source remains open work tracked in
[assurance-twin.md](../../../../docs/roadmap/operations/assurance-twin.md).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from fdai_service_contracts import OperationalFreshness

from fdai.core.assurance_twin.report import build_posture_assessment_report
from fdai.delivery.assurance_twin_posture import AssuranceTwinPostureRecorder
from fdai.delivery.operational_activity import EventBusOperationalActivityPublisher
from fdai.delivery.persistence.state_store_assurance_twin_posture import (
    StateStoreAssuranceTwinPostureLedger,
)
from fdai.shared.contracts.models import Mode
from fdai.shared.providers.event_bus import EventBus
from fdai.shared.providers.iac_review import IacReview
from fdai.shared.providers.projection import Finding, ResourceRef, Severity
from fdai.shared.providers.state_store import StateStore

POSTURE_CANDIDATE_EVENT_TYPE = "assurance.twin.posture.candidate.v1"
CHANGE_REVIEW_CANDIDATE_EVENT_TYPE = "assurance.twin.review.candidate.v1"
ASSURANCE_TWIN_CANDIDATE_EVENT_TYPES = frozenset(
    {POSTURE_CANDIDATE_EVENT_TYPE, CHANGE_REVIEW_CANDIDATE_EVENT_TYPE}
)

_EVENT_PRODUCER_PRINCIPAL = "Huginn"
_MAX_FINDINGS = 200
_MAX_REASON_CODES = 16
_MAX_TEXT_CHARS = 512
#: Identity fields become part of a derived ``activity_id``/``idempotency_key``
#: that the shared contract bounds at 512 characters, so they stay well inside
#: that budget instead of failing schema validation after the durable write.
_MAX_IDENTITY_CHARS = 256
_SEVERITIES: frozenset[str] = frozenset({"low", "medium", "high", "critical"})
_VERDICTS: frozenset[str] = frozenset({"clear", "needs_review", "blocked"})
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")

_LOGGER = logging.getLogger(__name__)


class AssuranceTwinPostureObserver:
    """Validate one ambient twin candidate and record it as Heimdall evidence."""

    def __init__(self, *, recorder: AssuranceTwinPostureRecorder) -> None:
        self._recorder = recorder

    async def observe(self, payload: Mapping[str, Any]) -> bool:
        """Return whether the candidate produced a durable, announced record.

        Never raises: an invalid candidate is dropped with a bounded log so
        one malformed ingress payload cannot stall Heimdall's event loop.
        """

        try:
            return await self._observe(payload)
        except ValueError as exc:
            _LOGGER.warning(
                "assurance_twin_candidate_rejected",
                extra={
                    "event_type": str(payload.get("event_type") or ""),
                    "reason": str(exc),
                },
            )
            return False

    async def _observe(self, payload: Mapping[str, Any]) -> bool:
        event_type = str(payload.get("event_type") or "")
        if event_type not in ASSURANCE_TWIN_CANDIDATE_EVENT_TYPES:
            raise ValueError("unknown assurance twin candidate event type")
        if payload.get("producer_principal") != _EVENT_PRODUCER_PRINCIPAL:
            raise ValueError("assurance twin candidate MUST be Huginn-produced Event evidence")
        attributes = payload.get("attributes")
        if not isinstance(attributes, Mapping):
            raise ValueError("assurance twin candidate attributes MUST be an object")
        correlation_id = _identity(payload.get("correlation_id"), "correlation_id")
        source_revision = _text(attributes.get("source_revision"), "source_revision")
        freshness = _freshness(attributes.get("freshness"))
        reason_codes = _reason_codes(attributes.get("reason_codes"))
        findings = _findings(attributes.get("findings"))
        generated_at = _timestamp(attributes.get("generated_at"))
        mode = _mode(attributes.get("mode"))

        if event_type == POSTURE_CANDIDATE_EVENT_TYPE:
            report = build_posture_assessment_report(
                scope=_identity(attributes.get("scope"), "scope"),
                generated_at=generated_at,
                mode=mode,
                findings=findings,
            )
            record = await self._recorder.record_posture_report(
                report,
                correlation_id=correlation_id,
                freshness=freshness,
                reason_codes=reason_codes,
                evidence_source_revision=source_revision,
            )
            return record.published

        verdict = _verdict(attributes.get("verdict"))
        review = IacReview(
            pr_ref=_text(attributes.get("pr_ref"), "pr_ref"),
            review_key=_identity(attributes.get("review_key"), "review_key"),
            findings=tuple(findings),
            verdict=verdict,
            mode=mode,
            generated_at=generated_at,
        )
        record = await self._recorder.record_change_review(
            review,
            correlation_id=correlation_id,
            freshness=freshness,
            reason_codes=reason_codes,
            evidence_source_revision=source_revision,
        )
        return record.published and not record.conflict


def build_assurance_twin_posture_observer(
    *,
    state_store: StateStore,
    event_bus: EventBus,
    topic: str,
) -> AssuranceTwinPostureObserver:
    """Bind the durable ledger and the schema-validated activity publisher."""

    return AssuranceTwinPostureObserver(
        recorder=AssuranceTwinPostureRecorder(
            ledger=StateStoreAssuranceTwinPostureLedger(store=state_store),
            publisher=EventBusOperationalActivityPublisher(event_bus=event_bus, topic=topic),
        )
    )


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > _MAX_TEXT_CHARS:
        raise ValueError(f"{field_name} MUST be a bounded non-empty string")
    return value


def _identity(value: object, field_name: str) -> str:
    text = _text(value, field_name)
    if len(text) > _MAX_IDENTITY_CHARS:
        raise ValueError(f"{field_name} MUST fit the derived activity identity bound")
    return text


def _mode(value: object) -> Mode:
    if value == Mode.SHADOW.value:
        return Mode.SHADOW
    if value == Mode.ENFORCE.value:
        return Mode.ENFORCE
    raise ValueError("mode MUST be shadow or enforce")


def _verdict(value: object) -> str:
    if not isinstance(value, str) or value not in _VERDICTS:
        raise ValueError("verdict MUST be clear, needs_review, or blocked")
    return value


def _freshness(value: object) -> OperationalFreshness:
    try:
        return OperationalFreshness(str(value))
    except ValueError as exc:
        raise ValueError("freshness MUST be a declared operational freshness") from exc


def _timestamp(value: object) -> str:
    text = _text(value, "generated_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("generated_at MUST be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("generated_at MUST include a timezone")
    return text


def _reason_codes(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError("reason_codes MUST be an array")
    codes = tuple(str(item) for item in value)
    if len(codes) > _MAX_REASON_CODES or len(set(codes)) != len(codes):
        raise ValueError("reason_codes MUST be bounded and unique")
    if any(_REASON_CODE.fullmatch(code) is None for code in codes):
        raise ValueError("reason_codes MUST match the shared reason-code pattern")
    return codes


def _findings(value: object) -> tuple[Finding, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError("findings MUST be an array")
    if len(value) > _MAX_FINDINGS:
        raise ValueError("findings MUST be bounded")
    findings: list[Finding] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("finding MUST be an object")
        severity = item.get("severity")
        if not isinstance(severity, str) or severity not in _SEVERITIES:
            raise ValueError("finding severity MUST be a declared severity")
        findings.append(
            Finding(
                rule_id=_text(item.get("rule_id"), "finding.rule_id"),
                resource=ResourceRef(
                    resource_type=_text(item.get("resource_type"), "finding.resource_type"),
                    ref=_text(item.get("resource_ref"), "finding.resource_ref"),
                ),
                severity=_severity(severity),
                reason=_text(item.get("reason"), "finding.reason"),
                evidence_refs=_evidence_refs(item.get("evidence_refs")),
            )
        )
    return tuple(findings)


def _severity(value: str) -> Severity:
    if value == "low":
        return "low"
    if value == "medium":
        return "medium"
    if value == "high":
        return "high"
    return "critical"


def _evidence_refs(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError("evidence_refs MUST be an array")
    if len(value) > _MAX_FINDINGS:
        raise ValueError("evidence_refs MUST be bounded")
    return tuple(_text(item, "evidence_ref") for item in value)


__all__ = [
    "ASSURANCE_TWIN_CANDIDATE_EVENT_TYPES",
    "CHANGE_REVIEW_CANDIDATE_EVENT_TYPE",
    "POSTURE_CANDIDATE_EVENT_TYPE",
    "AssuranceTwinPostureObserver",
    "build_assurance_twin_posture_observer",
]
