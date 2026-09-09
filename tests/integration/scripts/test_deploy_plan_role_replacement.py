"""Regression tests for the protected Operator identity role replacement."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = (ROOT / ".github/workflows/deploy-dev.yml").read_text(encoding="utf-8")
ROLE_ADDRESS = (
    'module.llm_azure_openai[0].azurerm_role_assignment.additional_openai_user["operator_api"]'
)
IDENTITY_ADDRESS = "module.operator_api_identity[0].azurerm_user_assigned_identity.primary"


def _guard_source() -> str:
    step = WORKFLOW.split("- name: Reject destructive protected plan", maxsplit=1)[1].split(
        "- name: Run complete Azure live preflight",
        maxsplit=1,
    )[0]
    match = re.search(r"python3 - <<'PY'\n(?P<source>.*?)\n\s+PY", step, re.DOTALL)
    assert match is not None
    return textwrap.dedent(match.group("source"))


def _plan(mutation: str | None = None) -> dict[str, object]:
    before = {
        "scope": "same-account",
        "role_definition_id": "openai-user-role",
        "role_definition_name": "Cognitive Services OpenAI User",
        "principal_id": "old-principal",
        "principal_type": "ServicePrincipal",
        "condition": None,
        "delegated_managed_identity_resource_id": None,
    }
    after = {
        **before,
        "role_definition_id": None,
        "principal_id": None,
        "principal_type": None,
    }
    role_change = {
        "address": ROLE_ADDRESS,
        "change": {
            "actions": ["delete", "create"],
            "before": before,
            "after": after,
            "after_unknown": {
                "role_definition_id": True,
                "principal_id": True,
                "principal_type": True,
            },
            "replace_paths": [["principal_id"]],
        },
    }
    identity_change = {
        "address": IDENTITY_ADDRESS,
        "change": {"actions": ["create"], "before": None, "after": {}},
    }
    changes = [role_change, identity_change]
    details = role_change["change"]
    assert isinstance(details, dict)

    if mutation == "missing-successor":
        changes.pop()
    elif mutation == "successor-update":
        identity_change["change"] = {"actions": ["update"], "before": {}, "after": {}}
    elif mutation == "scope":
        after["scope"] = "different-account"
    elif mutation == "role":
        after["role_definition_name"] = "Owner"
    elif mutation == "concrete-principal":
        after["principal_id"] = "new-principal"
    elif mutation == "role-definition-id":
        after["role_definition_id"] = "different-role"
    elif mutation == "unknown-principal":
        details["after_unknown"] = {"principal_id": False}
    elif mutation == "replace-path":
        details["replace_paths"] = [["scope"]]
    elif mutation == "action-order":
        details["actions"] = ["create", "delete"]
    elif mutation is not None:
        raise AssertionError(f"unknown test mutation: {mutation}")
    return {"resource_changes": changes}


def _run_guard(tmp_path: Path, mutation: str | None = None) -> subprocess.CompletedProcess[str]:
    (tmp_path / "dev.plan.review.json").write_text(
        json.dumps(_plan(mutation)),
        encoding="utf-8",
    )
    return subprocess.run(  # noqa: S603 - fixed interpreter executes reviewed local source
        [sys.executable, "-c", _guard_source()],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )


def test_guard_accepts_exact_operator_identity_role_replacement(tmp_path: Path) -> None:
    result = _run_guard(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "permits exact identity role replacement" in result.stdout


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-successor",
        "successor-update",
        "scope",
        "role",
        "concrete-principal",
        "role-definition-id",
        "unknown-principal",
        "replace-path",
        "action-order",
    ],
)
def test_guard_rejects_operator_identity_role_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    result = _run_guard(tmp_path, mutation)

    assert result.returncode == 1
    assert ROLE_ADDRESS in result.stdout
