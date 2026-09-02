"""Durable Assurance Twin posture/review ledger tests.

Every case asks one question: can a reader replay the exact evidence a tip
announced, and does a contradicting redelivery fail closed instead of
silently keeping one truth in the ledger and publishing another?
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fdai.core.assurance_twin import build_posture_assessment_report
from fdai.delivery.persistence.state_store_assurance_twin_posture import (
    CONFLICT_MARKER_FIELD,
    REVIEW_CONFLICT_REASON_CODE,
    StateStoreAssuranceTwinPostureLedger,
    change_review_state_key,
    evidence_body_digest,
    posture_report_state_key,
)
from fdai.shared.contracts.models import Mode
from fdai.shared.providers.iac_review import IacReview
from fdai.shared.providers.projection import Finding, ResourceRef
from fdai.shared.providers.testing.state_store import InMemoryStateStore

_SCOPE = "sub/00000000-0000-0000-0000-000000000001"
_PROVENANCE = {
    "activity_id": "assurance-twin.change-review:k-1:completed",
    "correlation_id": "correlation-1",
    "evidence_source_revision": "sha256:feedface",
}


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


async def test_posture_report_write_is_readable_and_overwrites_latest() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    first = await ledger.record_posture_report(
        _report(_finding()),
        freshness="fresh",
        **_PROVENANCE,
    )
    assert first.created is True
    assert first.key == posture_report_state_key(_SCOPE)

    read_back = await ledger.read_latest_posture_report(_SCOPE)
    assert read_back is not None
    assert read_back["scope"] == _SCOPE
    assert read_back["freshness"] == "fresh"
    assert len(read_back["findings"]) == 1

    # A later report for the same scope replaces the prior snapshot.
    second = await ledger.record_posture_report(
        _report(_finding(), _finding(rule="r-2")),
        freshness="fresh",
        **_PROVENANCE,
    )
    assert second.created is True
    replaced = await ledger.read_latest_posture_report(_SCOPE)
    assert replaced is not None
    assert len(replaced["findings"]) == 2


async def test_posture_report_row_carries_replayable_provenance() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    write = await ledger.record_posture_report(
        _report(_finding()),
        freshness="fresh",
        **_PROVENANCE,
    )

    row = await ledger.read_latest_posture_report(_SCOPE)
    assert row is not None
    assert row["activity_id"] == _PROVENANCE["activity_id"]
    assert row["correlation_id"] == _PROVENANCE["correlation_id"]
    assert row["evidence_source_revision"] == _PROVENANCE["evidence_source_revision"]
    assert row["evidence_digest"] == write.evidence_digest
    # The digest covers the evidence body only, so provenance never changes it.
    assert evidence_body_digest(row) == write.evidence_digest


async def test_change_review_write_is_idempotent_by_review_key() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    first = await ledger.record_change_review(
        _review("k-1", _finding()),
        freshness="fresh",
        **_PROVENANCE,
    )
    assert first.created is True
    assert first.conflict is False
    assert first.key == change_review_state_key("k-1")

    duplicate = await ledger.record_change_review(
        _review("k-1", _finding()),
        freshness="fresh",
        **_PROVENANCE,
    )
    assert duplicate.created is False
    assert duplicate.conflict is False
    assert duplicate.evidence_digest == first.evidence_digest

    reviews = await ledger.read_recent_change_reviews(limit=10)
    assert len(reviews) == 1
    assert reviews[0]["review_key"] == "k-1"
    assert reviews[0]["findings"][0]["rule_id"] == "r-1"


async def test_identical_redelivery_under_a_new_correlation_stays_idempotent() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    await ledger.record_change_review(_review("k-1", _finding()), freshness="fresh", **_PROVENANCE)
    replay = await ledger.record_change_review(
        _review("k-1", _finding()),
        freshness="fresh",
        activity_id="assurance-twin.change-review:k-1:completed",
        correlation_id="correlation-2",
        evidence_source_revision="sha256:feedface",
    )

    assert replay.created is False
    assert replay.conflict is False


async def test_conflicting_redelivery_tombstones_the_row_and_keeps_the_stored_body() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    first = await ledger.record_change_review(
        _review("k-1", _finding()),
        freshness="fresh",
        **_PROVENANCE,
    )
    conflicting = await ledger.record_change_review(
        _review("k-1", _finding(rule="r-2"), verdict="blocked"),
        freshness="fresh",
        **_PROVENANCE,
    )

    assert conflicting.created is False
    assert conflicting.conflict is True
    assert conflicting.stored_evidence_digest == first.evidence_digest
    assert conflicting.evidence_digest != first.evidence_digest

    reviews = await ledger.read_recent_change_reviews(limit=10)
    assert len(reviews) == 1
    assert reviews[0]["verdict"] == "needs_review"
    assert reviews[0]["findings"][0]["rule_id"] == "r-1"
    # The durable marker is what makes an Operator API/Console read render
    # the row unavailable instead of serving one of two contradicting bodies.
    marker = reviews[0][CONFLICT_MARKER_FIELD]
    assert marker["reason_code"] == REVIEW_CONFLICT_REASON_CODE
    assert marker["stored_evidence_digest"] == first.evidence_digest
    assert marker["rejected_evidence_digest"] == conflicting.evidence_digest
    # The marker is write history, so the preserved body still verifies.
    assert evidence_body_digest(reviews[0]) == first.evidence_digest


async def test_conflict_marker_is_durable_across_later_redeliveries() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    first = await ledger.record_change_review(
        _review("k-1", _finding()),
        freshness="fresh",
        **_PROVENANCE,
    )
    await ledger.record_change_review(
        _review("k-1", _finding(rule="r-2"), verdict="blocked"),
        freshness="fresh",
        **_PROVENANCE,
    )

    # Replaying the originally stored body cannot clear the conflict.
    replay = await ledger.record_change_review(
        _review("k-1", _finding()),
        freshness="fresh",
        **_PROVENANCE,
    )
    assert replay.conflict is True
    assert replay.created is False
    assert replay.evidence_digest == first.evidence_digest

    rows = await ledger.read_recent_change_reviews(limit=10)
    assert len(rows) == 1
    assert rows[0][CONFLICT_MARKER_FIELD]["reason_code"] == REVIEW_CONFLICT_REASON_CODE
    assert rows[0]["verdict"] == "needs_review"


async def test_conflict_is_detected_against_a_row_without_recorded_provenance() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)
    legacy_body = {
        "pr_ref": "owner/repo#1",
        "review_key": "k-1",
        "verdict": "clear",
        "mode": "shadow",
        "generated_at": "2026-07-07T00:00:00Z",
        "freshness": "fresh",
        "reason_codes": [],
        "metadata": {},
        "findings": [],
    }
    await store.write_state(change_review_state_key("k-1"), legacy_body)

    conflicting = await ledger.record_change_review(
        _review("k-1", _finding()),
        freshness="fresh",
        **_PROVENANCE,
    )

    assert conflicting.conflict is True
    assert conflicting.stored_evidence_digest == evidence_body_digest(legacy_body)


async def test_read_recent_change_reviews_returns_newest_first() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    await ledger.record_change_review(_review("k-1", _finding()), freshness="fresh", **_PROVENANCE)
    await ledger.record_change_review(_review("k-2", _finding()), freshness="fresh", **_PROVENANCE)

    reviews = await ledger.read_recent_change_reviews(limit=10)
    assert [row["review_key"] for row in reviews] == ["k-2", "k-1"]


async def test_read_latest_posture_report_is_none_when_unrecorded() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    assert await ledger.read_latest_posture_report(_SCOPE) is None


def test_empty_scope_is_rejected() -> None:
    with pytest.raises(ValueError, match="scope MUST be non-empty"):
        posture_report_state_key("  ")


def test_empty_review_key_is_rejected() -> None:
    with pytest.raises(ValueError, match="review key MUST be non-empty"):
        change_review_state_key("")


async def test_provenance_identity_is_required() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    with pytest.raises(ValueError, match="activity and correlation identity"):
        await ledger.record_posture_report(
            _report(),
            freshness="fresh",
            activity_id=" ",
            correlation_id="correlation-1",
            evidence_source_revision="sha256:feedface",
        )
    with pytest.raises(ValueError, match="evidence source revision"):
        await ledger.record_posture_report(
            _report(),
            freshness="fresh",
            activity_id="activity-1",
            correlation_id="correlation-1",
            evidence_source_revision="",
        )


async def test_read_recent_change_reviews_bounds_limit() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    with pytest.raises(ValueError, match=r"limit MUST be in \[1, 1000\]"):
        await ledger.read_recent_change_reviews(limit=0)


class _StalledCasStateStore:
    """Wrap ``InMemoryStateStore`` to force two CAS attempts to race.

    Nothing in this in-memory store ever suspends mid-call, so two
    concurrently scheduled coroutines never actually interleave unless a
    call explicitly yields. This wrapper makes the *first* arrival at
    ``compare_and_set_state_with_audit`` block until a *second* concurrent
    caller has also reached the same call, so the deterministic scenario
    this exercises is: two conflict-resolution attempts computed against
    the exact same pre-write snapshot, both trying to tombstone the row,
    with only the underlying compare-and-set - not call order - deciding
    the single winner.
    """

    def __init__(self, inner: InMemoryStateStore) -> None:
        self._inner = inner
        self._arrivals = 0
        self._second_arrived: asyncio.Event = asyncio.Event()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    async def compare_and_set_state_with_audit(
        self,
        key: str,
        value: Any,
        *,
        expected_revision: int,
        audit_entry: Any,
    ) -> bool:
        self._arrivals += 1
        if self._arrivals == 1:
            await self._second_arrived.wait()
        else:
            self._second_arrived.set()
        return await self._inner.compare_and_set_state_with_audit(
            key, value, expected_revision=expected_revision, audit_entry=audit_entry
        )


async def test_concurrent_conflicting_redeliveries_tombstone_exactly_once() -> None:
    """Two different-body redeliveries racing the same tombstone write.

    Both read the identical pre-conflict row, so without a CAS both would
    independently decide to overwrite it with a plain ``write_state`` - a
    lost-update race where the loser's overwrite can silently discard the
    winner's tombstone. With the atomic compare-and-set, exactly one
    concurrent attempt lands; the other loses, re-reads the now-tombstoned
    row, and reports the conflict it observes instead of clobbering it.
    """

    inner = InMemoryStateStore()
    store = _StalledCasStateStore(inner)
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)  # type: ignore[arg-type]

    baseline = await ledger.record_change_review(
        _review("k-1", _finding()),
        freshness="fresh",
        **_PROVENANCE,
    )
    assert baseline.created is True

    results = await asyncio.gather(
        ledger.record_change_review(
            _review("k-1", _finding(rule="r-conflict-a"), verdict="blocked"),
            freshness="fresh",
            **_PROVENANCE,
        ),
        ledger.record_change_review(
            _review("k-1", _finding(rule="r-conflict-b"), verdict="blocked"),
            freshness="fresh",
            **_PROVENANCE,
        ),
    )

    # Neither concurrent conflicting redelivery is ever allowed to publish a
    # completed/available result once its identity is contested.
    assert all(result.conflict is True for result in results)
    assert all(result.created is False for result in results)
    assert all(result.stored_evidence_digest == baseline.evidence_digest for result in results)

    # Exactly one durable mutation lands: the compare-and-set audit trail
    # proves the loser re-read instead of racing a second overwrite.
    conflict_audits = [
        entry
        for entry in inner.audit_entries
        if entry["entry"].get("action_kind") == "assurance_twin.review_conflict_marked"
    ]
    assert len(conflict_audits) == 1

    rows = await ledger.read_recent_change_reviews(limit=10)
    assert len(rows) == 1
    assert rows[0]["verdict"] == "needs_review"
    assert rows[0]["findings"][0]["rule_id"] == "r-1"
    marker = rows[0][CONFLICT_MARKER_FIELD]
    assert marker["reason_code"] == REVIEW_CONFLICT_REASON_CODE
    assert marker["stored_evidence_digest"] == baseline.evidence_digest
    # The winning rejected digest is one of the two racers, never a third
    # value and never the baseline's own digest.
    assert marker["rejected_evidence_digest"] in {result.evidence_digest for result in results}


async def test_concurrent_duplicate_conflict_after_tombstone_never_publishes_available() -> None:
    """A duplicate racing the very write that first tombstones its identity.

    Simulates the exact regression this hardens: a redelivery of the
    *same* conflicting body arrives twice, concurrently. Under the old
    read-then-``write_state`` sequence, both racers could observe the
    pre-conflict row and one's plain overwrite could silently replace the
    other's tombstone. With the CAS, only one lands; the loser's retry
    observes the marker its sibling wrote and reports conflict, never a
    completed/available outcome for either racer.
    """

    inner = InMemoryStateStore()
    store = _StalledCasStateStore(inner)
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)  # type: ignore[arg-type]

    baseline = await ledger.record_change_review(
        _review("k-1", _finding()),
        freshness="fresh",
        **_PROVENANCE,
    )

    duplicate_conflicting_review = _review("k-1", _finding(rule="r-2"), verdict="blocked")
    results = await asyncio.gather(
        ledger.record_change_review(
            duplicate_conflicting_review,
            freshness="fresh",
            **_PROVENANCE,
        ),
        ledger.record_change_review(
            duplicate_conflicting_review,
            freshness="fresh",
            **_PROVENANCE,
        ),
    )

    assert all(result.conflict is True for result in results)
    assert {result.evidence_digest for result in results} == {results[0].evidence_digest}
    assert all(result.stored_evidence_digest == baseline.evidence_digest for result in results)

    conflict_audits = [
        entry
        for entry in inner.audit_entries
        if entry["entry"].get("action_kind") == "assurance_twin.review_conflict_marked"
    ]
    assert len(conflict_audits) == 1


async def test_concurrent_creation_race_is_won_by_exactly_one_writer() -> None:
    """Two brand-new-key writes racing ``write_state_if_absent`` itself.

    The first-writer-wins path was already atomic via the underlying
    ``write_state_if_absent`` primitive; this asserts that guarantee still
    holds end to end through the ledger when both callers race a key that
    has never been written. (No CAS stall is needed here: only the loser
    of ``write_state_if_absent`` ever reaches the compare-and-set path.)
    """

    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    results = await asyncio.gather(
        ledger.record_change_review(
            _review("k-new", _finding(rule="r-a")),
            freshness="fresh",
            **_PROVENANCE,
        ),
        ledger.record_change_review(
            _review("k-new", _finding(rule="r-b"), verdict="blocked"),
            freshness="fresh",
            **_PROVENANCE,
        ),
    )

    created_results = [result for result in results if result.created]
    assert len(created_results) == 1
    conflicting = [result for result in results if not result.created]
    assert len(conflicting) == 1
    assert conflicting[0].conflict is True
    assert conflicting[0].stored_evidence_digest == created_results[0].evidence_digest
