"""Assurance Twin posture/review projection - state_kv rows to Console envelopes.

The twin's runtime already computed the verdict, severity, and freshness
before persisting the row (``fdai.delivery.assurance_twin_posture`` on the
Core side); this module renders that stored content as-is. It never
re-derives a verdict, freshness, or severity.

Fail-closed contract
--------------------

A row becomes a rendered **report** only when it is well formed, its
recorded provenance digest matches its body, its recorded freshness is
``fresh``, and it carries no durable conflict marker. Every other row
becomes an explicit **gap** carrying a reason code and, when decodable, its
identity and freshness. A stale, unavailable, unknown, malformed,
digest-mismatched, or conflict-tombstoned row is therefore never rendered as
a usable posture, and an empty ``reports`` list never reads as a clear
estate: ``available`` states whether any usable report exists and
``complete`` states whether anything was withheld.

Safety-relevant flags are read strictly: ``blocks_action`` MUST be a present
boolean. A missing value or a truthy string is malformed evidence, not a
default, because coercing it would silently render a blocking posture as
non-blocking.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

_MAX_ITEMS = 200
_SEVERITIES = ("low", "medium", "high", "critical")
_FRESHNESS_STATES = ("fresh", "stale", "unavailable", "unknown")
_USABLE_FRESHNESS = "fresh"
_VERDICTS = ("clear", "needs_review", "blocked")
_MODES = ("shadow", "enforce")

#: Provenance fields describe the write, not the twin's evidence body. They
#: mirror ``fdai.delivery.persistence.state_store_assurance_twin_posture``;
#: the two services stay independently packaged, so the digest rule is
#: restated here rather than imported across a service boundary.
_PROVENANCE_FIELDS = frozenset(
    {
        "activity_id",
        "correlation_id",
        "evidence_digest",
        "evidence_source_revision",
        "conflict",
    }
)

#: Row field the recorder writes when one identity received two different
#: evidence bodies. Its presence alone makes the row permanently unusable.
_CONFLICT_MARKER_FIELD = "conflict"

GAP_MALFORMED = "evidence_malformed"
GAP_DIGEST_MISMATCH = "evidence_digest_mismatch"
GAP_CONFLICT = "evidence_conflict"
GAP_NOT_FRESH = "evidence_not_fresh"
GAP_TRUNCATED = "evidence_truncated"

POSTURE_SOURCE = "postgresql:state_kv:assurance-twin-posture"
REVIEW_SOURCE = "postgresql:state_kv:assurance-twin-review"


def assurance_twin_posture_projection(rows: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    """Project the latest recorded posture report(s), newest first.

    Returns an explicit unavailable envelope when no usable report exists,
    rather than inferring a clear posture from silence or from evidence the
    twin itself marked stale.
    """

    reports, gaps = _classify(rows, decode=_posture_report, identity_key="scope")
    reports.sort(key=lambda item: str(item["generated_at"]), reverse=True)
    return {
        "surface": "assurance-twin-posture",
        "available": bool(reports),
        "complete": not gaps,
        "source": POSTURE_SOURCE,
        "reports": reports,
        "gaps": gaps,
    }


def assurance_twin_review_list_projection(rows: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    """Project bounded ambient change-review summaries, newest first."""

    reviews, gaps = _classify(rows, decode=_review_summary, identity_key="review_key")
    reviews.sort(key=lambda item: str(item["generated_at"]), reverse=True)
    return {
        "surface": "assurance-twin-review",
        "available": bool(reviews),
        "complete": not gaps,
        "source": REVIEW_SOURCE,
        "reviews": reviews,
        "gaps": gaps,
    }


def assurance_twin_review_detail_projection(
    row: Mapping[str, Any] | None,
) -> dict[str, object] | None:
    """Project one ambient change-review's full finding evidence, if present.

    ``None`` means the row does not exist (the caller renders 404). A row
    that exists but cannot be rendered as usable evidence returns an
    explicit unavailable envelope instead of a fabricated clear detail.
    """

    if row is None:
        return None
    value = _mapping(row.get("value"))
    if value is None:
        return _detail_gap(_gap(None, None, GAP_MALFORMED))
    identity = _text(value.get("review_key"))
    freshness = _enum(value.get("freshness"), _FRESHNESS_STATES)
    reason_codes = _string_list(value.get("reason_codes"))
    digest_reason = _digest_reason(value)
    if digest_reason is not None:
        return _detail_gap(_gap(identity, freshness, digest_reason, reason_codes))
    summary = _review_summary(row)
    findings = _findings(value.get("findings"))
    if summary is None or findings is None:
        return _detail_gap(_gap(identity, freshness, GAP_MALFORMED, reason_codes))
    if summary["freshness"] != _USABLE_FRESHNESS:
        return _detail_gap(_gap(identity, freshness, GAP_NOT_FRESH, reason_codes))
    return {
        "surface": "assurance-twin-review-detail",
        "source": REVIEW_SOURCE,
        "available": True,
        "review": {**summary, "findings": findings},
        "gap": None,
    }


def _detail_gap(gap: dict[str, object]) -> dict[str, object]:
    return {
        "surface": "assurance-twin-review-detail",
        "source": REVIEW_SOURCE,
        "available": False,
        "review": None,
        "gap": gap,
    }


def _classify(
    rows: Sequence[Mapping[str, Any]],
    *,
    decode: Any,
    identity_key: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Split bounded rows into usable records and explicit evidence gaps."""

    usable: list[dict[str, object]] = []
    gaps: list[dict[str, object]] = []
    digests_by_identity: dict[str, set[str]] = {}
    if len(rows) > _MAX_ITEMS:
        gaps.append(_gap(None, None, GAP_TRUNCATED))
    for row in rows[:_MAX_ITEMS]:
        value = row.get("value")
        if not isinstance(value, Mapping):
            gaps.append(_gap(None, None, GAP_MALFORMED))
            continue
        identity = _text(value.get(identity_key))
        freshness = _enum(value.get("freshness"), _FRESHNESS_STATES)
        reason_codes = _string_list(value.get("reason_codes"))
        digest_reason = _digest_reason(value)
        if digest_reason is not None:
            gaps.append(_gap(identity, freshness, digest_reason, reason_codes))
            continue
        record = decode(row)
        if record is None:
            gaps.append(_gap(identity, freshness, GAP_MALFORMED, reason_codes))
            continue
        if record["freshness"] != _USABLE_FRESHNESS:
            gaps.append(_gap(identity, freshness, GAP_NOT_FRESH, reason_codes))
            continue
        if identity is not None:
            digests_by_identity.setdefault(identity, set()).add(str(record["evidence_digest"]))
        usable.append(record)

    conflicting = {
        identity for identity, digests in digests_by_identity.items() if len(digests) > 1
    }
    if conflicting:
        retained = [record for record in usable if str(record[identity_key]) not in conflicting]
        gaps.extend(_gap(identity, None, GAP_CONFLICT) for identity in sorted(conflicting))
        usable = retained
    return usable, gaps


