"""Accountable Assurance Twin posture trigger tests.

The recorder is only useful if a real, accountable runtime path reaches it.
These cases drive the trigger through Heimdall's declared ``object.event``
subscription and assert that the durable ledger, the schema-validated bus
tip, and the fail-closed rejections all behave as the design requires.
"""

from __future__ import annotations

import pytest
from fdai.agents.heimdall import Heimdall
from fdai.delivery.persistence.state_store_assurance_twin_posture import (
    CHANGE_REVIEW_STATE_PREFIX,
    POSTURE_REPORT_STATE_PREFIX,
)
from fdai.runtime.assurance_twin_posture import (
    CHANGE_REVIEW_CANDIDATE_EVENT_TYPE,
    POSTURE_CANDIDATE_EVENT_TYPE,
    build_assurance_twin_posture_observer,
)
from fdai.shared.providers.testing.event_bus import InMemoryEventBus
from fdai.shared.providers.testing.state_store import InMemoryStateStore

_TOPIC = "fdai.pipeline.stages"
_SCOPE = "sub/00000000-0000-0000-0000-000000000001"
_REVISION = "sha256:0000000000000000000000000000000000000000000000000000000000000001"


def _finding(rule: str = "r-1", severity: str = "high") -> dict[str, object]:
    return {
        "rule_id": rule,
        "resource_type": "compute.vm",
        "resource_ref": "vm-a",
        "severity": severity,
        "reason": "reason",
        "evidence_refs": [],
    }


def _posture_candidate(**overrides: object) -> dict[str, object]:
    attributes: dict[str, object] = {
        "scope": _SCOPE,
        "generated_at": "2026-07-07T00:00:00Z",
        "mode": "shadow",
        "freshness": "fresh",
        "reason_codes": [],
        "source_revision": _REVISION,
        "findings": [_finding()],
    }
    attributes.update(overrides)
    return {
        "event_type": POSTURE_CANDIDATE_EVENT_TYPE,
        "producer_principal": "Huginn",
        "correlation_id": "correlation-1",
        "attributes": attributes,
    }


def _review_candidate(**overrides: object) -> dict[str, object]:
    attributes: dict[str, object] = {
        "pr_ref": "owner/repo#1",
        "review_key": "Review_Key-1",
        "verdict": "needs_review",
        "generated_at": "2026-07-07T00:00:00Z",
        "mode": "shadow",
        "freshness": "fresh",
        "reason_codes": [],
        "source_revision": _REVISION,
        "findings": [_finding()],
    }
    attributes.update(overrides)
    return {
        "event_type": CHANGE_REVIEW_CANDIDATE_EVENT_TYPE,
        "producer_principal": "Huginn",
        "correlation_id": "correlation-2",
        "attributes": attributes,
    }


def _observer(
    bus: InMemoryEventBus,
    store: InMemoryStateStore,
) -> object:
    return build_assurance_twin_posture_observer(
        state_store=store,
        event_bus=bus,
        topic=_TOPIC,
    )


def _heimdall(bus: InMemoryEventBus, store: InMemoryStateStore) -> Heimdall:
    observer = build_assurance_twin_posture_observer(
        state_store=store,
        event_bus=bus,
        topic=_TOPIC,
    )
    agent = Heimdall()
    agent.register_assurance_twin_posture(observer.observe)
    return agent


async def test_heimdall_records_a_posture_candidate_from_its_event_subscription() -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    agent = _heimdall(bus, store)

    await agent.on_typed_message("object.event", _posture_candidate())

    assert "assurance_twin_posture:recorded" in agent.behavior_snapshot()
    rows = await store.read_states(POSTURE_REPORT_STATE_PREFIX, limit=10)
    assert len(rows) == 1
    assert rows[0]["verdict"] == "blocked"
    assert rows[0]["evidence_source_revision"] == _REVISION

    envelopes = [event async for event in bus.subscribe(_TOPIC, "replay-consumer")]
    assert len(envelopes) == 1
    tip = envelopes[0].payload
    assert tip["kind"] == "assurance-twin.posture"
    assert tip["schema_version"] == "1.2.0"
    assert tip["owner_agent"] == "Heimdall"
    assert tip["producer"] == "assurance-twin"
    assert tip["execution_authority"] is False
    # Event-to-report replay: the durable row names the exact published tip.
    assert rows[0]["activity_id"] == tip["activity_id"]
    assert rows[0]["correlation_id"] == tip["correlation_id"]


