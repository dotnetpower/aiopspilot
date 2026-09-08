"""Protected deployment contract for the provider-schema Job."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW = _ROOT / ".github/workflows/deploy-dev.yml"


def test_dev_operations_plan_includes_provider_schema_job() -> None:
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    target_expression = workflow[workflow.index("TF_CLI_ARGS_plan:") :]
    target_expression = target_expression[: target_expression.index("\n")]
    dev_targets = target_expression.split("inputs.deploy_dev_operations_gateway && '", maxsplit=1)[
        1
    ].split("' || ''", maxsplit=1)[0]

    assert "inputs.deploy_dev_operations_gateway" in target_expression
    assert "-target=module.resource_group.azurerm_resource_group.primary" in dev_targets
    assert (
        "-target=module.compute.azurerm_container_app_job.provider_schema[0]" in target_expression
    )
