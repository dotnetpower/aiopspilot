"""Assurance Twin durable ledger + live activity-tip orchestration tests."""

from __future__ import annotations

from fdai.core.assurance_twin import build_posture_assessment_report
from fdai.delivery.assurance_twin_posture import (
    REVIEW_CONFLICT_REASON_CODE,
    AssuranceTwinPostureRecorder,
)
from fdai.delivery.operational_activity import EventBusOperationalActivityPublisher
from fdai.delivery.persistence.state_store_assurance_twin_posture import (
    StateStoreAssuranceTwinPostureLedger,
)
from fdai.shared.contracts.models import Mode
from fdai.shared.providers.iac_review import IacReview
from fdai.shared.providers.projection import Finding, ResourceRef
from fdai.shared.providers.testing.event_bus import InMemoryEventBus
from fdai.shared.providers.testing.state_store import InMemoryStateStore
from fdai_service_contracts import OperationalFreshness

_SCOPE = "sub/00000000-0000-0000-0000-000000000001"
_TOPIC = "fdai.pipeline.stages"
_REVISION = "sha256:0000000000000000000000000000000000000000000000000000000000000001"


def _finding(rule: str = "r-1", ref: str = "vm-a", severity: str = "high") -> Finding:
    return Finding(
        rule_id=rule,
        resource=ResourceRef(resource_type="compute.vm", ref=ref),
        severity=severity,  # type: ignore[arg-type]
        reason="reason",
    )


def _report(*findings: Finding) -> object:
    return build_posture_assessment_report(
        scope=_SCOPE,
        generated_at="2026-07-07T00:00:00Z",
        mode=Mode.SHADOW,
        findings=findings,
    )


def _review(key: str = "k-1", *findings: Finding, verdict: str = "needs_review") -> IacReview:
    return IacReview(
        pr_ref="owner/repo#1",
        review_key=key,
        findings=findings,
        verdict=verdict,
        mode=Mode.SHADOW,
        generated_at="2026-07-07T00:00:00Z",
    )


def _recorder(bus: InMemoryEventBus, store: InMemoryStateStore) -> AssuranceTwinPostureRecorder:
    return AssuranceTwinPostureRecorder(
        ledger=StateStoreAssuranceTwinPostureLedger(store=store),
        publisher=EventBusOperationalActivityPublisher(event_bus=bus, topic=_TOPIC),
    )


async def test_posture_report_is_durably_recorded_and_replayable_from_the_bus() -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    recorder = _recorder(bus, store)

    result = await recorder.record_posture_report(
        _report(_finding()),
        correlation_id="posture-1",
        freshness=OperationalFreshness.FRESH,
        evidence_source_revision=_REVISION,
    )

    assert result.published is True
    assert result.durable_write_created is True
    assert result.activity.owner_agent == "Heimdall"
    assert result.activity.execution_authority is False

    # Governed-runtime replay: an independent consumer subscribing to the
    # same topic sees the exact tip that was published, and the durable
    # projection is readable without recomputing anything.
    envelopes = [event async for event in bus.subscribe(_TOPIC, "replay-consumer")]
    assert len(envelopes) == 1
    assert envelopes[0].payload["activity_id"] == result.activity.activity_id
    assert envelopes[0].payload["kind"] == "assurance-twin.posture"

    durable = await recorder.read_latest_posture_report(_SCOPE)
    assert durable is not None
    assert durable["verdict"] == "blocked"
    # Event-to-report replay: the durable row names the tip that announced it.
    assert durable["activity_id"] == envelopes[0].payload["activity_id"]
    assert durable["correlation_id"] == envelopes[0].payload["correlation_id"]
    assert durable["evidence_digest"] == result.evidence_digest
    assert durable["evidence_source_revision"] == _REVISION


async def test_change_review_redelivery_is_idempotent_but_still_publishes_a_tip() -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    recorder = _recorder(bus, store)

    first = await recorder.record_change_review(
        _review("k-1", _finding()),
        correlation_id="review-1",
        freshness=OperationalFreshness.FRESH,
        evidence_source_revision=_REVISION,
    )
    second = await recorder.record_change_review(
        _review("k-1", _finding()),
        correlation_id="review-1",
        freshness=OperationalFreshness.FRESH,
        evidence_source_revision=_REVISION,
    )

    assert first.durable_write_created is True
    assert second.durable_write_created is False
    assert second.conflict is False
    assert second.activity.activity_id == first.activity.activity_id
    reviews = await recorder.read_recent_change_reviews(limit=10)
    assert len(reviews) == 1

    envelopes = [event async for event in bus.subscribe(_TOPIC, "replay-consumer")]
    assert len(envelopes) == 2, "each attempt still announces its live tip"


async def test_conflicting_review_key_publishes_unavailable_and_keeps_one_truth() -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    recorder = _recorder(bus, store)

    await recorder.record_change_review(
        _review("k-1", _finding()),
        correlation_id="review-1",
        freshness=OperationalFreshness.FRESH,
        evidence_source_revision=_REVISION,
    )
    conflicting = await recorder.record_change_review(
        _review("k-1", _finding(rule="r-2"), verdict="blocked"),
        correlation_id="review-2",
        freshness=OperationalFreshness.FRESH,
        evidence_source_revision=_REVISION,
    )

    assert conflicting.conflict is True
    assert conflicting.durable_write_created is False
    assert conflicting.activity.freshness is OperationalFreshness.UNAVAILABLE
    assert conflicting.activity.status.value == "failed"
    assert conflicting.activity.reason_codes == (REVIEW_CONFLICT_REASON_CODE,)
    assert conflicting.activity.execution_authority is False

    reviews = await recorder.read_recent_change_reviews(limit=10)
    assert len(reviews) == 1
    assert reviews[0]["verdict"] == "needs_review", "the durable body is never replaced"

    envelopes = [event async for event in bus.subscribe(_TOPIC, "replay-consumer")]
    assert [envelope.payload["freshness"] for envelope in envelopes] == ["fresh", "unavailable"]


async def test_unavailable_source_never_grants_authority() -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    recorder = _recorder(bus, store)

    result = await recorder.record_posture_report(
        _report(),
        correlation_id="posture-2",
        freshness=OperationalFreshness.UNAVAILABLE,
        reason_codes=("inventory_freshness_ttl_exceeded",),
        evidence_source_revision=_REVISION,
    )

    assert result.activity.freshness is OperationalFreshness.UNAVAILABLE
    assert result.activity.execution_authority is False
    assert result.activity.status.value == "failed"
