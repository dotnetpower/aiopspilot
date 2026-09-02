"""Runtime startup binding for the deployment-owned six-type operating-intent source.

Distinct from the generic ``FDAI_OPERATING_MODEL_PATH`` mechanism in
``operating_model.py`` (which may legitimately carry only ``Resource`` instances),
this binding is specifically for ``ServiceObjective``, ``RecoveryObjective``,
``CostObjective``, ``ArchitectureConstraint``, ``Ownership``, and ``ChangeWindow``.
It requires every candidate source to carry the operator-pinned exact revision,
self-consistent provenance, and content digest, and it fails closed - preserving
whatever operating-intent graph is already durably owned - on a missing, duplicate,
stale, or cross-release attempt rather than projecting a partial or wrong graph.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from fdai.core.operational_context import (
    OperatingIntentSourceBinding,
    OperatingIntentSourceError,
    OperatingModelProjectionResult,
    OperatingModelProjector,
    validate_operating_intent_snapshot,
)
from fdai.delivery.operating_model import (
    JsonOperatingIntentSourceProvider,
    JsonOperatingModelProviderConfig,
)
from fdai.runtime.operating_model import project_operating_model_snapshot
from fdai.shared.contracts.models import OntologyLinkType, OntologyObjectType
from fdai.shared.providers.ontology_instance import OntologyInstanceStore
from fdai.shared.providers.operating_model import OperatingModelSnapshot
from fdai.shared.providers.state_store import StateStore

OPERATING_INTENT_SOURCE_STATUS_KEY = "operating-intent-source:status"
_OPERATING_INTENT_SOURCE_MANIFEST_KEY = "operating-intent-source:manifest"


async def project_operating_intent_source_from_env(
    *,
    store: OntologyInstanceStore | None,
    object_types: Sequence[OntologyObjectType],
    link_types: Sequence[OntologyLinkType],
    status_store: StateStore | None = None,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> OperatingModelProjectionResult | None:
    """Load, validate, and project the pinned six-type operating-intent source.

    Returns ``None`` when the source is unconfigured (clearing any previously owned
    instances) or when the candidate source fails a fail-closed check; in the latter
    case the failure is recorded durably as ``rejected`` with its reason and the
    already-projected graph is left untouched. Raises only on a genuine
    startup/config defect (missing required binding env vars, an unreadable or
    malformed file) - the same convention ``project_operating_model_from_env`` uses
    for its own required-store/path checks.
    """

    values = env if env is not None else os.environ
    raw_path = values.get("FDAI_OPERATING_INTENT_SOURCE_PATH", "").strip()
    if not raw_path:
        if store is not None:
            prior_manifest = (
                await status_store.read_state(_OPERATING_INTENT_SOURCE_MANIFEST_KEY)
                if status_store is not None
                else None
            )
            previous_object_ids, previous_link_keys = _decode_prior_manifest(prior_manifest)
            if previous_object_ids or previous_link_keys:
                await OperatingModelProjector(
                    store=store,
                    object_types=object_types,
                    link_types=link_types,
                ).project(
                    OperatingModelSnapshot(source_revision="unconfigured", objects=(), links=()),
                    previous_object_ids=previous_object_ids,
                    previous_link_keys=previous_link_keys,
                )
        if status_store is not None:
            await status_store.write_state(
                _OPERATING_INTENT_SOURCE_MANIFEST_KEY,
                {
                    "schema_version": "1.0.0",
                    "status": "unconfigured",
                    "source_revision": "unconfigured",
                    "object_ids": [],
                    "link_keys": [],
                },
            )
            await status_store.write_state(
                OPERATING_INTENT_SOURCE_STATUS_KEY,
                {"schema_version": "1.0.0", "status": "unconfigured"},
            )
        return None
    if store is None:
        raise RuntimeError("FDAI_OPERATING_INTENT_SOURCE_PATH requires an ontology instance store")
    binding = _binding_from_env(values)
    raw_max_bytes = values.get("FDAI_OPERATING_INTENT_SOURCE_MAX_BYTES", "").strip()
    try:
        max_bytes = int(raw_max_bytes) if raw_max_bytes else 16 * 1024 * 1024
    except ValueError as exc:
        raise RuntimeError("FDAI_OPERATING_INTENT_SOURCE_MAX_BYTES MUST be an integer") from exc
    provider = JsonOperatingIntentSourceProvider(
        config=JsonOperatingModelProviderConfig(path=Path(raw_path), max_bytes=max_bytes)
    )
    document = await provider.load()
    effective_now = now if now is not None else datetime.now(UTC)
    try:
        validate_operating_intent_snapshot(
            document.snapshot,
            provenance=document.provenance,
            binding=binding,
            now=effective_now,
        )
    except OperatingIntentSourceError as exc:
        if status_store is not None:
            await status_store.write_state(
                OPERATING_INTENT_SOURCE_STATUS_KEY,
                {
                    "schema_version": "1.0.0",
                    "status": "rejected",
                    "reason": str(exc),
                },
            )
        return None
    return await project_operating_model_snapshot(
        snapshot=document.snapshot,
        store=store,
        object_types=object_types,
        link_types=link_types,
        status_store=status_store,
        snapshot_digest=binding.expected_sha256,
        manifest_key=_OPERATING_INTENT_SOURCE_MANIFEST_KEY,
        status_key=OPERATING_INTENT_SOURCE_STATUS_KEY,
    )


def _binding_from_env(values: Mapping[str, str]) -> OperatingIntentSourceBinding:
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


def _decode_prior_manifest(
    raw: Mapping[str, object] | None,
) -> tuple[tuple[str, ...], tuple[tuple[str, str, str], ...]]:
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
    "OPERATING_INTENT_SOURCE_STATUS_KEY",
    "project_operating_intent_source_from_env",
]
