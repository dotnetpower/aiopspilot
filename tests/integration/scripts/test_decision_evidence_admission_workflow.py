"""Protected governed decision-evidence workflow contract tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW = (_ROOT / ".github/workflows/decision-evidence-admission.yml").read_text(
    encoding="utf-8"
)
_DEPLOY = (_ROOT / ".github/workflows/deploy-dev.yml").read_text(encoding="utf-8")


def test_workflow_is_exact_revision_and_source_run_bound() -> None:
    assert "workflow-path: .github/workflows/decision-evidence-admission.yml" in _WORKFLOW
    assert 'git merge-base --is-ancestor "$TARGET_COMMIT_SHA" origin/main' in _WORKFLOW
    assert 'git rev-list --first-parent origin/main | grep -Fqx "$TARGET_COMMIT_SHA"' in (_WORKFLOW)
    assert '"$(git rev-parse HEAD)" == "$TARGET_COMMIT_SHA"' in _WORKFLOW
    assert "actions/runs/$SOURCE_RUN_ID/attempts/$SOURCE_RUN_ATTEMPT" in _WORKFLOW
    assert '[[ "$PLAN_ID" =~ ^plan-[1-9][0-9]*-[1-9][0-9]*$ ]]' in _WORKFLOW
    assert "deployment-apply-receipt-${PLAN_ID}" in _WORKFLOW
    assert "--policy config/decision-evidence-deployment-policy.json" in _WORKFLOW


def test_workflow_uses_managed_identity_and_immutable_blob_writes() -> None:
    assert "az login --identity --client-id" in _WORKFLOW
    assert "verify-azure-context.sh" in _WORKFLOW
    assert "--overwrite false" in _WORKFLOW
    assert "decision evidence immutable record collision" in _WORKFLOW
    assert "decision evidence immutable metadata collision" in _WORKFLOW
    assert "--query 'metadata.fdaisha256' -o tsv" in _WORKFLOW
    assert '--metadata "fdaisha256=$digest"' in _WORKFLOW
    assert '"decision-evidence/v1/admissions/${lookup_digest}.json" stable-lookup' in (_WORKFLOW)
    assert "datetime.now(UTC) <= valid_until" in _WORKFLOW


def test_retention_shell_block_is_valid_bash() -> None:
    workflow = yaml.safe_load(_WORKFLOW)
    steps = workflow["jobs"]["verify-retain-attest"]["steps"]
    step = next(
        item
        for item in steps
        if item.get("name") == "Retain attested immutable decision evidence records"
    )

    result = subprocess.run(
        ["/bin/bash", "-n"],
        input=step["run"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "secrets." not in _WORKFLOW


def test_workflow_retains_all_proof_layers_and_attests_record() -> None:
    for path in (
        "decision-evidence/v1/authentication/",
        "decision-evidence/v1/readback/",
        "decision-evidence/v1/requirements/",
        "decision-evidence/v1/bundles/",
        "decision-evidence/v1/admissions/",
    ):
        assert path in _WORKFLOW
    assert "actions/attest@" in _WORKFLOW
    assert (
        "subject-path: ${{ runner.temp }}/decision-evidence-inputs/admission-record.json"
        in _WORKFLOW
    )
    assert _WORKFLOW.index("Attest governed decision evidence") < _WORKFLOW.index(
        "Retain attested immutable decision evidence records"
    )
    assert "retention-days: 90" in _WORKFLOW
    assert "Execution authority: `false`" in _WORKFLOW
    assert "Promotion authority: `false`" in _WORKFLOW


def test_deploy_workflow_emits_fixed_candidate_artifact() -> None:
    assert 'candidate="$RUNNER_TEMP/deployment-apply-artifact"' in _DEPLOY
    assert "name: deployment-apply-receipt-${{ inputs.plan_id }}" in _DEPLOY
    assert "terraform output -raw decision_evidence_container_url" in _DEPLOY
    assert "retention-days: 90" in _DEPLOY
    for name in (
        "plan-metadata.json",
        "preflight-evidence.json",
        "azure-preflight-evidence.json",
        "apply-claim.json",
        "apply-receipt.json",
    ):
        assert name in _DEPLOY
