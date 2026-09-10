from __future__ import annotations

import re
from pathlib import Path

_WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "deploy-dev.yml"
).read_text(encoding="utf-8")


def test_observability_request_reconciles_state_then_targets_only_analyzer() -> None:
    assert "plan-observability-" in _WORKFLOW
    assignment = re.search(r"export TF_CLI_ARGS_plan='([^']+)'", _WORKFLOW)
    assert assignment is not None
    assert assignment.group(1).split() == [
        "-target=module.compute.azurerm_container_app_job.analyzer_tick[0]"
    ]
    assert "reconcile_rca_bootstrap_state.sh observability" in _WORKFLOW
    assert "mode=observability-analyzer" in _WORKFLOW
