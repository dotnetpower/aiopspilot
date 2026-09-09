"""Regression tests for the protected Operator identity role replacement."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from scripts.deployment.azure import guard_operator_role_plan as guard

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = (ROOT / ".github/workflows/deploy-dev.yml").read_text(encoding="utf-8")


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
        "address": guard.ROLE_ADDRESS,
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
        "address": guard.IDENTITY_ADDRESS,
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


def test_workflow_runs_guard_before_excluding_reviewed_role() -> None:
    guard_command = "python3 ../scripts/deployment/azure/guard_operator_role_plan.py"

    assert guard_command in WORKFLOW
    assert guard.ROLE_ADDRESS not in WORKFLOW


def test_guard_accepts_exact_operator_identity_role_replacement() -> None:
    assert guard.validate_operator_role_replacement(_plan()) is True
    filtered, accepted = guard.filter_validated_operator_role_replacement(_plan())

    assert accepted is True
    assert all(
        not isinstance(change, dict) or change.get("address") != guard.ROLE_ADDRESS
        for change in filtered["resource_changes"]
    )


def test_guard_cli_filters_the_temporary_review_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan_path = tmp_path / "dev.plan.review.json"
    plan_path.write_text(json.dumps(_plan()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["guard_operator_role_plan.py", "--plan", str(plan_path)])

    assert guard.main() == 0
    filtered = json.loads(plan_path.read_text(encoding="utf-8"))
    assert all(
        change.get("address") != guard.ROLE_ADDRESS for change in filtered["resource_changes"]
    )


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
    mutation: str,
) -> None:
    with pytest.raises(ValueError, match="Operator API role replacement"):
        guard.validate_operator_role_replacement(_plan(mutation))
