"""Collect bounded exact-target Kubernetes metric evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from fdai.shared.providers.metric import MetricPoint, MetricProvider, MetricQuery

_MAX_POINTS: Final[int] = 20
KUBERNETES_DIAGNOSTIC_METRICS: Final[frozenset[str]] = frozenset(
    {
        "kubernetes.container.cpu.usage",
        "kubernetes.container.cpu.throttled_seconds",
        "kubernetes.container.filesystem.usage_bytes",
        "kubernetes.container.memory.working_set_bytes",
        "kubernetes.container.network.receive_bytes",
        "kubernetes.container.network.transmit_bytes",
        "kubernetes.container.oom_events",
        "kubernetes.node.allocatable.cpu",
        "kubernetes.node.allocatable.memory_bytes",
        "kubernetes.node.pressure",
        "kubernetes.pod.request.cpu",
        "kubernetes.pod.request.memory_bytes",
    }
)


@dataclass(frozen=True, slots=True)
class KubernetesMetricTarget:
    """Exact Kubernetes metric subject."""

    cluster_ref: str
    uid: str
    namespace: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("cluster_ref", "uid"):
            value = getattr(self, field_name)
            if not value.strip() or len(value) > 512:
                raise ValueError(f"Kubernetes metric {field_name} MUST be bounded non-empty text")
        if self.namespace is not None and (not self.namespace.strip() or len(self.namespace) > 253):
            raise ValueError("Kubernetes metric namespace MUST be bounded non-empty text or null")


@dataclass(frozen=True, slots=True)
class KubernetesMetricWindowEvidence:
    """Validated metric candidates plus independent window-coverage state."""

    metric_name: str
    target: KubernetesMetricTarget
    start: datetime
    end: datetime
    points: tuple[MetricPoint, ...]
    source_identity: str
    source_revision: str
    provider_cutoff: datetime | None
    coverage_receipt_ref: str | None
    complete: bool
    limitation: str | None

    def __post_init__(self) -> None:
        if self.metric_name not in KUBERNETES_DIAGNOSTIC_METRICS:
            raise ValueError("Kubernetes diagnostic metric name is not reviewed")
        if self.start.tzinfo is None or self.end.tzinfo is None or self.start >= self.end:
            raise ValueError("Kubernetes metric window MUST be aware and positive")
        if not self.source_identity.strip() or not self.source_revision.strip():
            raise ValueError("Kubernetes metric source identity and revision are required")
        if len(self.points) > _MAX_POINTS:
            raise ValueError("Kubernetes metric evidence exceeds its point bound")
        if self.complete != (self.limitation is None):
            raise ValueError("Kubernetes metric completeness and limitation are inconsistent")
        if self.complete and (self.provider_cutoff is None or self.coverage_receipt_ref is None):
            raise ValueError("complete Kubernetes metrics require provider cutoff and coverage")


class KubernetesMetricEvidenceCollector:
    """Validate exact-label metric candidates without inventing source coverage."""

    def __init__(
        self,
        *,
        provider: MetricProvider,
        source_identity: str,
        source_revision: str,
        coverage_receipt_ref: str | None = None,
        provider_cutoff: datetime | None = None,
    ) -> None:
        if not source_identity.strip() or not source_revision.strip():
            raise ValueError("Kubernetes metric source identity and revision are required")
        if (coverage_receipt_ref is None) != (provider_cutoff is None):
            raise ValueError("Kubernetes metric coverage receipt and cutoff MUST be paired")
        if provider_cutoff is not None and provider_cutoff.tzinfo is None:
            raise ValueError("Kubernetes metric provider cutoff MUST be timezone-aware")
        self._provider = provider
        self._source_identity = source_identity
        self._source_revision = source_revision
        self._coverage_receipt_ref = coverage_receipt_ref
        self._provider_cutoff = provider_cutoff

    async def collect(
        self,
        *,
        metric_name: str,
        target: KubernetesMetricTarget,
        start: datetime,
        end: datetime,
    ) -> KubernetesMetricWindowEvidence:
        """Return bounded exact-target points and honest coverage state."""

        if metric_name not in KUBERNETES_DIAGNOSTIC_METRICS:
            raise ValueError("Kubernetes diagnostic metric name is not reviewed")
        if start.tzinfo is None or end.tzinfo is None or start >= end:
            raise ValueError("Kubernetes metric window MUST be aware and positive")
        labels = {"cluster_ref": target.cluster_ref, "uid": target.uid}
        if target.namespace is not None:
            labels["namespace"] = target.namespace
        points: list[MetricPoint] = []
        async for point in self._provider.query(
            MetricQuery(
                metric_name=metric_name,
                labels=labels,
                since=start,
                until=end,
            )
        ):
            points.append(point)
            if len(points) > _MAX_POINTS:
                break
        limitation = self._validate_points(
            points,
            metric_name=metric_name,
            labels=labels,
            start=start,
            end=end,
        )
        bounded = tuple(sorted(points[:_MAX_POINTS], key=lambda item: (item.at, item.value)))
        if limitation is None and len(points) > _MAX_POINTS:
            limitation = "result_truncated"
        if limitation is None and self._coverage_receipt_ref is None:
            limitation = "provider_coverage_unverified"
        return KubernetesMetricWindowEvidence(
            metric_name=metric_name,
            target=target,
            start=start,
            end=end,
            points=bounded if limitation != "point_scope_invalid" else (),
            source_identity=self._source_identity,
            source_revision=self._source_revision,
            provider_cutoff=self._provider_cutoff,
            coverage_receipt_ref=self._coverage_receipt_ref,
            complete=limitation is None,
            limitation=limitation,
        )

    @staticmethod
    def _validate_points(
        points: list[MetricPoint],
        *,
        metric_name: str,
        labels: dict[str, str],
        start: datetime,
        end: datetime,
    ) -> str | None:
        for point in points:
            if (
                point.metric_name != metric_name
                or point.at.tzinfo is None
                or not start <= point.at <= end
                or any(point.labels.get(key) != value for key, value in labels.items())
                or not math.isfinite(point.value)
                or point.value < 0
            ):
                return "point_scope_invalid"
        if not points:
            return "zero_points_unverified"
        return None


__all__ = [
    "KUBERNETES_DIAGNOSTIC_METRICS",
    "KubernetesMetricEvidenceCollector",
    "KubernetesMetricTarget",
    "KubernetesMetricWindowEvidence",
]
