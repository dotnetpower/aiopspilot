"""Deterministic pytest shard assignment contract."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.quality.ci.pytest_shard import _assign_shards, _load_duration_weights
from scripts.quality.ci.resolve_test_scope import classify_paths


def test_shard_assignment_is_stable_balanced_and_bounded() -> None:
    weights = {
        Path("tests/heavy.py"): 8,
        Path("tests/medium.py"): 5,
        Path("tests/light-a.py"): 3,
        Path("tests/light-b.py"): 2,
    }

    assignments = _assign_shards(weights, 3)

    assert assignments == _assign_shards(dict(reversed(tuple(weights.items()))), 3)
    assert set(assignments) == set(weights)
    assert set(assignments.values()) <= {0, 1, 2}
    loads = [
        sum(weight for path, weight in weights.items() if assignments[path] == shard)
        for shard in range(3)
    ]
    assert max(loads) - min(loads) <= max(weights.values())


@pytest.mark.parametrize(
    ("weights", "count", "message"),
    [
        ({Path("tests/test_one.py"): 1}, 0, "count must be >= 1"),
        (
            {Path("tests/test_one.py"): 0},
            1,
            "file weights must be positive finite numbers",
        ),
    ],
)
def test_shard_assignment_rejects_invalid_weights(
    weights: dict[Path, int],
    count: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _assign_shards(weights, count)


def test_duration_weights_are_versioned_and_validate_paths(tmp_path: Path) -> None:
    manifest = tmp_path / "durations.json"
    manifest.write_text(
        """
{
  "schema_version": 1,
  "default_seconds_per_test": 0.01,
  "files": {
    "tests/test_fast.py": 0.5,
    "tests/test_slow.py": 12.25
  }
}
""".strip(),
        encoding="utf-8",
    )

    default, weights = _load_duration_weights(manifest)

    assert default == 0.01
    assert weights == {
        Path("tests/test_fast.py"): 0.5,
        Path("tests/test_slow.py"): 12.25,
    }

    manifest.write_text(
        '{"schema_version":1,"default_seconds_per_test":0.01,"files":{"../outside.py":1}}',
        encoding="utf-8",
    )
    with pytest.raises(pytest.UsageError, match="invalid pytest shard duration path"):
        _load_duration_weights(manifest)


def test_change_scope_classification_skips_expensive_python_for_docs_and_console() -> None:
    assert classify_paths(["docs/roadmap/architecture/project-structure.md"]) == (
        False,
        True,
        False,
    )
    assert classify_paths(["console/src/app.tsx"]) == (False, False, False)
    assert classify_paths(["services/core-control-plane/src/fdai/core/risk_gate/gate.py"]) == (
        True,
        False,
        False,
    )
    assert classify_paths(["alembic/versions/revision.py"]) == (True, False, False)
    assert classify_paths(["config/rbac-groups.yaml"]) == (True, False, False)
    assert classify_paths(["tools/seed_p1_rules.py"]) == (True, False, False)
    assert classify_paths(["extensions/code-assurance/assets/skill.json"]) == (
        True,
        False,
        False,
    )
    assert classify_paths(["infra/scenario-lab/main.tf"]) == (False, False, True)
    assert classify_paths(
        ["services/core-control-plane/tests/core/risk_gate/test_gate.py", "README.md"]
    ) == (True, True, False)
