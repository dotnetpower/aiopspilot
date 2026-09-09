"""Contract tests for the generated semantic-intent coverage inventory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from scripts.automation.build_semantic_intent_coverage import _ratio, build_inventory

_ROOT = Path(__file__).resolve().parents[3]
_ARTIFACT = _ROOT / "eval/golden-dataset/semantic-intent-coverage.json"


def _artifact() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(_ARTIFACT.read_text(encoding="utf-8")),
    )


def test_semantic_intent_coverage_artifact_matches_authoritative_sources() -> None:
    assert _artifact() == build_inventory(_ROOT)


def test_semantic_intent_inventory_exposes_complete_topic_denominators() -> None:
    payload = _artifact()
    topics = payload["topic_inventory"]

    assert len(topics["operating_domains"]) == 4
    assert len(topics["question_bank_domains"]) == 7
    assert len(topics["golden_categories"]) == 12
    assert len(topics["pantheon_question_domains"]) == 47
    assert len(topics["ontology_query_functions"]) == 36
    assert len({item["agent"] for item in topics["pantheon_question_domains"]}) == 15
    assert all(item["coverage_state"] == "unmapped" for item in topics["pantheon_question_domains"])
    functions = {item["topic_id"]: item for item in topics["ontology_query_functions"]}
    assert functions["query.resource_health_inventory"]["intent_contract_case_count"] == 0
    assert functions["query.resource_current_state"]["intent_contract_case_count"] > 0
    assert payload["coverage_metrics"]["ontology_query_function_any_contract_coverage"] == {
        "covered": 12,
        "total": 36,
        "rate": 1 / 3,
    }


def test_semantic_intent_metrics_fail_closed_on_unsupported_slices() -> None:
    payload = _artifact()
    metrics = [metric for group in payload["metric_contract"].values() for metric in group]
    by_name = {metric["name"]: metric for metric in metrics}

    assert len(by_name) == len(metrics)
    assert len(metrics) == 47
    assert payload["scoring_policy"]["empty_denominator"].startswith("not_scored")
    assert set(payload["hard_zero_metrics"]) <= set(by_name)
    assert all(by_name[name]["promotion_target"] == 0 for name in payload["hard_zero_metrics"])
    assert payload["coverage_metrics"]["pantheon_domain_semantic_contract_coverage"] == {
        "covered": 0,
        "total": 47,
        "rate": 0.0,
    }
    assert _ratio(0, 0) == {"covered": 0, "total": 0, "rate": None}
