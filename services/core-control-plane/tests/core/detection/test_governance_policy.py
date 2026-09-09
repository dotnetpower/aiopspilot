from __future__ import annotations

import json
from pathlib import Path

import pytest
from fdai.core.detection.governance_policy import (
    AnomalyMethod,
    DetectionGovernancePolicyError,
    ForecastModelFamily,
    load_detection_governance_policy,
)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_POLICY_PATH = _REPO_ROOT / "config" / "detection-governance-policy.json"


def _policy() -> dict[str, object]:
    return json.loads(_POLICY_PATH.read_text(encoding="utf-8"))


def _write_policy(tmp_path: Path, value: dict[str, object]) -> Path:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_repository_policy_resolves_every_open_design_decision() -> None:
    policy = load_detection_governance_policy(_POLICY_PATH)

    assert policy.signal_class("reliability.stationary").anomaly_method is AnomalyMethod.Z_SCORE
    assert (
        policy.signal_class("reliability.seasonal").anomaly_method is AnomalyMethod.SEASONAL_Z_SCORE
    )
    assert policy.forecast_target("capacity").model_family is ForecastModelFamily.LINEAR_TREND
    assert policy.forecast_target("expiry").horizon_seconds == 2_592_000
    assert policy.correlation.exact_keys == ("correlation_id", "resource_ref")
    assert policy.correlation.t1_similarity_floor == 0.85
    assert policy.forecast_promotion.min_scorable_episodes == 30
    assert policy.forecast_promotion.max_policy_escapes == 0
    assert policy.change_window.behavior == "annotate_and_hold_incident"
    assert len(policy.content_digest) == 64


def test_policy_rejects_unknown_fields(tmp_path: Path) -> None:
    raw = _policy()
    raw["unexpected"] = True

    with pytest.raises(DetectionGovernancePolicyError, match="fields"):
        load_detection_governance_policy(_write_policy(tmp_path, raw))


def test_policy_rejects_duplicate_signal_classes(tmp_path: Path) -> None:
    raw = _policy()
    signal_classes = raw["signal_classes"]
    assert isinstance(signal_classes, list)
    signal_classes.append(dict(signal_classes[0]))

    with pytest.raises(DetectionGovernancePolicyError, match="signal class"):
        load_detection_governance_policy(_write_policy(tmp_path, raw))


def test_policy_rejects_seasonal_method_without_phase(tmp_path: Path) -> None:
    raw = _policy()
    signal_classes = raw["signal_classes"]
    assert isinstance(signal_classes, list)
    signal_classes[0]["seasonal_phase"] = None

    with pytest.raises(DetectionGovernancePolicyError, match="requires seasonal_phase"):
        load_detection_governance_policy(_write_policy(tmp_path, raw))


def test_policy_rejects_reversed_interval_coverage(tmp_path: Path) -> None:
    raw = _policy()
    promotion = raw["forecast_promotion"]
    assert isinstance(promotion, dict)
    promotion["min_interval_coverage"] = 0.99

    with pytest.raises(DetectionGovernancePolicyError, match="reversed"):
        load_detection_governance_policy(_write_policy(tmp_path, raw))


def test_policy_rejects_confidence_levels_the_forecast_band_cannot_evaluate(
    tmp_path: Path,
) -> None:
    raw = _policy()
    targets = raw["forecast_targets"]
    assert isinstance(targets, list)
    targets[0]["confidence_level"] = "0.85"

    with pytest.raises(DetectionGovernancePolicyError, match="confidence_level"):
        load_detection_governance_policy(_write_policy(tmp_path, raw))
