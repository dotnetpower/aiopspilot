from __future__ import annotations

from pathlib import Path

_WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "deploy-dev.yml"
).read_text(encoding="utf-8")


def test_observability_request_targets_only_the_analyzer_job() -> None:
    assert "plan-observability-" in _WORKFLOW
    assert (
        "TF_CLI_ARGS_plan='-target=module.compute.azurerm_container_app_job.analyzer_tick[0]'"
        in _WORKFLOW
    )
    assert "mode=observability-analyzer" in _WORKFLOW
