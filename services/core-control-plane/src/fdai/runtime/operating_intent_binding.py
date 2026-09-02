"""Parse the operator-pinned operating-intent binding out of process configuration.

Separated from the admission runtime so configuration parsing has exactly one reason
to change. Every function here is a boundary validator: it rejects a malformed or
incomplete binding with an explicit English error instead of substituting a default,
because a silently defaulted pin would admit a source no operator ever reviewed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from fdai.core.operational_context import OperatingIntentSourceBinding


def operating_intent_positive_int(values: Mapping[str, str], key: str, default: int) -> int:
    """Return one positive integer setting, or ``default`` when the key is absent."""

    raw = values.get(key, "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{key} MUST be an integer") from exc
    if parsed < 1:
        raise RuntimeError(f"{key} MUST be a positive integer")
    return parsed


def operating_intent_binding_from_env(values: Mapping[str, str]) -> OperatingIntentSourceBinding:
    """Return the exact operator-pinned expectation a candidate source MUST satisfy."""

    expected_revision = values.get("FDAI_OPERATING_INTENT_SOURCE_REVISION", "").strip()
    if not expected_revision:
        raise RuntimeError(
            "FDAI_OPERATING_INTENT_SOURCE_PATH requires FDAI_OPERATING_INTENT_SOURCE_REVISION"
        )
    expected_sha256 = values.get("FDAI_OPERATING_INTENT_SOURCE_SHA256", "").strip()
    if not expected_sha256:
        raise RuntimeError(
            "FDAI_OPERATING_INTENT_SOURCE_PATH requires FDAI_OPERATING_INTENT_SOURCE_SHA256"
        )
    raw_counts = values.get("FDAI_OPERATING_INTENT_SOURCE_EXPECTED_COUNTS_JSON", "").strip()
    expected_counts: dict[str, int] = {}
    if raw_counts:
        try:
            parsed = json.loads(raw_counts)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FDAI_OPERATING_INTENT_SOURCE_EXPECTED_COUNTS_JSON MUST be a JSON object"
            ) from exc
        if not isinstance(parsed, dict):
            raise RuntimeError(
                "FDAI_OPERATING_INTENT_SOURCE_EXPECTED_COUNTS_JSON MUST be a JSON object"
            )
        expected_counts = parsed
    return OperatingIntentSourceBinding(
        expected_revision=expected_revision,
        expected_sha256=expected_sha256,
        expected_instance_counts=expected_counts,
    )


def decode_operating_intent_manifest(
    raw: Mapping[str, object] | None,
) -> tuple[tuple[str, ...], tuple[tuple[str, str, str], ...]]:
    """Return the object ids and link keys the intent source manifest currently owns."""

    if raw is None:
        return (), ()
    raw_ids = raw.get("object_ids")
    raw_links = raw.get("link_keys")
    if not isinstance(raw_ids, list) or not isinstance(raw_links, list):
        raise RuntimeError("operating intent source manifest is malformed")
    if any(not isinstance(item, str) or not item for item in raw_ids):
        raise RuntimeError("operating intent source manifest object_ids are malformed")
    links: list[tuple[str, str, str]] = []
    for item in raw_links:
        if (
            not isinstance(item, list)
            or len(item) != 3
            or any(not isinstance(value, str) or not value for value in item)
        ):
            raise RuntimeError("operating intent source manifest link_keys are malformed")
        links.append((item[0], item[1], item[2]))
    return tuple(raw_ids), tuple(links)


__all__ = [
    "decode_operating_intent_manifest",
    "operating_intent_binding_from_env",
    "operating_intent_positive_int",
]
