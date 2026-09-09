"""Tests for the allowlisted Manual Studio deployment artifact."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PATH = _ROOT / "scripts" / "deployment" / "azure" / "build_manual_studio_artifact.py"
_PUBLISHER_PATH = _ROOT / "scripts" / "deployment" / "azure" / "publish-console.sh"
_WORKFLOW_PATH = _ROOT / ".github" / "workflows" / "publish-console.yml"
_SPEC = importlib.util.spec_from_file_location("build_manual_studio_artifact", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_build_artifact_copies_only_publishable_manual_files(tmp_path: Path) -> None:
    output = tmp_path / "manuals"

    copied = _MODULE.build_artifact(_ROOT, output)

    copied_names = {path.relative_to(output).as_posix() for path in copied}
    assert {
        "app.js",
        "art-of-possible.css",
        "art-of-possible.js",
        "catalog.json",
        "executive-deck.css",
        "executive-story.css",
        "library.html",
        "manual-content.js",
        "manual-decks.css",
        "ontology-foundation.css",
        "ontology-foundation.js",
        "ontology-opening.css",
        "ontology-editorial.css",
        "ontology-slide-kit.js",
        "ontology-story-foundations.js",
        "ontology-story-contracts.js",
        "ontology-story-operations.js",
        "presentation-standard.css",
        "readiness-action-plan.js",
        "readiness-ai.js",
        "readiness-diagrams.css",
        "readiness-diagrams.js",
        "readiness-foundations.js",
        "readiness-maturity-model.js",
        "readiness-maturity.css",
        "readiness-maturity.js",
        "readiness-slide-kit.js",
        "readiness-visuals.css",
        "sre-incident-response.css",
        "sre-incident-response.js",
        "styles.css",
        "target-architecture-decision.js",
        "target-architecture-diagram-kit.js",
        "target-architecture-deployment.css",
        "target-architecture-deployment.js",
        "target-architecture-execution.js",
        "target-architecture-review.js",
        "target-architecture-runtime.js",
        "target-architecture-slide-kit.js",
        "target-architecture-visuals.css",
        "target-architecture.css",
        "target-architecture.js",
        "value-prioritization-action.js",
        "value-prioritization-eligibility.js",
        "value-prioritization-foundations.js",
        "value-prioritization-portfolio.css",
        "value-prioritization-portfolio.js",
        "value-prioritization-slide-kit.js",
        "value-prioritization-value.js",
        "value-prioritization-visuals.css",
        "value-prioritization.css",
        "value-prioritization.js",
    } <= copied_names
    assert "assets/executive-briefing.jpeg" in copied_names
    assert "assets/provenance.json" in copied_names
    assert "server.mjs" not in copied_names
    assert "package.json" not in copied_names
    assert "readiness-maturity-plan.md" not in copied_names
    assert not any(name.startswith("test/") for name in copied_names)
    assert (output / "catalog.json").read_bytes() == (
        _ROOT / "tools" / "manual-studio" / "catalog.json"
    ).read_bytes()


def test_build_artifact_resolves_module_and_stylesheet_dependencies(tmp_path: Path) -> None:
    output = tmp_path / "manuals"
    copied = _MODULE.build_artifact(_ROOT, output)

    for path in copied:
        if path.suffix == ".js":
            imports = re.findall(r"\bfrom\s+[\"'](\./[^\"']+)[\"']", path.read_text())
            for imported in imports:
                assert (path.parent / imported).is_file(), (path.name, imported)

    html = (output / "library.html").read_text()
    for stylesheet in re.findall(r'href="([^"]+\.css)"', html):
        assert (output / stylesheet).is_file(), stylesheet


def test_console_publisher_binds_and_verifies_same_origin_manuals() -> None:
    publisher = _PUBLISHER_PATH.read_text(encoding="utf-8")

    assert 'VITE_MANUAL_STUDIO_URL="https://$hostname/manuals"' in publisher
    assert "build_manual_studio_artifact.py" in publisher
    assert '"https://$hostname/manuals/$manual_file"' in publisher
    assert "sha256sum --check --status" in publisher
    assert "resolve_service_fqdn operator-service" in publisher
    assert "resolve_service_fqdn document-ingestion-api" in publisher
    assert 'state_key="services/$service/$FDAI_DEPLOY_ENVIRONMENT.tfstate"' in publisher
    assert "jq -er '.fqdn | select(type == \"string\" and length > 0)'" in publisher
    assert "DEPLOY_OPERATOR_API" not in publisher
    assert "DEPLOY_DOCUMENT_INGESTION" not in publisher


def test_console_static_publish_workflow_requires_exact_green_main_revision() -> None:
    workflow = _WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "inputs.commit_sha == github.sha" in workflow
    assert "runs-on: [self-hosted, fdai-deploy, fdai-deploy-candidate]" in workflow
    assert 'select(.name == "required")' in workflow
    assert "verify-github-environment.py" not in workflow
    assert "login-deploy-identity.sh" in workflow
    assert "terraform init -input=false" in workflow
    assert "CONSOLE_DEFAULT_HOSTNAME: ${{ vars.CONSOLE_DEFAULT_HOSTNAME }}" in workflow
    assert "CONSOLE_STATIC_WEB_APP_ID: ${{ vars.CONSOLE_STATIC_WEB_APP_ID }}" in workflow
    assert "FDAI_DEPLOY_ENVIRONMENT: ${{ inputs.environment }}" in workflow
    assert (
        "STATE_RESOURCE_GROUP: ${{ vars.STATE_RESOURCE_GROUP || vars.OPS_RESOURCE_GROUP_NAME }}"
        in workflow
    )
    assert "STATE_STORAGE_ACCOUNT: ${{ vars.STATE_STORAGE_ACCOUNT }}" in workflow
    assert "publish-console.sh infra" in workflow
