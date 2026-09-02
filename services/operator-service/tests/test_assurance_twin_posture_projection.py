"""Assurance Twin posture/review projection tests.

The Operator Service does not compute the twin's verdict, severity, or
freshness - it only shapes rows the twin already wrote. Every test below
asks whether a malformed row produces an explicit unavailable/gap outcome
rather than a fabricated one.
"""

from __future__ import annotations

from typing import Any

from fdai_operator_service.assurance_twin_posture_projection import (
    assurance_twin_posture_projection,
    assurance_twin_review_detail_projection,
    assurance_twin_review_list_projection,
)

_POSTURE_VALUE: dict[str, Any] = {
    "scope": "sub/00000000-0000-0000-0000-000000000001",
    "generated_at": "2026-07-07T00:00:00Z",
    "mode": "shadow",
    "verdict": "blocked",
    "blocks_action": False,
    "resource_count": 1,
    "rule_count": 1,
    "highest_severity": "high",
    "severity_counts": {"low": 0, "medium": 0, "high": 1, "critical": 0},
    "findings": [
        {
            "rule_id": "r-1",
            "resource_type": "compute.vm",
            "resource_ref": "vm-a",
            "severity": "high",
            "reason": "reason",
            "evidence_refs": [],
        }
    ],
    "freshness": "fresh",
    "reason_codes": [],
}

_REVIEW_VALUE: dict[str, Any] = {
    "pr_ref": "owner/repo#1",
    "review_key": "k-1",
    "verdict": "needs_review",
    "mode": "shadow",
    "generated_at": "2026-07-07T00:00:00Z",
    "freshness": "fresh",
    "reason_codes": [],
    "findings": [
        {
            "rule_id": "r-1",
            "resource_type": "compute.vm",
            "resource_ref": "vm-a",
            "severity": "high",
            "reason": "reason",
            "evidence_refs": [],
        }
    ],
}


def test_posture_projection_is_unavailable_when_no_rows_exist() -> None:
    projection = assurance_twin_posture_projection(())
    assert projection["available"] is False
    assert projection["reports"] == []


def test_posture_projection_renders_a_recorded_report_verbatim() -> None:
    projection = assurance_twin_posture_projection(({"value": _POSTURE_VALUE},))
    assert projection["available"] is True
    reports = projection["reports"]
    assert isinstance(reports, list)
    report = reports[0]
    assert report["verdict"] == "blocked"
    assert report["finding_count"] == 1
    assert report["severity_counts"] == {"low": 0, "medium": 0, "high": 1, "critical": 0}
    assert report["freshness"] == "fresh"


def test_posture_projection_drops_a_row_with_an_invalid_verdict() -> None:
    malformed = {**_POSTURE_VALUE, "verdict": "not-a-real-verdict"}
    projection = assurance_twin_posture_projection(({"value": malformed},))
    assert projection["available"] is False
    assert projection["reports"] == []


def test_posture_projection_drops_a_row_with_incomplete_severity_counts() -> None:
    malformed = {**_POSTURE_VALUE, "severity_counts": {"low": 0}}
    projection = assurance_twin_posture_projection(({"value": malformed},))
    assert projection["available"] is False


def test_posture_projection_sorts_multiple_reports_newest_first() -> None:
    older = {**_POSTURE_VALUE, "scope": "sub/a", "generated_at": "2026-01-01T00:00:00Z"}
    newer = {**_POSTURE_VALUE, "scope": "sub/b", "generated_at": "2026-06-01T00:00:00Z"}
    projection = assurance_twin_posture_projection(({"value": older}, {"value": newer}))
    reports = projection["reports"]
    assert isinstance(reports, list)
    assert [report["scope"] for report in reports] == ["sub/b", "sub/a"]


def test_review_list_projection_is_unavailable_when_no_rows_exist() -> None:
    projection = assurance_twin_review_list_projection(())
    assert projection["available"] is False
    assert projection["reviews"] == []


def test_review_list_projection_renders_a_recorded_review_summary() -> None:
    projection = assurance_twin_review_list_projection(({"value": _REVIEW_VALUE},))
    assert projection["available"] is True
    reviews = projection["reviews"]
    assert isinstance(reviews, list)
    review = reviews[0]
    assert review["review_key"] == "k-1"
    assert review["finding_count"] == 1
    assert "findings" not in review


def test_review_detail_projection_is_none_when_row_is_absent() -> None:
    assert assurance_twin_review_detail_projection(None) is None


def test_review_detail_projection_includes_finding_evidence() -> None:
    detail = assurance_twin_review_detail_projection({"value": _REVIEW_VALUE})
    assert detail is not None
    assert detail["review_key"] == "k-1"
    findings = detail["findings"]
    assert isinstance(findings, list)
    assert findings[0]["rule_id"] == "r-1"


def test_review_detail_projection_is_none_for_malformed_findings() -> None:
    malformed = {**_REVIEW_VALUE, "findings": "not-a-list"}
    assert assurance_twin_review_detail_projection({"value": malformed}) is None