async def test_heimdall_records_an_ambient_change_review_candidate() -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    agent = _heimdall(bus, store)

    await agent.on_typed_message("object.event", _review_candidate())

    assert "assurance_twin_posture:recorded" in agent.behavior_snapshot()
    rows = await store.read_states(CHANGE_REVIEW_STATE_PREFIX, limit=10)
    assert len(rows) == 1
    assert rows[0]["review_key"] == "Review_Key-1"


async def test_conflicting_review_candidate_is_held_and_never_overwrites() -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    agent = _heimdall(bus, store)

    await agent.on_typed_message("object.event", _review_candidate())
    await agent.on_typed_message(
        "object.event",
        _review_candidate(verdict="blocked", findings=[_finding(rule="r-2")]),
    )

    assert "assurance_twin_posture:held" in agent.behavior_snapshot()
    rows = await store.read_states(CHANGE_REVIEW_STATE_PREFIX, limit=10)
    assert len(rows) == 1
    assert rows[0]["verdict"] == "needs_review"

    envelopes = [event async for event in bus.subscribe(_TOPIC, "replay-consumer")]
    assert [envelope.payload["freshness"] for envelope in envelopes] == ["fresh", "unavailable"]


async def test_unbound_hook_reports_unavailable_instead_of_a_clear_estate() -> None:
    agent = Heimdall()

    await agent.on_typed_message("object.event", _posture_candidate())

    assert "assurance_twin_posture:unavailable" in agent.behavior_snapshot()


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({"producer_principal": "Bragi"}, "wrong producer principal"),
        ({"correlation_id": ""}, "missing correlation identity"),
        ({"attributes": "not-a-mapping"}, "malformed attributes"),
    ],
)
async def test_malformed_candidate_envelopes_are_rejected(
    payload: dict[str, object],
    reason: str,
) -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    observer = _observer(bus, store)

    candidate = {**_posture_candidate(), **payload}
    assert await observer.observe(candidate) is False, reason  # type: ignore[attr-defined]
    assert await store.read_states(POSTURE_REPORT_STATE_PREFIX, limit=10) == ()


@pytest.mark.parametrize(
    "overrides",
    [
        {"scope": ""},
        {"mode": "audit"},
        {"freshness": "maybe"},
        {"generated_at": "2026-07-07T00:00:00"},
        {"source_revision": ""},
        {"findings": "not-a-list"},
        {"findings": [{"rule_id": "r-1", "severity": "catastrophic"}]},
        {"reason_codes": ["Bad Code"]},
        {"reason_codes": ["dup", "dup"]},
    ],
)
async def test_malformed_posture_attributes_never_produce_evidence(
    overrides: dict[str, object],
) -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    observer = _observer(bus, store)

    assert await observer.observe(_posture_candidate(**overrides)) is False  # type: ignore[attr-defined]
    assert await store.read_states(POSTURE_REPORT_STATE_PREFIX, limit=10) == ()
    assert [event async for event in bus.subscribe(_TOPIC, "replay-consumer")] == []


async def test_unknown_event_type_is_not_treated_as_a_candidate() -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    observer = _observer(bus, store)

    candidate = {**_posture_candidate(), "event_type": "assurance.twin.unknown.v1"}
    assert await observer.observe(candidate) is False  # type: ignore[attr-defined]


async def test_stale_candidate_requires_a_reason_code() -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    observer = _observer(bus, store)

    assert await observer.observe(_posture_candidate(freshness="stale")) is False  # type: ignore[attr-defined]

    recorded = await observer.observe(  # type: ignore[attr-defined]
        _posture_candidate(freshness="stale", reason_codes=["inventory_freshness_ttl_exceeded"])
    )
    assert recorded is True
    envelopes = [event async for event in bus.subscribe(_TOPIC, "replay-consumer")]
    assert envelopes[0].payload["status"] == "degraded"


async def test_unbounded_identity_cannot_overflow_the_derived_activity_id() -> None:
    bus = InMemoryEventBus()
    store = InMemoryStateStore()
    observer = _observer(bus, store)

    overlong = await observer.observe(_review_candidate(review_key="k" * 257))  # type: ignore[attr-defined]
    assert overlong is False
    assert await store.read_states(CHANGE_REVIEW_STATE_PREFIX, limit=10) == ()

    bounded = await observer.observe(_review_candidate(review_key="k" * 256))  # type: ignore[attr-defined]
    assert bounded is True
    envelopes = [event async for event in bus.subscribe(_TOPIC, "replay-consumer")]
    assert len(envelopes[0].payload["activity_id"]) <= 512
