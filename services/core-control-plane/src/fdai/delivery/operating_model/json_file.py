"""Bounded JSON-file adapter for deployment operating model instances."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fdai.shared.providers.ontology_instance import (
    OntologyInstanceValidationError,
    OntologyLinkRecord,
    OntologyObjectRecord,
    normalize_json_value,
)
from fdai.shared.providers.operating_model import (
    OperatingIntentSourceDocument,
    OperatingIntentSourceProvenance,
    OperatingModelSnapshot,
)


@dataclass(frozen=True, slots=True)
class JsonOperatingModelProviderConfig:
    path: Path
    max_bytes: int = 16 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.max_bytes < 1:
            raise ValueError("operating model max_bytes MUST be >= 1")


class JsonOperatingModelProvider:
    def __init__(self, *, config: JsonOperatingModelProviderConfig) -> None:
        self._config = config

    async def load(self) -> OperatingModelSnapshot:
        raw = await asyncio.to_thread(
            _read_bounded_document, self._config.path, self._config.max_bytes
        )
        return operating_model_snapshot_from_mapping(raw)


class JsonOperatingIntentSourceProvider:
    """Load the deployment-owned operating-intent source, provenance included."""

    def __init__(self, *, config: JsonOperatingModelProviderConfig) -> None:
        self._config = config

    async def load(self) -> OperatingIntentSourceDocument:
        raw = await asyncio.to_thread(
            _read_bounded_document, self._config.path, self._config.max_bytes
        )
        return operating_intent_source_document_from_mapping(raw)


def _read_bounded_document(path: Path, max_bytes: int) -> Mapping[str, object]:
    if path.stat().st_size > max_bytes:
        raise ValueError("operating model file exceeds max_bytes")
    content = path.read_text(encoding="utf-8")
    try:
        raw = normalize_json_value(json.loads(content), path="operating_model")
    except (json.JSONDecodeError, RecursionError, OntologyInstanceValidationError) as exc:
        raise ValueError("operating model file MUST contain bounded canonical JSON") from exc
    if not isinstance(raw, Mapping):
        raise ValueError("operating model document MUST be an object")
    return raw


def _array(value: Mapping[str, object], key: str) -> Sequence[object]:
    raw = value.get(key)
    if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
        raise ValueError(f"operating model {key} MUST be an array")
    return raw


def operating_model_snapshot_from_mapping(
    raw: Mapping[str, object],
) -> OperatingModelSnapshot:
    """Parse one already bounded JSON mapping into a complete snapshot."""

    objects = _array(raw, "objects")
    links = _array(raw, "links")
    return OperatingModelSnapshot(
        source_revision=_required_string(raw, "source_revision"),
        objects=tuple(_object_record(item) for item in objects),
        links=tuple(_link_record(item) for item in links),
    )


def operating_intent_source_document_from_mapping(
    raw: Mapping[str, object],
) -> OperatingIntentSourceDocument:
    """Parse one deployment-owned operating-intent source document.

    Unlike the generic operating-model file, this format MUST carry a ``provenance``
    block so the runtime binding can verify exact revision and provenance before
    projecting any of the six operating-intent ObjectTypes.
    """

    return OperatingIntentSourceDocument(
        snapshot=operating_model_snapshot_from_mapping(raw),
        provenance=_provenance(raw),
    )


def _provenance(raw: Mapping[str, object]) -> OperatingIntentSourceProvenance:
    value = raw.get("provenance")
    if not isinstance(value, Mapping):
        raise ValueError("operating intent source provenance MUST be an object")
    retrieved_at_raw = value.get("retrieved_at")
    if not isinstance(retrieved_at_raw, str) or not retrieved_at_raw.strip():
        raise ValueError("operating intent source provenance.retrieved_at MUST be non-empty")
    try:
        retrieved_at = datetime.fromisoformat(retrieved_at_raw)
    except ValueError as exc:
        raise ValueError(
            "operating intent source provenance.retrieved_at MUST be an RFC 3339 timestamp"
        ) from exc
    return OperatingIntentSourceProvenance(
        source_url=_required_string(value, "source_url"),
        resolved_ref=_required_string(value, "resolved_ref"),
        retrieved_at=retrieved_at,
    )


def _required_string(value: Mapping[str, object], key: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"operating model {key} MUST be non-empty")
    return raw


def _object_record(raw: object) -> OntologyObjectRecord:
    if not isinstance(raw, Mapping):
        raise ValueError("operating model object entries MUST be objects")
    properties = raw.get("properties")
    if not isinstance(properties, Mapping):
        raise ValueError("operating model object properties MUST be an object")
    return OntologyObjectRecord(
        id=_required_string(raw, "id"),
        object_type=_required_string(raw, "object_type"),
        properties=dict(properties),
    )


def _link_record(raw: object) -> OntologyLinkRecord:
    if not isinstance(raw, Mapping):
        raise ValueError("operating model link entries MUST be objects")
    properties = raw.get("properties", {})
    if not isinstance(properties, Mapping):
        raise ValueError("operating model link properties MUST be an object")
    return OntologyLinkRecord(
        link_type=_required_string(raw, "link_type"),
        from_id=_required_string(raw, "from_id"),
        to_id=_required_string(raw, "to_id"),
        properties=dict(properties),
    )


__all__ = [
    "JsonOperatingIntentSourceProvider",
    "JsonOperatingModelProvider",
    "JsonOperatingModelProviderConfig",
    "OperatingIntentSourceDocument",
    "OperatingIntentSourceProvenance",
    "operating_intent_source_document_from_mapping",
    "operating_model_snapshot_from_mapping",
]
