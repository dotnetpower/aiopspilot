"""Exact prompt profile selection and content-free comparison tests."""

from __future__ import annotations

from pathlib import Path

from fdai.core.prompts import FileSystemPromptRegistry, compare_prompt_profiles

_CATALOG = Path(__file__).resolve().parents[5] / "rule-catalog"


def test_compact_semantic_profiles_reduce_static_prompt_tokens() -> None:
    registry = FileSystemPromptRegistry(_CATALOG)
    treatments = {
        "semantic.judgment": "shadow.semantic-judgment-compact",
        "semantic.query.frame": "shadow.semantic-query-frame-compact",
        "semantic.query.plan": "shadow.semantic-query-plan-compact",
    }

    comparisons = {
        capability: compare_prompt_profiles(
            registry,
            capability_id=capability,
            treatment_profile_id=profile_id,
        )
        for capability, profile_id in treatments.items()
    }

    assert comparisons["semantic.judgment"].token_reduction_rate > 0.5
    assert comparisons["semantic.query.frame"].token_reduction_rate > 0.9
    assert comparisons["semantic.query.plan"].token_reduction_rate > 0.9
    assert all(
        comparison.active_profile_digest != comparison.treatment_profile_digest
        for comparison in comparisons.values()
    )