def _gap(
    identity: str | None,
    freshness: str | None,
    reason_code: str,
    reason_codes: list[str] | None = None,
) -> dict[str, object]:
    return {
        "identity": identity,
        "freshness": freshness,
        "reason_code": reason_code,
        "reason_codes": reason_codes or [],
    }


def _digest_reason(value: Mapping[str, Any]) -> str | None:
    """Return a gap reason when the row is tombstoned or fails provenance."""

    if _CONFLICT_MARKER_FIELD in value:
        return GAP_CONFLICT
    recorded = value.get("evidence_digest")
    if not isinstance(recorded, str) or not recorded:
        return GAP_MALFORMED
    if not isinstance(value.get("activity_id"), str) or not value["activity_id"]:
        return GAP_MALFORMED
    if not isinstance(value.get("correlation_id"), str) or not value["correlation_id"]:
        return GAP_MALFORMED
    if not isinstance(value.get("evidence_source_revision"), str):
        return GAP_MALFORMED
    if _evidence_body_digest(value) != recorded:
        return GAP_DIGEST_MISMATCH
    return None


def _evidence_body_digest(value: Mapping[str, Any]) -> str:
    material = {key: item for key, item in value.items() if key not in _PROVENANCE_FIELDS}
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def _provenance(value: Mapping[str, Any]) -> dict[str, object]:
    return {
        "activity_id": value.get("activity_id"),
        "correlation_id": value.get("correlation_id"),
        "evidence_digest": value.get("evidence_digest"),
        "evidence_source_revision": value.get("evidence_source_revision"),
    }


def _posture_report(row: Mapping[str, Any]) -> dict[str, object] | None:
    value = _mapping(row.get("value"))
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
    resource_count = _bounded_int(value.get("resource_count"))
    rule_count = _bounded_int(value.get("rule_count"))
    if resource_count is None or rule_count is None:
        return None
    highest_severity = value.get("highest_severity")
    if highest_severity is not None and highest_severity not in _SEVERITIES:
        return None
    blocks_action = value.get("blocks_action")
    if not isinstance(blocks_action, bool):
        return None
    return {
        "scope": scope,
        "generated_at": generated_at,
        "mode": mode,
        "verdict": verdict,
        "blocks_action": blocks_action,
        "resource_count": resource_count,
        "rule_count": rule_count,
        "highest_severity": highest_severity,
        "severity_counts": severity_counts,
        "finding_count": len(findings),
        "findings": findings,
        "freshness": freshness,
        "reason_codes": _string_list(value.get("reason_codes")),
        **_provenance(value),
    }


def _review_summary(row: Mapping[str, Any]) -> dict[str, object] | None:
    value = _mapping(row.get("value"))
    if value is None:
        return None
    review_key = _text(value.get("review_key"))
    pr_ref = _text(value.get("pr_ref"))
    generated_at = _timestamp(value.get("generated_at"))
    mode = _enum(value.get("mode"), _MODES)
    verdict = _enum(value.get("verdict"), _VERDICTS)
    freshness = _enum(value.get("freshness"), _FRESHNESS_STATES)
    findings = _findings(value.get("findings"))
    if (
        review_key is None
        or pr_ref is None
        or generated_at is None
        or mode is None
        or verdict is None
        or freshness is None
        or findings is None
    ):
        return None
    return {
        "review_key": review_key,
        "pr_ref": pr_ref,
        "generated_at": generated_at,
        "mode": mode,
        "verdict": verdict,
        "finding_count": len(findings),
        "freshness": freshness,
        "reason_codes": _string_list(value.get("reason_codes")),
        **_provenance(value),
    }


def _findings(value: object) -> list[dict[str, object]] | None:
    if not isinstance(value, list):
        return None
    if len(value) > _MAX_ITEMS:
        return None
    findings: list[dict[str, object]] = []
    for item in value:
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


def _mapping(value: object) -> Mapping[str, Any] | None:
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
    "GAP_CONFLICT",
    "GAP_DIGEST_MISMATCH",
    "GAP_MALFORMED",
    "GAP_NOT_FRESH",
    "GAP_TRUNCATED",
    "assurance_twin_posture_projection",
    "assurance_twin_review_detail_projection",
    "assurance_twin_review_list_projection",
]
