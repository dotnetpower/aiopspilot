#!/usr/bin/env python3
"""Route one noninteractive FDAI Azure deployment through bounded safety stages."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TextIO

from genesis_checks import CheckError, GenesisChecks
from genesis_status import StatusStore, StatusStoreError, render_plan
from resource_provider_reconcile import ProviderReconcileError, reconcile_resource_providers

_GUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REGION = re.compile(r"^[a-z][a-z0-9]+$")


class OrchestrationError(RuntimeError):
    """Carry a stable failure reason and documented process exit code."""

    def __init__(self, reason_code: str, exit_code: int = 4) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.exit_code = exit_code


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Validated non-secret inputs for one orchestration attempt."""

    repository_root: Path
    subscription_id: str
    tenant_id: str
    region: str
    environment: str
    repository: str | None
    apply: bool
    allow_probe_resources: bool
    provider_timeout_seconds: int
    execution_timeout_seconds: int
    output: str
    work_dir: Path | None

    def validate(self) -> None:
        """Reject ambiguous targets and implicit mutation authority."""

        if _GUID.fullmatch(self.subscription_id) is None or _GUID.fullmatch(self.tenant_id) is None:
            raise OrchestrationError("invalid_azure_target", 64)
        if _REGION.fullmatch(self.region) is None:
            raise OrchestrationError("invalid_azure_region", 64)
        if self.environment not in {"dev", "staging", "prod"}:
            raise OrchestrationError("invalid_environment", 64)
        if self.repository is not None and _REPOSITORY.fullmatch(self.repository) is None:
            raise OrchestrationError("invalid_repository", 64)
        if self.apply and self.repository is None:
            raise OrchestrationError("repository_required_for_apply", 64)
        if self.apply and not self.allow_probe_resources:
            raise OrchestrationError("policy_probe_approval_required", 64)
        if not 30 <= self.provider_timeout_seconds <= 1800:
            raise OrchestrationError("invalid_provider_timeout", 64)
        if not 300 <= self.execution_timeout_seconds <= 14400:
            raise OrchestrationError("invalid_execution_timeout", 64)
        if self.apply and self.execution_timeout_seconds < 1800:
            raise OrchestrationError("apply_execution_timeout_too_short", 64)
        if self.work_dir is not None and not self.work_dir.is_absolute():
            raise OrchestrationError("work_dir_must_be_absolute", 64)


