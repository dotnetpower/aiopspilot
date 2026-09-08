"""Protected governed decision-evidence workflow contract tests."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW = (_ROOT / ".github/workflows/decision-evidence-admission.yml").read_text(
    encoding="utf-8"
)
_DEPLOY = (_ROOT / ".github/workflows/deploy-dev.yml").read_text(encoding="utf-8")


def test_workflow_is_exact_revision_and_source_run_bound() -> None:
    assert "workflow-path: .github/workflows/decision-evidence-admission.yml" in _WORKFLOW
    assert 'git merge-base --is-ancestor "$TARGET_COMMIT_SHA" origin/main' in _WORKFLOW
    assert '"$(git rev-parse HEAD)" == "$TARGET_COMMIT_SHA"' in _WORKFLOW
    assert "actions/runs/$SOURCE_RUN_ID/attempts/$SOURCE_RUN_ATTEMPT" in _WORKFLOW
    assert "governed-deployment-evidence-candidate-${SOURCE_RUN_ID}-${SOURCE_RUN_ATTEMPT}" in (
        _WORKFLOW
    )


def test_workflow_uses_managed_identity_and_immutable_blob_writes() -> None:
    assert "az login --identity --client-id" in _WORKFLOW
    assert "verify-azure-context.sh" in _WORKFLOW
    assert "--overwrite false" in _WORKFLOW
    assert "decision evidence immutable record collision" in _WORKFLOW
    assert '--metadata "fdai-sha256=$digest"' in _WORKFLOW
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
    assert "retention-days: 90" in _WORKFLOW
    assert "Execution authority: `false`" in _WORKFLOW
    assert "Promotion authority: `false`" in _WORKFLOW


def test_deploy_workflow_emits_fixed_candidate_artifact() -> None:
    assert "Prepare governed decision evidence candidate" in _DEPLOY
    assert "governed-deployment-evidence-candidate-${{ github.run_id }}-" in _DEPLOY
    assert "terraform output -raw operational_history_container_url" in _DEPLOY
    for name in (
        "plan-metadata.json",
        "preflight-evidence.json",
        "azure-preflight-evidence.json",
        "apply-claim.json",
        "apply-receipt.json",
        "decision-evidence-container-url.txt",
    ):
        assert name in _DEPLOY
