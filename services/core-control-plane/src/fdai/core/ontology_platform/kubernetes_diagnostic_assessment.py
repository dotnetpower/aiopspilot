"""Reduce exact-target AKS diagnostic evidence into a Forseti-owned T0 receipt."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal

from fdai.shared.contracts.models import ContractBase
from fdai.shared.providers.inventory import ResourceRecord
from fdai.shared.providers.kubernetes_metric import KubernetesMetricWindowEvidence


class AksDiagnosticStatus(StrEnum):
    """Primary evidence classification for one exact Kubernetes target."""

    AUTOSCALE_LIMITED = "autoscale_limited"
    CONTROL_PLANE_UNAVAILABLE = "control_plane_unavailable"
    CRASH_LOOP = "crash_loop"
    ENDPOINT_UNREADY = "endpoint_unready"
    EVICTED = "evicted"
    HELD = "held"
    IMAGE_PULL_FAILED = "image_pull_failed"
    NODE_PRESSURE = "node_pressure"
    NO_FAILURE_SIGNAL = "no_failure_signal"
    OOM_KILLED = "oom_killed"
    PROBE_FAILURE_EVIDENCE = "probe_failure_evidence"
    QUOTA_CONSTRAINED = "quota_constrained"
    RESOURCE_PRESSURE = "resource_pressure"
    ROLLOUT_STALLED = "rollout_stalled"
    SCHEDULING_BLOCKED = "scheduling_blocked"
    STORAGE_BLOCKED = "storage_blocked"


_SIGNAL_PRIORITY = tuple(AksDiagnosticStatus)


class AksDiagnosticEvidenceReceipt(ContractBase):
    """Replayable no-authority evidence emitted for Forseti RCA admission."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    owner_agent: Literal["Forseti"] = "Forseti"
    principal_class: str
    purpose: Literal["operations-review"] = "operations-review"
    producer_version: str
    method_version: str
    target_resource_id: str
    target_uid: str
    target_resource_version: str
    ontology_release: str
    cutoff: datetime
    source_cutoffs: dict[str, datetime]
    source_revisions: dict[str, str]
    status: AksDiagnosticStatus
    signals: tuple[AksDiagnosticStatus, ...]
    complete: bool
    evidence_gaps: tuple[str, ...]
    conflicts: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    synthetic: Literal[False] = False
    cause_claim_supported: Literal[False] = False
    execution_authority: Literal[False] = False
    audit_correlation_id: str


@dataclass(frozen=True, slots=True)
class AksDiagnosticContext:
    """Exact target and independently qualified evidence used by one reducer."""

    target: ResourceRecord
    related: tuple[ResourceRecord, ...]
    event_reasons: tuple[str, ...]
    metrics: tuple[KubernetesMetricWindowEvidence, ...]
    api_reachable: bool | None
    azure_availability: str | None
    cutoff: datetime
    source_cutoffs: dict[str, datetime]
    source_revisions: dict[str, str]
    evidence_refs: tuple[str, ...]
    evidence_complete: bool
    ontology_release: str
    principal_class: str
    audit_correlation_id: str


def assess_aks_diagnostic(context: AksDiagnosticContext) -> AksDiagnosticEvidenceReceipt:
    """Return deterministic signals without claiming root cause or execution authority."""

    if context.cutoff.tzinfo is None:
        raise ValueError("AKS diagnostic cutoff MUST be timezone-aware")
    props = context.target.props
    uid = _required_text(props, "uid")
    resource_version = _required_text(props, "resource_version")
    for source, cutoff in context.source_cutoffs.items():
        if not source.strip() or cutoff.tzinfo is None or cutoff > context.cutoff:
            raise ValueError("AKS diagnostic source cutoff is invalid")
    if any(not key.strip() or not value.strip() for key, value in context.source_revisions.items()):
        raise ValueError("AKS diagnostic source revisions MUST be bounded non-empty text")

    gaps: list[str] = []
    conflicts: list[str] = []
    if not context.evidence_complete:
        gaps.append("required_evidence_incomplete")
    if set(context.source_cutoffs) != set(context.source_revisions):
        conflicts.append("source_identity_mismatch")
    signals = _signals(context)
    if conflicts or (not signals and gaps):
        status = AksDiagnosticStatus.HELD
    elif signals:
        status = min(signals, key=_SIGNAL_PRIORITY.index)
    else:
        status = AksDiagnosticStatus.NO_FAILURE_SIGNAL
    return AksDiagnosticEvidenceReceipt(
        principal_class=context.principal_class,
        producer_version="aks-diagnostic-evidence-v1",
        method_version="deterministic-t0-v1",
        target_resource_id=context.target.resource_id,
        target_uid=uid,
        target_resource_version=resource_version,
        ontology_release=context.ontology_release,
        cutoff=context.cutoff,
        source_cutoffs=context.source_cutoffs,
        source_revisions=context.source_revisions,
        status=status,
        signals=tuple(sorted(signals, key=_SIGNAL_PRIORITY.index)),
        complete=not gaps and not conflicts,
        evidence_gaps=tuple(gaps),
        conflicts=tuple(conflicts),
        evidence_refs=tuple(dict.fromkeys(context.evidence_refs)),
        audit_correlation_id=context.audit_correlation_id,
    )


