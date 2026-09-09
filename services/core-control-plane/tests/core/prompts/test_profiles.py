"""Exact prompt-profile loading, selection, and budget tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fdai.core.prompts import (
    FileSystemPromptRegistry,
    PromptArtifactRef,
    PromptBudgetExceededError,
    PromptLayer,
    PromptProfile,
    PromptProfileMode,
    PromptRegistryError,
    compose_static_selection,
)

_ROOT = Path(__file__).resolve().parents[5]
_CATALOG = _ROOT / "rule-catalog"


def test_shipped_active_profiles_pin_exact_versions() -> None:
    registry = FileSystemPromptRegistry(_CATALOG)

    judgment = registry.resolve("semantic.judgment")
    frame = registry.resolve("semantic.query.frame")
    plan = registry.resolve("semantic.query.plan")

    assert judgment.profile is not None
    assert judgment.profile.mode is PromptProfileMode.ACTIVE
    assert (judgment.root.id, judgment.root.version) == ("semantic-judgment", 8)
    assert (frame.root.id, frame.root.version) == ("semantic-query-frame", 40)
    assert (plan.root.id, plan.root.version) == ("semantic-query-plan", 18)


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"id": "Bad ID"}, "profile id"),
        ({"version": True}, "profile version"),
        ({"capability_id": ""}, "capability_id"),
        ({"system_token_budget": 0}, "system_token_budget"),
        ({"request_token_budget": 1}, "request budget"),
        ({"reserved_output_tokens": 20_000}, "reserved output"),
        ({"promotion_evidence": ("",)}, "promotion evidence"),
        ({"provenance_source": ""}, "provenance source"),
    ),
)
def test_prompt_profile_rejects_invalid_direct_values(
    overrides: dict[str, object],
    message: str,
) -> None:
    values: dict[str, object] = {
        "id": "test.profile",
        "version": 1,
        "capability_id": "test.capability",
        "mode": PromptProfileMode.ACTIVE,
        "root": PromptArtifactRef("root", 1, PromptLayer.BASE),
        "packs": (),
        "system_token_budget": 128,
        "request_token_budget": 4096,
        "reserved_output_tokens": 512,
        "promotion_evidence": ("test",),
        "provenance_source": "test",
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        PromptProfile(**values)  # type: ignore[arg-type]


def test_shadow_profile_requires_explicit_id_and_preserves_active_selection() -> None:
    registry = FileSystemPromptRegistry(_CATALOG)

    active = registry.resolve("semantic.query.frame")
    treatment = registry.resolve(
        "semantic.query.frame",
        profile_id="shadow.semantic-query-frame-compact",
    )

    assert active.profile is not None
    assert treatment.profile is not None
    assert active.profile.mode is PromptProfileMode.ACTIVE
    assert treatment.profile.mode is PromptProfileMode.SHADOW
    assert active.root.id == "semantic-query-frame"
    assert treatment.root.id == "semantic-query-frame-common"


def test_profile_cannot_bind_a_different_capability() -> None:
    registry = FileSystemPromptRegistry(_CATALOG)

    with pytest.raises(LookupError, match="does not bind capability"):
        registry.resolve(
            "semantic.query.plan",
            profile_id="shadow.semantic-query-frame-compact",
        )


def test_profile_catalog_never_falls_back_to_highest_unprofiled_artifact() -> None:
    registry = FileSystemPromptRegistry(_CATALOG)

    with pytest.raises(LookupError, match="no active prompt profile"):
        registry.resolve("t2.critic")


def test_profile_catalog_rejects_missing_exact_artifact(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    shutil.copytree(_CATALOG / "prompts", catalog / "prompts")
    (catalog / "prompts" / "base" / "semantic-query-frame.v40.yaml").unlink()

    with pytest.raises(PromptRegistryError) as excinfo:
        FileSystemPromptRegistry(catalog)

    assert any("unknown artifact" in issue.message for issue in excinfo.value.issues)


def test_profile_catalog_rejects_invalid_profile_schema(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    shutil.copytree(_CATALOG / "prompts", catalog / "prompts")
    schema_path = catalog / "prompts" / "profiles" / "schema" / "prompt-profile.schema.json"
    schema_path.write_text('{"type":"not-a-json-schema-type"}')

    with pytest.raises(PromptRegistryError) as excinfo:
        FileSystemPromptRegistry(catalog)

    assert any("invalid prompt profile schema" in issue.message for issue in excinfo.value.issues)


def test_static_composition_enforces_profile_system_budget(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    shutil.copytree(_CATALOG / "prompts", catalog / "prompts")
    profile_path = catalog / "prompts" / "profiles" / "catalog.yaml"
    profile_path.write_text(
        profile_path.read_text().replace(
            "system_token_budget: 12288\n    request_token_budget: 196608",
            "system_token_budget: 1\n    request_token_budget: 196608",
            1,
        )
    )
    registry = FileSystemPromptRegistry(catalog)

    with pytest.raises(PromptBudgetExceededError, match="exceeds system token budget"):
        compose_static_selection(registry.resolve("semantic.query.frame"))
