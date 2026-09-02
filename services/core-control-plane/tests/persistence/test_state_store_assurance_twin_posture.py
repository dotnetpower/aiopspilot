"""Durable Assurance Twin posture/review ledger tests.

Every case asks one question: can a reader replay the exact evidence a tip
announced, and does a contradicting redelivery fail closed instead of
silently keeping one truth in the ledger and publishing another?
"""

from __future__ import annotations

import pytest
from fdai.core.assurance_twin import build_posture_assessment_report
from fdai.delivery.persistence.state_store_assurance_twin_posture import (
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


async def test_conflicting_redelivery_never_replaces_the_durable_body() -> None:
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
