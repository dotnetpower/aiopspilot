"""Completeness and safety gates for generated WAF and CAF assessment catalogs."""

from __future__ import annotations

from pathlib import Path

import yaml
from fdai.rule_catalog.schema.framework_assessment import (
    FrameworkCrosswalkKind,
    FrameworkProcessPhase,
    load_framework_assessment_catalog,
)

ROOT = Path(__file__).resolve().parents[4]
GENERATED = ROOT / "rule-catalog/framework-assessments/generated"


def _catalog(name: str):
    return load_framework_assessment_catalog(GENERATED / f"{name}.json")


def test_waf_catalog_covers_all_controls_and_evidence_references() -> None:
    catalog = _catalog("azure-waf")

    assert len(catalog.controls) == 59
    assert sum(len(control.evidence) for control in catalog.controls) == 186
    assert all(
        item.authoritative_producer is not None or item.blocked_dependency is not None
        for control in catalog.controls
        for item in control.evidence
    )
    assert all(control.owner_slot for control in catalog.controls)
    assert {
        reference.target_kind for control in catalog.controls for reference in control.crosswalk
    } >= {
        FrameworkCrosswalkKind.BEST_PRACTICE,
        FrameworkCrosswalkKind.RULE,
        FrameworkCrosswalkKind.MANUAL_EVIDENCE,
    }


def test_caf_catalog_covers_all_areas_and_process_evidence() -> None:
    catalog = _catalog("azure-caf")

    assert len(catalog.controls) == 15
    by_id = {control.control_id: control for control in catalog.controls}
    assert set(by_id) >= {"strategy", "plan", "adopt", "ready", "govern", "secure", "manage"}
    for control_id in ("strategy", "plan", "adopt"):
        assert {item.process_phase for item in by_id[control_id].evidence} >= {
            FrameworkProcessPhase.PROCEDURE,
            FrameworkProcessPhase.EXECUTION,
        }
    assert all(
        item.authoritative_producer is not None or item.blocked_dependency is not None
        for control in catalog.controls
        for item in control.evidence
    )
    assert all(control.crosswalk for control in catalog.controls)


def test_caf_crosswalk_targets_resolve_exact_catalog_records() -> None:
    caf = _catalog("azure-caf")
    waf = _catalog("azure-waf")
    mcsb_raw = yaml.safe_load((ROOT / "rule-catalog/compliance/mcsb/v1/controls.yaml").read_text())
    policy_raw = yaml.safe_load(
        (ROOT / "rule-catalog/compliance/mcsb/v1/crosswalk.yaml").read_text()
    )
    mcsb_ids = {str(item["id"]) for item in mcsb_raw["controls"]}
    policy_ids = {str(item["profile_id"]) for item in policy_raw["policy_profiles"]}
    waf_ids = {item.control_id for item in waf.controls}

    for control in caf.controls:
        evidence_refs = {item.source_ref for item in control.evidence}
        for reference in control.crosswalk:
            if reference.target_kind is FrameworkCrosswalkKind.WAF:
                assert reference.target_ref in waf_ids
            elif reference.target_kind is FrameworkCrosswalkKind.MCSB:
                assert reference.target_ref in mcsb_ids
            elif reference.target_kind is FrameworkCrosswalkKind.AZURE_POLICY:
                assert reference.target_ref in policy_ids
            elif reference.target_kind in {
                FrameworkCrosswalkKind.OBSERVATION,
                FrameworkCrosswalkKind.MANUAL_EVIDENCE,
            }:
                assert reference.target_ref in evidence_refs


def test_generated_catalogs_are_content_addressed() -> None:
    first = _catalog("azure-waf")
    second = _catalog("azure-waf")

    assert first == second
    assert first.catalog_digest.startswith("sha256:")