def _signals(context: AksDiagnosticContext) -> set[AksDiagnosticStatus]:
    props = context.target.props
    signals: set[AksDiagnosticStatus] = set()
    waiting = _string_set(props.get("container_waiting_reasons"))
    waiting.update(_string_set(props.get("init_container_waiting_reasons")))
    if waiting & {"ErrImagePull", "ImagePullBackOff", "InvalidImageName"}:
        signals.add(AksDiagnosticStatus.IMAGE_PULL_FAILED)
    if "CrashLoopBackOff" in waiting:
        signals.add(AksDiagnosticStatus.CRASH_LOOP)
    terminations = props.get("container_terminations")
    if isinstance(terminations, tuple) and any(
        isinstance(item, dict) and item.get("reason") == "OOMKilled" for item in terminations
    ):
        signals.add(AksDiagnosticStatus.OOM_KILLED)
    if props.get("reason") == "Evicted":
        signals.add(AksDiagnosticStatus.EVICTED)
    if "Unhealthy" in context.event_reasons:
        signals.add(AksDiagnosticStatus.PROBE_FAILURE_EVIDENCE)
    conditions = _conditions(props)
    if conditions.get("PodScheduled") == "False":
        signals.add(AksDiagnosticStatus.SCHEDULING_BLOCKED)
    if any(
        conditions.get(name) == "True"
        for name in ("DiskPressure", "MemoryPressure", "NetworkUnavailable", "PIDPressure")
    ):
        signals.add(AksDiagnosticStatus.NODE_PRESSURE)
    if context.target.type == "kubernetes.endpoint-slice":
        endpoint_count = _count(props, "endpoint_count")
        ready = _count(props, "ready")
        if endpoint_count > 0 and ready == 0:
            signals.add(AksDiagnosticStatus.ENDPOINT_UNREADY)
    if context.target.type in {
        "kubernetes.daemon-set",
        "kubernetes.deployment",
        "kubernetes.stateful-set",
    } and (_count(props, "unavailable_replicas") > 0 or conditions.get("Progressing") == "False"):
        signals.add(AksDiagnosticStatus.ROLLOUT_STALLED)
    if context.target.type in {
        "kubernetes.persistent-volume",
        "kubernetes.persistent-volume-claim",
    } and props.get("phase") in {"Failed", "Lost", "Pending", "Released"}:
        signals.add(AksDiagnosticStatus.STORAGE_BLOCKED)
    if context.target.type == "kubernetes.resource-quota" and _quota_exhausted(props):
        signals.add(AksDiagnosticStatus.QUOTA_CONSTRAINED)
    if context.target.type == "kubernetes.horizontal-pod-autoscaler" and (
        conditions.get("ScalingLimited") == "True"
        or (
            _count(props, "max_replicas") > 0
            and _count(props, "current_replicas") >= _count(props, "max_replicas")
        )
    ):
        signals.add(AksDiagnosticStatus.AUTOSCALE_LIMITED)
    if context.api_reachable is False or context.azure_availability in {
        "Degraded",
        "Unavailable",
    }:
        signals.add(AksDiagnosticStatus.CONTROL_PLANE_UNAVAILABLE)
    for metric in context.metrics:
        if not metric.complete:
            continue
        if metric.metric_name == "kubernetes.container.oom_events" and any(
            point.value > 0 for point in metric.points
        ):
            signals.add(AksDiagnosticStatus.OOM_KILLED)
        if metric.metric_name in {
            "kubernetes.container.cpu.throttled_seconds",
            "kubernetes.node.pressure",
        } and any(point.value > 0 for point in metric.points):
            signals.add(AksDiagnosticStatus.RESOURCE_PRESSURE)
    return signals


def _conditions(props: Mapping[str, object]) -> dict[str, str]:
    raw = props.get("diagnostic_conditions")
    if not isinstance(raw, tuple):
        return {}
    output: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        kind = item.get("type")
        status = item.get("status")
        if isinstance(kind, str) and isinstance(status, str):
            output[kind] = status
    return output


def _quota_exhausted(props: Mapping[str, object]) -> bool:
    hard = props.get("quota_hard")
    used = props.get("quota_used")
    return (
        isinstance(hard, Mapping)
        and isinstance(used, Mapping)
        and any(used.get(key) == value for key, value in hard.items())
    )


def _string_set(value: object) -> set[str]:
    if not isinstance(value, tuple):
        return set()
    return {item for item in value if isinstance(item, str)}


def _count(props: Mapping[str, object], key: str) -> int:
    direct = props.get(key)
    if isinstance(direct, int) and not isinstance(direct, bool):
        return direct
    status_counts = props.get("status_counts")
    if isinstance(status_counts, Mapping):
        nested = status_counts.get(key)
        if isinstance(nested, int) and not isinstance(nested, bool):
            return nested
    return 0


def _required_text(props: Mapping[str, object], key: str) -> str:
    value = props.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError(f"AKS diagnostic target {key} MUST be bounded non-empty text")
    return value.strip()


__all__ = [
    "AksDiagnosticContext",
    "AksDiagnosticEvidenceReceipt",
    "AksDiagnosticStatus",
    "assess_aks_diagnostic",
]
