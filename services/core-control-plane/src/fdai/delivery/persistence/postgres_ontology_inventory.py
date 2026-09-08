"""Inventory state validation helpers for PostgreSQL ontology persistence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def inventory_state_base_available(
    manifest: Mapping[str, Any],
    status: Mapping[str, Any],
    *,
    expected_generation: str,
) -> bool:
    if manifest.get("generation") != expected_generation or manifest.get("complete") is not True:
        return False
    return (
        status.get("generation") == expected_generation
        and status.get("status") == "available"
        and status.get("complete") is True
    ) or unavailable_inventory_projection_status(status)


def unavailable_inventory_projection_status(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("status") == "unavailable"
        and value.get("complete") is False
    )


def inventory_manifest_object_ids(manifest: Mapping[str, Any]) -> frozenset[str]:
    content = manifest.get("object_content")
    if not isinstance(content, list):
        raise ValueError("inventory ontology manifest object ownership is unavailable")
    identifiers: list[str] = []
    for item in content:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
            raise ValueError("inventory ontology manifest object ownership is malformed")
        identifiers.append(str(item["id"]))
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("inventory ontology manifest object ownership is duplicated")
    return frozenset(identifiers)


__all__ = [
    "inventory_manifest_object_ids",
    "inventory_state_base_available",
    "unavailable_inventory_projection_status",
]
