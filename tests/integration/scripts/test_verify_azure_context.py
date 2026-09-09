from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_VERIFY = _ROOT / "scripts" / "deployment" / "azure" / "verify-azure-context.sh"
_AZD_UP = _ROOT / "scripts" / "deployment" / "azure" / "azd-up.sh"


def _fake_az(tmp_path: Path) -> tuple[Path, Path]:
    calls = tmp_path / "calls"
    binary = tmp_path / "az"
    binary.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$FAKE_AZ_CALLS"
if [[ "$1 $2" == "account show" ]]; then
    if [[ " $* " == *" --subscription "* ]]; then
        if [[ "${FAKE_AZ_SHOW_FAIL:-0}" == "1" ]]; then
            exit 1
        fi
        # Real `az ... --query '[id,tenantId]' --output tsv` prints one element per
        # line. A tab-joined fake hides a parser that only ever reads the first line.
        printf '%s\n%s\n' "$FAKE_AZ_SUBSCRIPTION" "$FAKE_AZ_TENANT"
    else
        printf '%s\n' "${FAKE_AZ_ACTIVE_TENANT:-$FAKE_AZ_TENANT}"
    fi
elif [[ "$1 $2" == "account set" ]]; then
  exit 0
elif [[ "$1 $2" == "cloud show" ]]; then
    printf '%s\n' AzureCloud
elif [[ "$1 $2" == "provider show" ]]; then
    printf '%s\n' "${FAKE_AZ_PROVIDER_STATE:-Registered}"
elif [[ "$1 $2 $3" == "ad signed-in-user show" ]]; then
    printf '%s\n' 00000000-0000-0000-0000-000000000003
else
  exit 9
fi
""",
        encoding="ascii",
    )
    binary.chmod(0o755)
    return binary, calls


def _run(
    tmp_path: Path,
    *,
    actual_subscription: str = "sub-expected",
    actual_tenant: str = "tenant-expected",
    active_tenant: str | None = None,
    show_fails: bool = False,
) -> tuple[subprocess.CompletedProcess[str], str]:
    _binary, calls = _fake_az(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "FAKE_AZ_CALLS": str(calls),
        "FAKE_AZ_SUBSCRIPTION": actual_subscription,
        "FAKE_AZ_TENANT": actual_tenant,
        "FAKE_AZ_ACTIVE_TENANT": active_tenant or actual_tenant,
        "FAKE_AZ_SHOW_FAIL": "1" if show_fails else "0",
    }
    result = subprocess.run(  # noqa: S603 - controlled repository script
        [str(_VERIFY), "sub-expected", "tenant-expected"],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, calls.read_text(encoding="ascii") if calls.exists() else ""


def test_exact_context_is_selected_only_after_both_axes_match(tmp_path: Path) -> None:
    result, calls = _run(tmp_path)

    assert result.returncode == 0
    assert "exact subscription and tenant verified" in result.stdout
    assert "account show --query tenantId" in calls
    assert "account show --subscription sub-expected" in calls
    assert "account set --subscription sub-expected" in calls


def test_active_tenant_mismatch_blocks_cross_profile_subscription_lookup(
    tmp_path: Path,
) -> None:
    result, calls = _run(tmp_path, active_tenant="tenant-other")

    assert result.returncode == 1
    assert "active tenant does not match" in result.stderr
    assert "account show --subscription" not in calls
    assert "account set" not in calls


@pytest.mark.parametrize(
    ("subscription", "tenant", "message"),
    [
        ("sub-other", "tenant-expected", "subscription does not match"),
        ("sub-expected", "tenant-other", "tenant does not match"),
    ],
)
def test_mismatch_fails_before_account_set(
    tmp_path: Path,
    subscription: str,
    tenant: str,
    message: str,
) -> None:
    result, calls = _run(
        tmp_path,
        actual_subscription=subscription,
        actual_tenant=tenant,
    )

    assert result.returncode == 1
    assert message in result.stderr
    assert "account set" not in calls


def test_unavailable_expected_subscription_fails_closed(tmp_path: Path) -> None:
    result, calls = _run(tmp_path, show_fails=True)

    assert result.returncode == 1
    assert "expected subscription is unavailable" in result.stderr
    assert "account set" not in calls


def test_private_bootstrap_callers_verify_before_mutation() -> None:
    callers = {
        "infra/bootstrap/onboard.sh": "create-state-account.sh",
        "infra/bootstrap/create-state-account.sh": "az group show",
        "infra/bootstrap/preflight-policy-check.sh": "az group create",
        "infra/bootstrap/register-runner.sh": "gh api -X POST",
        "scripts/deployment/azure/set-gh-actions-config.sh": "gh variable set",
    }
    for relative, first_mutation in callers.items():
        content = (_ROOT / relative).read_text(encoding="utf-8")
        assert content.index("verify-azure-context.sh") < content.index(first_mutation)

    workflow = (_ROOT / ".github" / "workflows" / "deploy-dev.yml").read_text(encoding="utf-8")
    assert workflow.index("Verify exact Azure context") < workflow.index(
        "Verify protected storage containers"
    )


def _fake_azd(tmp_path: Path) -> Path:
    calls = tmp_path / "azd-calls"
    binary = tmp_path / "azd"
    binary.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$FAKE_AZD_CALLS"
case "$1 $2" in
    "env select") exit 0 ;;
    "env get-value") printf '%s\n' "$FAKE_AZD_SUBSCRIPTION" ;;
    "env set") exit 0 ;;
    "auth login") exit 0 ;;
    "provision --environment") exit 0 ;;
    *) exit 9 ;;
esac
""",
        encoding="ascii",
    )
    binary.chmod(0o755)
    return calls


