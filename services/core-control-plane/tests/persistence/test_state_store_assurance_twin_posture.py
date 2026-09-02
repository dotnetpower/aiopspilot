"""Durable Assurance Twin posture/review ledger tests."""

from __future__ import annotations

import pytest
from fdai.core.assurance_twin import build_posture_assessment_report
from fdai.delivery.persistence.state_store_assurance_twin_posture import (
    StateStoreAssuranceTwinPostureLedger,
    change_review_state_key,
    posture_report_state_key,
)
from fdai.shared.contracts.models import Mode
from fdai.shared.providers.iac_review import IacReview
from fdai.shared.providers.projection import Finding, ResourceRef
from fdai.shared.providers.testing.state_store import InMemoryStateStore

_SCOPE = "sub/00000000-0000-0000-0000-000000000001"


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


def _review(key: str = "k-1", *findings: Finding) -> IacReview:
    return IacReview(
        pr_ref="owner/repo#1",
        review_key=key,
        findings=findings,
        verdict="needs_review",
        mode=Mode.SHADOW,
        generated_at="2026-07-07T00:00:00Z",
    )


async def test_posture_report_write_is_readable_and_overwrites_latest() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    first = await ledger.record_posture_report(
        _report(_finding()),
        freshness="fresh",
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
    )
    assert second.created is True
    replaced = await ledger.read_latest_posture_report(_SCOPE)
    assert replaced is not None
    assert len(replaced["findings"]) == 2


async def test_change_review_write_is_idempotent_by_review_key() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    first = await ledger.record_change_review(_review("k-1", _finding()), freshness="fresh")
    assert first.created is True
    assert first.key == change_review_state_key("k-1")

    duplicate = await ledger.record_change_review(_review("k-1", _finding()), freshness="fresh")
    assert duplicate.created is False

    reviews = await ledger.read_recent_change_reviews(limit=10)
    assert len(reviews) == 1
    assert reviews[0]["review_key"] == "k-1"
    assert reviews[0]["findings"][0]["rule_id"] == "r-1"


async def test_read_recent_change_reviews_returns_newest_first() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    await ledger.record_change_review(_review("k-1", _finding()), freshness="fresh")
    await ledger.record_change_review(_review("k-2", _finding()), freshness="fresh")

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


async def test_read_recent_change_reviews_bounds_limit() -> None:
    store = InMemoryStateStore()
    ledger = StateStoreAssuranceTwinPostureLedger(store=store)

    with pytest.raises(ValueError, match=r"limit MUST be in \[1, 1000\]"):
        await ledger.read_recent_change_reviews(limit=0)
