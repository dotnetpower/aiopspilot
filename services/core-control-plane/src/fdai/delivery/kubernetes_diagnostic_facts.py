"""Extract bounded content-safe Kubernetes diagnostic facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Final, cast

_MAX_CONDITIONS: Final[int] = 128
_MAX_CONTAINERS: Final[int] = 128
_MAX_SCHEDULING_ITEMS: Final[int] = 128
_MAX_TEXT: Final[int] = 512
_CONDITION_TYPES: Final[Mapping[str, frozenset[str]]] = {
    "kubernetes.node": frozenset(
        {"DiskPressure", "MemoryPressure", "NetworkUnavailable", "PIDPressure", "Ready"}
    ),
    "kubernetes.pod": frozenset(
        {
            "ContainersReady",
            "Initialized",
            "PodReadyToStartContainers",
            "PodScheduled",
            "Ready",
        }
    ),
    "kubernetes.deployment": frozenset({"Available", "Progressing", "ReplicaFailure"}),
    "kubernetes.daemon-set": frozenset({"Available", "Progressing"}),
    "kubernetes.stateful-set": frozenset({"Available", "Progressing"}),
    "kubernetes.job": frozenset({"Complete", "Failed", "Suspended"}),
}
_STATUS_COUNT_FIELDS: Final[Mapping[str, tuple[str, ...]]] = {
    "kubernetes.daemon-set": (
        "currentNumberScheduled",
        "desiredNumberScheduled",
        "numberAvailable",
        "numberMisscheduled",
        "numberReady",
        "numberUnavailable",
        "updatedNumberScheduled",
    ),
    "kubernetes.stateful-set": (
        "availableReplicas",
        "currentReplicas",
        "readyReplicas",
        "replicas",
        "updatedReplicas",
    ),
    "kubernetes.job": ("active", "failed", "ready", "succeeded", "terminating"),
}


def diagnostic_properties(
    *,
    resource_type: str,
    spec: Mapping[str, Any] | None,
    status: Mapping[str, Any] | None,
) -> dict[str, object]:
    """Return allowlisted diagnostic facts without raw provider-controlled text."""

    props: dict[str, object] = {}
    if status is not None:
        conditions = _conditions(status.get("conditions"), resource_type=resource_type)
        if conditions:
            props["diagnostic_conditions"] = conditions
        counts = _status_counts(status, resource_type=resource_type)
        if counts:
            props["status_counts"] = counts
        qos_class = _optional_text(status.get("qosClass"))
        if resource_type == "kubernetes.pod" and qos_class is not None:
            props["qos_class"] = qos_class
        for source_name, prefix in (
            ("initContainerStatuses", "init_container"),
            ("ephemeralContainerStatuses", "ephemeral_container"),
        ):
            summary = _container_status_summary(status.get(source_name))
            for key, value in summary.items():
                props[f"{prefix}_{key}"] = value
    if spec is not None and resource_type == "kubernetes.pod":
        props.update(_pod_spec_properties(spec))
    return props


def _conditions(value: object, *, resource_type: str) -> tuple[dict[str, object], ...]:
    allowed = _CONDITION_TYPES.get(resource_type)
    if allowed is None or value is None:
        return ()
    rows = _mapping_sequence(value, field="conditions", limit=_MAX_CONDITIONS)
    selected: dict[str, dict[str, object]] = {}
    for row in rows:
        condition_type = _required_text(row.get("type"), field="condition.type")
        if condition_type not in allowed:
            continue
        status = _required_text(row.get("status"), field="condition.status")
        if status not in {"True", "False", "Unknown"}:
            raise ValueError("Kubernetes diagnostic condition status is invalid")
        condition: dict[str, object] = {"status": status, "type": condition_type}
        reason = _optional_text(row.get("reason"))
        if reason is not None:
            condition["reason"] = reason
        transition = _optional_time(row.get("lastTransitionTime"))
        if transition is not None:
            condition["last_transition_time"] = transition
        if condition_type in selected:
            raise ValueError("Kubernetes diagnostic condition type is duplicated")
        selected[condition_type] = condition
    return tuple(selected[key] for key in sorted(selected))


def _status_counts(status: Mapping[str, Any], *, resource_type: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for field in _STATUS_COUNT_FIELDS.get(resource_type, ()):
        value = status.get(field)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"Kubernetes status {field} MUST be a non-negative integer")
        counts[_snake_case(field)] = value
    return counts


def _pod_spec_properties(spec: Mapping[str, Any]) -> dict[str, object]:
    props: dict[str, object] = {}
    for source_name, output_name in (
        ("priorityClassName", "priority_class_name"),
        ("restartPolicy", "restart_policy"),
        ("schedulerName", "scheduler_name"),
        ("serviceAccountName", "service_account_name"),
    ):
        value = _optional_text(spec.get(source_name))
        if value is not None:
            props[output_name] = value
    node_selector = _string_mapping(spec.get("nodeSelector"))
    if node_selector:
        props["node_selector"] = node_selector
    tolerations = _tolerations(spec.get("tolerations"))
    if tolerations:
        props["tolerations"] = tolerations
    affinity = spec.get("affinity")
    if affinity is not None:
        if not isinstance(affinity, Mapping):
            raise ValueError("Kubernetes Pod affinity MUST be an object")
        kinds = tuple(
            key
            for key in ("nodeAffinity", "podAffinity", "podAntiAffinity")
            if isinstance(affinity.get(key), Mapping)
        )
        if kinds:
            props["affinity_kinds"] = kinds
    containers = _mapping_sequence(
        spec.get("containers"),
        field="containers",
        limit=_MAX_CONTAINERS,
        allow_none=True,
    )
    resource_specs = _container_resource_specs(containers)
    if resource_specs:
        props["container_resources"] = resource_specs
    probe_kinds = _probe_kinds(containers)
    if probe_kinds:
        props["probe_kinds"] = probe_kinds
    claims = _pvc_claim_names(spec.get("volumes"))
    if claims:
        props["pvc_claim_names"] = claims
    return props


def _container_resource_specs(
    containers: tuple[Mapping[str, Any], ...],
) -> tuple[dict[str, object], ...]:
    specs: list[dict[str, object]] = []
    for container in containers:
        name = _required_text(container.get("name"), field="container.name")
        resources = container.get("resources")
        if resources is None:
            continue
        if not isinstance(resources, Mapping):
            raise ValueError("Kubernetes container resources MUST be an object")
        requests = _quantity_mapping(resources.get("requests"))
        limits = _quantity_mapping(resources.get("limits"))
        if requests or limits:
            specs.append({"container_name": name, "limits": limits, "requests": requests})
    return tuple(sorted(specs, key=lambda item: str(item["container_name"])))


def _probe_kinds(containers: tuple[Mapping[str, Any], ...]) -> tuple[dict[str, str], ...]:
    probes: list[dict[str, str]] = []
    for container in containers:
        name = _required_text(container.get("name"), field="container.name")
        for field, kind in (
            ("livenessProbe", "liveness"),
            ("readinessProbe", "readiness"),
            ("startupProbe", "startup"),
        ):
            value = container.get(field)
            if value is not None and not isinstance(value, Mapping):
                raise ValueError(f"Kubernetes container {field} MUST be an object")
            if isinstance(value, Mapping):
                probes.append({"container_name": name, "probe_kind": kind})
    return tuple(sorted(probes, key=lambda item: (item["container_name"], item["probe_kind"])))


def _container_status_summary(value: object) -> dict[str, object]:
    rows = _mapping_sequence(
        value,
        field="container statuses",
        limit=_MAX_CONTAINERS,
        allow_none=True,
    )
    if not rows:
        return {}
    ready_count = 0
    restart_count = 0
    waiting_reasons: set[str] = set()
    termination_reasons: set[str] = set()
    for row in rows:
        ready = row.get("ready")
        if not isinstance(ready, bool):
            raise ValueError("Kubernetes diagnostic container ready MUST be boolean")
        ready_count += int(ready)
        restart = row.get("restartCount")
        if isinstance(restart, bool) or not isinstance(restart, int) or restart < 0:
            raise ValueError("Kubernetes diagnostic restartCount MUST be non-negative")
        restart_count += restart
        for state_key in ("state", "lastState"):
            state = row.get(state_key)
            if state is None:
                continue
            if not isinstance(state, Mapping):
                raise ValueError("Kubernetes diagnostic container state MUST be an object")
            waiting = state.get("waiting")
            terminated = state.get("terminated")
            if isinstance(waiting, Mapping):
                reason = _optional_text(waiting.get("reason"))
                if reason is not None:
                    waiting_reasons.add(reason)
            if isinstance(terminated, Mapping):
                reason = _optional_text(terminated.get("reason"))
                if reason is not None:
                    termination_reasons.add(reason)
    summary: dict[str, object] = {
        "count": len(rows),
        "ready_count": ready_count,
        "restart_count": restart_count,
    }
    if waiting_reasons:
        summary["waiting_reasons"] = tuple(sorted(waiting_reasons))
    if termination_reasons:
        summary["termination_reasons"] = tuple(sorted(termination_reasons))
    return summary


def _tolerations(value: object) -> tuple[dict[str, str], ...]:
    rows = _mapping_sequence(
        value,
        field="tolerations",
        limit=_MAX_SCHEDULING_ITEMS,
        allow_none=True,
    )
    output: list[dict[str, str]] = []
    for row in rows:
        item = {
            key: text
            for key in ("effect", "key", "operator", "value")
            if (text := _optional_text(row.get(key))) is not None
        }
        if item:
            output.append(item)
    return tuple(sorted(output, key=lambda item: tuple(sorted(item.items()))))


def _pvc_claim_names(value: object) -> tuple[str, ...]:
    rows = _mapping_sequence(
        value,
        field="volumes",
        limit=_MAX_SCHEDULING_ITEMS,
        allow_none=True,
    )
    claims: set[str] = set()
    for row in rows:
        claim = row.get("persistentVolumeClaim")
        if claim is None:
            continue
        if not isinstance(claim, Mapping):
            raise ValueError("Kubernetes persistentVolumeClaim MUST be an object")
        claims.add(_required_text(claim.get("claimName"), field="persistentVolumeClaim.claimName"))
    return tuple(sorted(claims))


def _quantity_mapping(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or len(value) > 32:
        raise ValueError("Kubernetes resource quantities MUST be a bounded object")
    allowed = {"cpu", "ephemeral-storage", "memory"}
    output: dict[str, str] = {}
    for key, raw in value.items():
        if key not in allowed:
            continue
        output[str(key)] = _required_text(raw, field=f"resource quantity {key}")
    return dict(sorted(output.items()))


def _string_mapping(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or len(value) > _MAX_SCHEDULING_ITEMS:
        raise ValueError("Kubernetes diagnostic string mapping MUST be bounded")
    return dict(
        sorted(
            (
                _required_text(key, field="mapping key"),
                _required_text(item, field="mapping value"),
            )
            for key, item in value.items()
        )
    )


def _mapping_sequence(
    value: object,
    *,
    field: str,
    limit: int,
    allow_none: bool = False,
) -> tuple[Mapping[str, Any], ...]:
    if value is None and allow_none:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) > limit:
        raise ValueError(f"Kubernetes {field} MUST be a bounded array")
    if any(not isinstance(item, Mapping) for item in value):
        raise ValueError(f"Kubernetes {field} entries MUST be objects")
    return cast(tuple[Mapping[str, Any], ...], tuple(value))


def _required_text(value: object, *, field: str) -> str:
    text = _optional_text(value)
    if text is None:
        raise ValueError(f"Kubernetes {field} MUST be bounded non-empty text")
    return text


def _optional_text(value: object) -> str | None:
    return (
        value.strip()
        if isinstance(value, str) and value.strip() and len(value) <= _MAX_TEXT
        else None
    )


def _optional_time(value: object) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Kubernetes diagnostic timestamp is malformed") from exc
    if parsed.tzinfo is None:
        raise ValueError("Kubernetes diagnostic timestamp MUST include timezone")
    return parsed.isoformat()


def _snake_case(value: str) -> str:
    output: list[str] = []
    for character in value:
        if character.isupper() and output:
            output.append("_")
        output.append(character.casefold())
    return "".join(output)


__all__ = ["diagnostic_properties"]
