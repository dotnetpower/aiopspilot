"""Static contracts for the governed framework shadow assessment workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.deployment.azure.export_wara_job_context import extract_wara_context

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = (ROOT / ".github/workflows/framework-assessment-shadow.yml").read_text(encoding="utf-8")


def _jobs(*, workload_ids: object = None) -> list[dict[str, object]]:
    return [
        {
            "properties": {
                "template": {
                    "containers": [
                        {
                            "command": [
                                "python",
                                "-m",
                                "fdai.delivery.wara_assessment_cli",
                            ],
                            "env": [
                                {
                                    "name": "FDAI_WARA_WORKLOAD_IDS_JSON",
                                    "value": json.dumps(
                                        ["workload-example"]
                                        if workload_ids is None
                                        else workload_ids
                                    ),
                                },
                                {
                                    "name": "FDAI_WARA_INVENTORY_FRESHNESS_SECONDS",
                                    "value": "86400",
                                },
                                {
                                    "name": "FDAI_WARA_DSN",
                                    "secretRef": "wara-dsn",
                                },
                            ],
                        }
                    ]
                }
            }
        }
    ]


def test_workflow_is_exact_revision_read_only_and_evidence_bounded() -> None:
    assert "runs-on: [self-hosted, fdai-deploy, fdai-deploy-candidate]" in WORKFLOW
    assert "environment: plan-only" in WORKFLOW
    assert "Verify required CI for exact revision" in WORKFLOW
    assert 'select(.name == "required")' in WORKFLOW
    assert "login-deploy-identity.sh" in WORKFLOW
    assert "fdai.delivery.framework_assessment_cli" in WORKFLOW
    assert "framework-assessment-receipt.json" in WORKFLOW
    assert "retention-days: 90" in WORKFLOW
    assert "terraform apply" not in WORKFLOW
    assert "az deployment" not in WORKFLOW


def test_exporter_selects_only_non_secret_scope_settings() -> None:
    context = extract_wara_context(_jobs())

    assert context == {
        "FDAI_WARA_INVENTORY_FRESHNESS_SECONDS": "86400",
        "FDAI_WARA_WORKLOAD_IDS_JSON": '["workload-example"]',
    }
    assert all("DSN" not in name for name in context)


@pytest.mark.parametrize("workload_ids", [[], ["one", "two"], [""], [1]])
def test_exporter_rejects_missing_or_ambiguous_workload_scope(
    workload_ids: object,
) -> None:
    with pytest.raises(ValueError, match="exactly one workload"):
        extract_wara_context(_jobs(workload_ids=workload_ids))
