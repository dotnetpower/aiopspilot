"""Infrastructure contract for production decision-evidence admission."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SERVICE = _ROOT / "infra/services/core-control-plane"
_ROOT_VARIABLES = (_SERVICE / "variables.tf").read_text(encoding="utf-8")
_ROOT_MAIN = (_SERVICE / "main.tf").read_text(encoding="utf-8")
_MODULE_VARIABLES = (_SERVICE / "modules/core-control-plane/variables.tf").read_text(
    encoding="utf-8"
)
_MODULE_MAIN = (_SERVICE / "modules/core-control-plane/main.tf").read_text(encoding="utf-8")
_SERVICE_DEPLOY = (_ROOT / ".github/workflows/service-deploy.yml").read_text(encoding="utf-8")


def test_core_service_exposes_optional_private_container_binding() -> None:
    assert 'variable "decision_evidence_container_url"' in _ROOT_VARIABLES
    assert "must be empty or one HTTPS Blob container URL" in _ROOT_VARIABLES
    assert "decision_evidence_container_url     = var.decision_evidence_container_url" in (
        _ROOT_MAIN
    )
    assert 'variable "decision_evidence_container_url"' in _MODULE_VARIABLES
    assert '"FDAI_DECISION_EVIDENCE_CONTAINER_URL"' in _MODULE_MAIN


def test_service_deploy_uses_authoritative_platform_output() -> None:
    assert 'terraform -chdir="$TRUSTED_CONTROLS/infra"' in _SERVICE_DEPLOY
    assert "output -raw operational_history_container_url" in _SERVICE_DEPLOY
    assert 'DECISION_EVIDENCE_CONTAINER_URL="$decision_evidence_container_url"' in (_SERVICE_DEPLOY)