class GenesisOrchestrator:
    """Execute prerequisite checks and route only an eligible deployment path."""

    def __init__(self, config: RunConfig) -> None:
        config.validate()
        self.config = config
        self.checks = GenesisChecks(config.repository_root)
        self.source_commit = self.checks.capture(("git", "rev-parse", "HEAD"), "source_revision")
        if re.fullmatch(r"[0-9a-f]{40}", self.source_commit) is None:
            raise OrchestrationError("invalid_source_revision")
        self.target_binding = hashlib.sha256(
            (
                f"{config.tenant_id.lower()}:{config.subscription_id.lower()}:"
                f"{config.region}:{config.environment}:{config.repository or ''}"
            ).encode()
        ).hexdigest()
        mode = "apply" if config.apply else "inspect"
        work_dir = config.work_dir or (
            config.repository_root
            / ".fdai"
            / "deploy"
            / f"genesis-{self.target_binding[:12]}-{self.source_commit[:12]}-{mode}"
        )
        deadline = datetime.now(timezone.utc) + timedelta(  # noqa: UP017 - Python 3.10 entrypoint
            seconds=config.execution_timeout_seconds
        )
        self.store = StatusStore(
            path=work_dir / "status.json",
            source_commit=self.source_commit,
            target_binding=self.target_binding,
            mode=mode,
            deadline_at=deadline.isoformat().replace("+00:00", "Z"),
        )
        self.work_dir = work_dir
        self.current_stage = "toolchain"
        self.lock_stream: TextIO | None = None

    def run(self) -> int:
        """Run all currently authorized stages without prompting for input."""

        try:
            self._acquire_lock()
            render_plan(self.store.mode)
            self._stage("toolchain", self._verify_toolchain)
            self._stage("target", self._verify_target)
            self._stage("source", self._verify_source)
            if not self._reconcile_providers():
                return self._finish_waiting(
                    "providers",
                    "provider_registration_required",
                    "rerun_with_apply_and_policy_probe_approval",
                )
            if not self.config.apply:
                return self._finish_waiting(
                    "policy",
                    "policy_probe_requires_explicit_mutation_approval",
                    "rerun_with_apply_and_policy_probe_approval",
                )
            route = self._probe_policy_route()
            self.store.route = route
            self._stage("route", lambda: None)
            if route == "private-runner":
                return self._finish_waiting(
                    "execution",
                    "private_foundation_external_artifacts_required",
                    "provide_signed_offline_kit_exact_runner_image_and_foundation_profile_then_generate_exact_plan",
                )
            if route != "public-dev":
                raise OrchestrationError("deployment_route_indeterminate")
            if self.config.environment != "dev":
                raise OrchestrationError("public_route_supports_dev_only", 3)
            self._run_public_preview()
            return self._finish_waiting(
                "execution",
                "public_exact_plan_approval_required",
                "review_preview_and_create_an_exact_approved_plan",
            )
        except (OrchestrationError, CheckError) as exc:
            exit_code = exc.exit_code
            self.store.update(
                stage=self.current_stage,
                state="failed" if exit_code == 4 else "blocked",
                reason_code=exc.reason_code,
                next_action="review_failed_stage_and_resume",
            )
            self._print_final()
            return exit_code
        except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
            self.store.update(
                stage=self.current_stage,
                state="failed",
                reason_code="unexpected_orchestration_failure",
                next_action="review_failed_stage_and_resume",
            )
            self._print_final()
            return 4

    def _stage(self, stage: str, operation: Callable[[], None]) -> None:
        self.current_stage = stage
        self._bounded_timeout(1)
        self.store.update(stage=stage, state="running")
        operation()
        self._bounded_timeout(1)
        self.store.update(stage=stage, state="running", completed=True)

    def _verify_toolchain(self) -> None:
        self.checks.verify_toolchain(apply=self.config.apply)

    def _verify_target(self) -> None:
        self.checks.verify_target(
            subscription_id=self.config.subscription_id,
            tenant_id=self.config.tenant_id,
            region=self.config.region,
        )

    def _verify_source(self) -> None:
        self.checks.verify_source(
            source_commit=self.source_commit,
            repository=self.config.repository,
            apply=self.config.apply,
        )

    def _reconcile_providers(self) -> bool:
        self.current_stage = "providers"
        self.store.update(stage="providers", state="running")
        try:
            report = reconcile_resource_providers(
                subscription_id=self.config.subscription_id,
                profile="complete",
                apply=self.config.apply,
                timeout_seconds=self._bounded_timeout(
                    self.config.provider_timeout_seconds, minimum=30
                ),
                progress=self._provider_progress,
            )
        except ProviderReconcileError as exc:
            self.store.mutation_performed |= exc.mutation_performed
            raise OrchestrationError("resource_provider_reconciliation_failed") from exc
        self.store.provider_report = report.to_mapping()
        self.store.mutation_performed |= report.mutation_performed
        for namespace in report.missing:
            print(f"         registration required: {namespace}", file=sys.stderr)
        if report.state == "ready":
            self.store.update(stage="providers", state="running", completed=True)
            return True
        self.store.update(stage="providers", state="waiting")
        return False

    @staticmethod
    def _provider_progress(namespace: str, completed: int, total: int) -> None:
        print(f"         provider {completed}/{total}: {namespace}", file=sys.stderr)

    def _probe_policy_route(self) -> str:
        self.current_stage = "policy"
        if "policy" in self.store.completed:
            report = self.store.policy_report or {}
            if (
                report.get("schema_version") != "fdai.azure-policy-route.v1"
                or report.get("cleanup_complete") is not True
                or report.get("state") != "ready"
                or report.get("route") not in {"public-dev", "private-runner"}
            ):
                raise OrchestrationError("invalid_prior_policy_probe_evidence")
            self.store.route = str(report["route"])
            self.store.update(stage="policy", state="running")
            return self.store.route
        policy_file = self.work_dir / f"policy-route-attempt-{self.store.attempt}.json"
        prior_probe = self.store.policy_report or {}
        prior_binding = prior_probe.get("probe_binding")
        if prior_probe.get("state") == "probing" and isinstance(prior_binding, str):
            probe_run_id = prior_binding
        else:
            probe_run_id = hashlib.sha256(
                f"{self.target_binding}:{self.source_commit}:{self.store.attempt}".encode()
            ).hexdigest()[:16]
        if re.fullmatch(r"[0-9a-f]{16}", probe_run_id) is None:
            raise OrchestrationError("invalid_prior_policy_probe_binding")
        self.store.policy_report = {
            "schema_version": "fdai.azure-policy-route.v1",
            "state": "probing",
            "route": "incomplete",
            "cleanup_complete": False,
            "probe_binding": probe_run_id,
        }
        self.store.mutation_performed = True
        self.store.update(stage="policy", state="running")
        environment = {
            **os.environ,
            "AZURE_SUBSCRIPTION_ID": self.config.subscription_id,
            "AZURE_TENANT_ID": self.config.tenant_id,
            "FDAI_POLICY_PROBE_APPROVED": "1",
            "REGION": self.config.region,
        }
        self.checks.run_required(
            (
                "bash",
                str(self.config.repository_root / "infra/bootstrap/preflight-policy-check.sh"),
                "--run-id",
                probe_run_id,
                "--output-file",
                str(policy_file),
            ),
            "policy_probe_failed",
            timeout=self._bounded_timeout(1800, minimum=1800),
            env=environment,
        )
        report = json.loads(policy_file.read_text(encoding="utf-8"))
        if (
            report.get("schema_version") != "fdai.azure-policy-route.v1"
            or report.get("cleanup_complete") is not True
            or report.get("state") != "ready"
        ):
            raise OrchestrationError("policy_probe_incomplete")
        route = report.get("route")
        if route not in {"public-dev", "private-runner"}:
            raise OrchestrationError("deployment_route_indeterminate")
        report["probe_binding"] = probe_run_id
        self.store.policy_report = report
        self.store.mutation_performed = True
        self.store.route = str(route)
        self.store.update(stage="policy", state="running", completed=True)
        return str(route)

    def _run_public_preview(self) -> None:
        self.checks.run_required(
            ("azd", "config", "set", "auth.useAzCliAuth", "true"),
            "azd_delegated_auth_configuration_failed",
            timeout=self._bounded_timeout(30),
            capture=True,
        )
        environment = {
            **os.environ,
            "AZURE_SUBSCRIPTION_ID": self.config.subscription_id,
            "AZURE_TENANT_ID": self.config.tenant_id,
            "FDAI_AZD_CONFIRM": "0",
            "FDAI_AZD_ENVIRONMENT": f"fdai-dev-{self.target_binding[:6]}",
            "FDAI_AZURE_REGION": self.config.region,
        }
        self.checks.run_required(
            ("bash", str(self.config.repository_root / "scripts/deployment/azure/azd-up.sh")),
            "public_preview_failed",
            timeout=self._bounded_timeout(self.config.execution_timeout_seconds),
            env=environment,
        )
        self.checks.verify_checkout_unchanged()

    def _bounded_timeout(self, maximum: int, *, minimum: int = 1) -> int:
        remaining = self.store.remaining_seconds()
        if remaining < minimum:
            raise OrchestrationError("orchestration_deadline_exceeded", 3)
        return min(maximum, remaining)

    def _finish_waiting(self, stage: str, reason: str, next_action: str) -> int:
        self.current_stage = stage
        self.store.update(
            stage=stage,
            state="waiting",
            reason_code=reason,
            next_action=next_action,
        )
        self._print_final()
        return 2

    def _acquire_lock(self) -> None:
        lock_path = self.work_dir / "orchestration.lock"
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise OrchestrationError("unsafe_orchestration_lock", 3) from exc
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_uid != os.geteuid()
        ):
            os.close(descriptor)
            raise OrchestrationError("unsafe_orchestration_lock", 3)
        self.lock_stream = os.fdopen(descriptor, "a", encoding="utf-8")
        try:
            fcntl.flock(self.lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise OrchestrationError("another_orchestration_attempt_is_active", 3) from exc

    def _print_final(self) -> None:
        if self.config.output == "json":
            print(json.dumps(self.store.payload, sort_keys=True, separators=(",", ":")))
        else:
            payload = self.store.payload
            print(
                f"genesis state={payload['state']} route={payload['route']} "
                f"progress={payload['progress_percent']}% status={self.store.path}"
            )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="authorize provider registration and routing probe, not an unsealed plan apply",
    )
    parser.add_argument(
        "--allow-probe-resources",
        action="store_true",
        help="authorize creation and verified cleanup of the policy probe resource group",
    )
    parser.add_argument("--repository")
    parser.add_argument("--environment", choices=("dev", "staging", "prod"), default="dev")
    parser.add_argument("--region", default="koreacentral")
    parser.add_argument("--provider-timeout-seconds", type=int, default=900)
    parser.add_argument("--execution-timeout-seconds", type=int, default=10800)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--output", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse one noninteractive request and run the policy-aware orchestrator."""

    args = _parser().parse_args(argv)
    repository_root = Path(__file__).resolve().parents[3]
    config = RunConfig(
        repository_root=repository_root,
        subscription_id=os.environ.get("AZURE_SUBSCRIPTION_ID", ""),
        tenant_id=os.environ.get("AZURE_TENANT_ID", ""),
        region=args.region,
        environment=args.environment,
        repository=args.repository,
        apply=args.apply,
        allow_probe_resources=args.allow_probe_resources,
        provider_timeout_seconds=args.provider_timeout_seconds,
        execution_timeout_seconds=args.execution_timeout_seconds,
        output=args.output,
        work_dir=args.work_dir,
    )
    try:
        return GenesisOrchestrator(config).run()
    except (OrchestrationError, CheckError, StatusStoreError) as exc:
        reason = exc.reason_code if isinstance(exc, (OrchestrationError, CheckError)) else str(exc)
        code = exc.exit_code if isinstance(exc, (OrchestrationError, CheckError)) else 4
        print(f"genesis-up: {reason}", file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
