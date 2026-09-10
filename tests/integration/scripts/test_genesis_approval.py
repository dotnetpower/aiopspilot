"""Private exact-evidence Genesis approval regressions."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "scripts/deployment/azure"
sys.path.insert(0, str(SCRIPT_DIR))

from genesis_approval import load_genesis_approval  # noqa: E402

RUN_BINDING = "a" * 64
SOURCE_COMMIT = "b" * 40


def _write(path: Path, value: dict[str, object]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")


def _approval(stage: str, evidence: dict[str, str]) -> dict[str, object]:
    approved_at = datetime.now(timezone.utc).replace(  # noqa: UP017 - mirrors Python 3.10 script
        microsecond=0
    )
    return {
        "schema_version": "fdai.genesis-approval.v1",
        "run_binding": RUN_BINDING,
        "source_commit": SOURCE_COMMIT,
        "stage": stage,
        "approved": True,
        "approved_at": approved_at.isoformat(),
        "expires_at": (approved_at + timedelta(minutes=30)).isoformat(),
        "evidence": evidence,
    }


def test_exact_checkpoint_approval_matches_only_its_bound_evidence(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "approval.json"
    evidence = {"review_digest": "c" * 64, "plan_digest": "d" * 64}
    _write(path, _approval("foundation-apply", evidence))

    approval = load_genesis_approval(path, run_binding=RUN_BINDING, source_commit=SOURCE_COMMIT)

    assert approval is not None
    assert approval.authorizes("runner-image", **evidence) is False
    assert approval.authorizes("foundation-apply", **evidence) is True
    with pytest.raises(ValueError, match="does not match"):
        approval.authorizes(
            "foundation-apply",
            review_digest="c" * 64,
            plan_digest="e" * 64,
        )


@pytest.mark.parametrize(
    "mutation",
    ("target", "source", "approved", "stage", "field", "digest"),
)
def test_approval_rejects_wrong_context_authority_or_shape(tmp_path: Path, mutation: str) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "approval.json"
    value = _approval("runner-enrollment", {"foundation_receipt_digest": "c" * 64})
    if mutation == "target":
        value["run_binding"] = "d" * 64
    elif mutation == "source":
        value["source_commit"] = "e" * 40
    elif mutation == "approved":
        value["approved"] = False
    elif mutation == "stage":
        value["stage"] = "unknown"
    elif mutation == "field":
        evidence = value["evidence"]
        assert isinstance(evidence, dict)
        evidence["unexpected"] = "f" * 64
    else:
        evidence = value["evidence"]
        assert isinstance(evidence, dict)
        evidence["foundation_receipt_digest"] = "invalid"
    _write(path, value)

    with pytest.raises(ValueError, match="Genesis approval"):
        load_genesis_approval(path, run_binding=RUN_BINDING, source_commit=SOURCE_COMMIT)


def test_approval_requires_private_single_link_file(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "approval.json"
    _write(path, _approval("runner-image", {"review_digest": "c" * 64, "plan_digest": "d" * 64}))
    path.chmod(0o644)

    with pytest.raises(PermissionError, match="mode-0600"):
        load_genesis_approval(path, run_binding=RUN_BINDING, source_commit=SOURCE_COMMIT)


def test_approval_rejects_an_expired_window(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "approval.json"
    value = _approval("runner-enrollment", {"foundation_receipt_digest": "c" * 64})
    value["approved_at"] = "2000-01-01T00:00:00+00:00"
    value["expires_at"] = "2000-01-01T00:30:00+00:00"
    _write(path, value)

    with pytest.raises(ValueError, match="expired"):
        load_genesis_approval(path, run_binding=RUN_BINDING, source_commit=SOURCE_COMMIT)