def _fake_uv(tmp_path: Path) -> None:
    binary = tmp_path / "uv"
    binary.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --out|--output)
            output="$2"
            shift 2
            ;;
        *) shift ;;
    esac
done
if [[ -n "$output" ]]; then
    payload='{"schema_version":"1.0.0","capabilities":[]'
    payload+=',"mixed_model_mode":"hil-only"}'
    printf '%s\n' "$payload" > "$output"
fi
""",
        encoding="ascii",
    )
    binary.chmod(0o755)


def _fake_terraform(tmp_path: Path) -> None:
    binary = tmp_path / "terraform"
    binary.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="ascii")
    binary.chmod(0o755)


def test_azd_wrapper_rejects_mismatched_selected_environment(tmp_path: Path) -> None:
    _binary, az_calls = _fake_az(tmp_path)
    azd_calls = _fake_azd(tmp_path)
    _fake_uv(tmp_path)
    _fake_terraform(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "FAKE_AZ_CALLS": str(az_calls),
        "FAKE_AZ_SUBSCRIPTION": "sub-expected",
        "FAKE_AZ_TENANT": "tenant-expected",
        "FAKE_AZD_CALLS": str(azd_calls),
        "FAKE_AZD_SUBSCRIPTION": "sub-other",
        "AZURE_SUBSCRIPTION_ID": "sub-expected",
        "AZURE_TENANT_ID": "tenant-expected",
        "FDAI_AZD_WORK_DIR": str(tmp_path / "work"),
    }

    result = subprocess.run(  # noqa: S603 - controlled repository script
        [str(_AZD_UP)],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "does not match AZURE_SUBSCRIPTION_ID" in result.stderr
    assert "provision --preview" not in azd_calls.read_text(encoding="ascii")


def test_azd_wrapper_previews_after_exact_context_verification(tmp_path: Path) -> None:
    _binary, az_calls = _fake_az(tmp_path)
    azd_calls = _fake_azd(tmp_path)
    _fake_uv(tmp_path)
    _fake_terraform(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "FAKE_AZ_CALLS": str(az_calls),
        "FAKE_AZ_SUBSCRIPTION": "sub-expected",
        "FAKE_AZ_TENANT": "tenant-expected",
        "FAKE_AZD_CALLS": str(azd_calls),
        "FAKE_AZD_SUBSCRIPTION": "sub-expected",
        "AZURE_SUBSCRIPTION_ID": "sub-expected",
        "AZURE_TENANT_ID": "tenant-expected",
        "FDAI_AZD_WORK_DIR": str(tmp_path / "work"),
    }

    result = subprocess.run(  # noqa: S603 - controlled repository script
        [str(_AZD_UP)],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    azure_calls = az_calls.read_text(encoding="ascii")
    deployment_calls = azd_calls.read_text(encoding="ascii")
    assert "account set --subscription sub-expected" in azure_calls
    assert "provider register" not in azure_calls
    assert "role assignment create" not in azure_calls
    assert "acr build" not in azure_calls
    assert "postgres flexible-server firewall-rule create" not in azure_calls
    assert "provision --environment fdai-dev" in deployment_calls
    assert "--preview" in deployment_calls


def test_azd_wrapper_reports_provider_registration_without_mutating(
    tmp_path: Path,
) -> None:
    _binary, az_calls = _fake_az(tmp_path)
    azd_calls = _fake_azd(tmp_path)
    _fake_uv(tmp_path)
    _fake_terraform(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "FAKE_AZ_CALLS": str(az_calls),
        "FAKE_AZ_SUBSCRIPTION": "sub-expected",
        "FAKE_AZ_TENANT": "tenant-expected",
        "FAKE_AZ_PROVIDER_STATE": "NotRegistered",
        "FAKE_AZD_CALLS": str(azd_calls),
        "FAKE_AZD_SUBSCRIPTION": "sub-expected",
        "AZURE_SUBSCRIPTION_ID": "sub-expected",
        "AZURE_TENANT_ID": "tenant-expected",
        "FDAI_AZD_WORK_DIR": str(tmp_path / "work"),
    }

    result = subprocess.run(  # noqa: S603 - controlled repository script
        [str(_AZD_UP)],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "require registration" in result.stderr
    assert "provider register" not in az_calls.read_text(encoding="ascii")
    assert "provision" not in azd_calls.read_text(encoding="ascii")
