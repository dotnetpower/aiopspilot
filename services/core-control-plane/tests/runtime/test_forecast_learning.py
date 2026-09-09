from __future__ import annotations

import json
from pathlib import Path

import pytest
from fdai.core.detection.governance_policy import load_detection_governance_policy
from fdai.runtime.forecast_learning import (
    build_forecast_learning_runtime,
    parse_forecast_targets,
)
from fdai.shared.providers.metric import StaticMetricProvider

_REPO_ROOT = Path(__file__).resolve().parents[4]
_POLICY_PATH = _REPO_ROOT / "config" / "detection-governance-policy.json"


def _target(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "target_kind": "capacity",
        "detector_id": "capacity-linear",
        "detector_version": "1.0.0",
        "scorer_version": "1.0.0",
        "access_scope_digest": "a" * 64,
        "resource_ref": "resource-1",
        "metric": "capacity_percent",
        "threshold": 90.0,
        "horizon_seconds": 86_400,
        "lookback_seconds": 604_800,
        "telemetry_grace_seconds": 300,
        "min_samples": 5,
        "min_r_squared": 0.5,
        "confidence_level": "0.90",
    }
    value.update(overrides)
    return value


def test_forecast_targets_must_match_the_governed_policy() -> None:
    policy = load_detection_governance_policy(_POLICY_PATH)

    targets = parse_forecast_targets(
        json.dumps([_target()]),
        governance_policy=policy,
    )

    assert len(targets) == 1
    assert targets[0].horizon_seconds == 86_400


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"target_kind": None}, "target_kind"),
        ({"horizon_seconds": 3_600}, "horizon_seconds"),
        ({"min_samples": 4}, "min_samples"),
        ({"min_r_squared": 0.49}, "min_r_squared"),
        ({"confidence_level": "0.95"}, "confidence_level"),
    ),
)
def test_forecast_targets_cannot_weaken_or_bypass_policy(
    overrides: dict[str, object],
    message: str,
) -> None:
    policy = load_detection_governance_policy(_POLICY_PATH)

    with pytest.raises(ValueError, match=message):
        parse_forecast_targets(
            json.dumps([_target(**overrides)]),
            governance_policy=policy,
        )


def test_startup_loads_policy_even_when_forecast_targets_are_disabled(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unreadable detection governance policy"):
        build_forecast_learning_runtime(
            dsn=None,
            targets_json=None,
            metric_provider=StaticMetricProvider([]),
            governance_policy_path=tmp_path / "missing.json",
        )
