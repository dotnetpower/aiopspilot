"""Assurance Twin posture/review projection - state_kv rows to Console envelopes.

The twin's runtime already computed the verdict, severity, and freshness
before persisting the row (``fdai.delivery.assurance_twin_posture`` on the
Core side); this module renders that stored content as-is. It never
re-derives a verdict, freshness, or severity - only shape and bound the
already-authoritative fields so a malformed row degrades to an explicit
unavailable/gap state instead of a guess.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

_MAX_ITEMS = 200
_SEVERITIES = ("low", "medium", "high", "critical")
_FRESHNESS_STATES = ("fresh", "stale", "unavailable", "unknown")
_VERDICTS = ("clear", "needs_review", "blocked")
_MODES = ("shadow", "enforce")


def assurance_twin_posture_projection(rows: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    """Project the latest recorded posture report(s), newest first.

    Returns an explicit unavailable envelope when no report was ever
    recorded, rather than inferring a clear posture from silence.
    """

    reports = []
    for row in rows[:_MAX_ITEMS]:
        report = _posture_report(row)
        if report is not None:
            reports.append(report)
    reports.sort(key=lambda item: str(item["generated_at"]), reverse=True)
    return {
        "surface": "assurance-twin-posture",
        "available": bool(reports),
        "source": "postgresql:state_kv:assurance-twin-posture",
        "reports": reports,
    }


def assurance_twin_review_list_projection(rows: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    """Project bounded ambient change-review summaries, newest first."""

    reviews = []
    for row in rows[:_MAX_ITEMS]:
        review = _review_summary(row)
        if review is not None:
            reviews.append(review)
    reviews.sort(key=lambda item: str(item["generated_at"]), reverse=True)
    return {
        "surface": "assurance-twin-review",
        "available": bool(reviews),
        "source": "postgresql:state_kv:assurance-twin-review",
        "reviews": reviews,
    }


def assurance_twin_review_detail_projection(
    row: Mapping[str, Any] | None,
) -> dict[str, object] | None:
    """Project one ambient change-review's full finding evidence, if present."""

    if row is None:
        return None
    value = _mapping(row.get("value"), "assurance twin review value")
    if value is None:
        return None
    summary = _review_summary(row)
    if summary is None:
        return None
    findings = _findings(value.get("findings"))
    if findings is None:
        return None
    return {**summary, "findings": findings}


def _posture_report(row: Mapping[str, Any]) -> dict[str, object] | None:
    value = _mapping(row.get("value"), "assurance twin posture value")
    if value is None:
        return None
    scope = _text(value.get("scope"))
    generated_at = _timestamp(value.get("generated_at"))
    mode = _enum(value.get("mode"), _MODES)
    verdict = _enum(value.get("verdict"), _VERDICTS)
    freshness = _enum(value.get("freshness"), _FRESHNESS_STATES)
    if (
        scope is None
        or generated_at is None
        or mode is None
        or verdict is None
        or freshness is None
    ):
        return None
    severity_counts = _severity_counts(value.get("severity_counts"))
    if severity_counts is None:
        return None
    findings = _findings(value.get("findings"))
    if findings is None:
        return None
    highest_severity = value.get("highest_severity")
    if highest_severity is not None and highest_severity not in _SEVERITIES:
        return None
    return {
        "scope": scope,
        "generated_at": generated_at,
        "mode": mode,
        "verdict": verdict,
        "blocks_action": bool(value.get("blocks_action", False)),
        "resource_count": _bounded_int(value.get("resource_count")),
        "rule_count": _bounded_int(value.get("rule_count")),
        "highest_severity": highest_severity,
        "severity_counts": severity_counts,
        "finding_count": len(findings),
        "findings": findings,
        "freshness": freshness,
        "reason_codes": _string_list(value.get("reason_codes")),
    }


def _review_summary(row: Mapping[str, Any]) -> dict[str, object] | None:
    value = _mapping(row.get("value"), "assurance twin review value")
    if value is None:
        return None
    review_key = _text(value.get("review_key"))
    pr_ref = _text(value.get("pr_ref"))
    generated_at = _timestamp(value.get("generated_at"))
    mode = _enum(value.get("mode"), _MODES)
    verdict = _enum(value.get("verdict"), _VERDICTS)
    freshness = _enum(value.get("freshness"), _FRESHNESS_STATES)
    if (
        review_key is None
        or pr_ref is None
        or generated_at is None
        or mode is None
        or verdict is None
        or freshness is None
    ):
        return None
    raw_findings = value.get("findings")
    finding_count = len(raw_findings) if isinstance(raw_findings, list) else 0
    return {
        "review_key": review_key,
        "pr_ref": pr_ref,
        "generated_at": generated_at,
        "mode": mode,
        "verdict": verdict,
        "finding_count": finding_count,
        "freshness": freshness,
        "reason_codes": _string_list(value.get("reason_codes")),
    }


def _findings(value: object) -> list[dict[str, object]] | None:
    if not isinstance(value, list):
        return None
    findings: list[dict[str, object]] = []
    for item in value[:_MAX_ITEMS]:
        if not isinstance(item, Mapping):
            return None
        rule_id = _text(item.get("rule_id"))
        resource_type = _text(item.get("resource_type"))
        resource_ref = _text(item.get("resource_ref"))
        severity = _enum(item.get("severity"), _SEVERITIES)
        reason = _text(item.get("reason"))
        if (
            rule_id is None
            or resource_type is None
            or resource_ref is None
            or severity is None
            or reason is None
        ):
            return None
        findings.append(
            {
                "rule_id": rule_id,
                "resource_type": resource_type,
                "resource_ref": resource_ref,
                "severity": severity,
                "reason": reason,
                "evidence_refs": _string_list(item.get("evidence_refs")),
            }
        )
    return findings


def _severity_counts(value: object) -> dict[str, int] | None:
    if not isinstance(value, Mapping):
        return None
    counts: dict[str, int] = {}
    for severity in _SEVERITIES:
        count = _bounded_int(value.get(severity))
        if count is None:
            return None
        counts[severity] = count
    return counts


def _mapping(value: object, _label: str) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    return None


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _enum(value: object, allowed: tuple[str, ...]) -> str | None:
    return value if isinstance(value, str) and value in allowed else None


def _bounded_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if not 0 <= value <= 1_000_000:
        return None
    return value


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)][:_MAX_ITEMS]


def _timestamp(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC).isoformat()


__all__ = [
    "assurance_twin_posture_projection",
    "assurance_twin_review_detail_projection",
    "assurance_twin_review_list_projection",
]
