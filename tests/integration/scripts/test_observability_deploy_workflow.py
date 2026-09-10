from __future__ import annotations

import re
from pathlib import Path

_WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "deploy-dev.yml"
).read_text(encoding="utf-8")


def test_observability_request_includes_only_the_required_move_closure() -> None:
    assert "plan-observability-" in _WORKFLOW
    assignment = re.search(r"export TF_CLI_ARGS_plan='([^']+)'", _WORKFLOW)
    assert assignment is not None
    assert frozenset(assignment.group(1).split()) == frozenset(
        {
            "-target=module.compute.azurerm_container_app_job.analyzer_tick[0]",
            "-target=module.compute.azurerm_container_app_job.oob",
            "-target=module.compute.azurerm_container_app_job.rule_watcher",
        }
    )
    assert "mode=observability-analyzer" in _WORKFLOW
