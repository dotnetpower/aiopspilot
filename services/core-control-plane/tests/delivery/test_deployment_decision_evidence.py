"""Exact protected-deployment decision-evidence tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest
from fdai_service_contracts.decision_evidence_verification import (
    EvidenceVerificationProofKind,
)

_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "deployment" / "azure" / "deployment_decision_evidence.py"
_NOW = datetime(2026, 9, 8, 12, 30, tzinfo=UTC)
_COMMIT = "a" * 40
_PLAN_ID = "plan-123-1"
_PLAN_DIGEST = "b" * 64
_CONTEXT_DIGEST = "c" * 64
_RUN_ID = 123
_RUN_ATTEMPT = 1


@pytest.fixture(scope="module")
def verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("deployment_decision_evidence_script", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _evidence_dir(tmp_path: Path, *, status: str = "applied") -> Path:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    _write(
        evidence / "plan-metadata.json",
        {
            "schema_version": "fdai.deployment-plan.v1",
            "plan_id": _PLAN_ID,
            "plan_digest": _PLAN_DIGEST,
            "context_digest": _CONTEXT_DIGEST,
            "commit_sha": _COMMIT,
        },
    )
    _write(evidence / "preflight-evidence.json", {"blocks": False})
    _write(evidence / "azure-preflight-evidence.json", {"blocks": False})
    _write(
        evidence / "apply-claim.json",
        {
            "schema_version": "fdai.deployment-apply-claim.v1",
            "plan_id": _PLAN_ID,
            "plan_digest": _PLAN_DIGEST,
            "workflow_run_id": str(_RUN_ID),
            "workflow_run_attempt": str(_RUN_ATTEMPT),
        },
    )
    _write(
        evidence / "apply-receipt.json",
        {
            "schema_version": "fdai.deployment-apply-receipt.v1",
            "plan_id": _PLAN_ID,
            "plan_digest": _PLAN_DIGEST,
            "workflow_run_id": str(_RUN_ID),
            "workflow_run_attempt": str(_RUN_ATTEMPT),
            "applied_at": (_NOW - timedelta(minutes=5)).isoformat(),
            "status": status,
        },
    )
    (evidence / "decision-evidence-container-url.txt").write_text(
        "https://example.com/operational-history\n",
        encoding="utf-8",
    )
    return evidence


def _source_run() -> dict[str, object]:
    return {
        "id": _RUN_ID,
        "run_attempt": _RUN_ATTEMPT,
        "head_sha": _COMMIT,
        "path": ".github/workflows/deploy-dev.yml",
        "event": "workflow_dispatch",
        "status": "completed",
        "conclusion": "success",
    }


def test_builds_five_non_authorizing_proofs(
    verifier: ModuleType,
    tmp_path: Path,
) -> None:
    receipt, requirement, authentication, readback, container_url = (
        verifier.build_deployment_decision_evidence(
            evidence_dir=_evidence_dir(tmp_path),
            source_run=_source_run(),
            expected_commit_sha=_COMMIT,
            expected_run_id=_RUN_ID,
            expected_run_attempt=_RUN_ATTEMPT,
            evaluated_at=_NOW,
        )
    )

    assert receipt.execution_authority is False
    assert requirement.source_revision == _COMMIT
    assert authentication.kind is EvidenceVerificationProofKind.AUTHENTICATION
    assert len(readback) == 4
    assert all(proof.execution_authority is False for proof in (authentication, *readback))
    assert container_url == "https://example.com/operational-history"


def test_rejects_source_run_mismatch(verifier: ModuleType, tmp_path: Path) -> None:
    source_run = _source_run()
    source_run["head_sha"] = "f" * 40

    with pytest.raises(verifier.DeploymentDecisionEvidenceError, match="source deployment run"):
        verifier.build_deployment_decision_evidence(
            evidence_dir=_evidence_dir(tmp_path),
            source_run=source_run,
            expected_commit_sha=_COMMIT,
            expected_run_id=_RUN_ID,
            expected_run_attempt=_RUN_ATTEMPT,
            evaluated_at=_NOW,
        )


def test_rejects_non_applied_receipt(verifier: ModuleType, tmp_path: Path) -> None:
    with pytest.raises(verifier.DeploymentDecisionEvidenceError, match="do not agree"):
        verifier.build_deployment_decision_evidence(
            evidence_dir=_evidence_dir(tmp_path, status="failed"),
            source_run=_source_run(),
            expected_commit_sha=_COMMIT,
            expected_run_id=_RUN_ID,
            expected_run_attempt=_RUN_ATTEMPT,
            evaluated_at=_NOW,
        )


def test_rejects_stale_deployment_evidence(verifier: ModuleType, tmp_path: Path) -> None:
    with pytest.raises(verifier.DeploymentDecisionEvidenceError, match="freshness window"):
        verifier.build_deployment_decision_evidence(
            evidence_dir=_evidence_dir(tmp_path),
            source_run=_source_run(),
            expected_commit_sha=_COMMIT,
            expected_run_id=_RUN_ID,
            expected_run_attempt=_RUN_ATTEMPT,
            evaluated_at=_NOW + timedelta(hours=2),
        )
