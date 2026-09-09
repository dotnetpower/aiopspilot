"""Kubernetes diagnostic fact extraction tests."""

from __future__ import annotations

import pytest
from fdai.delivery.kubernetes_diagnostic_facts import diagnostic_properties


def test_collects_node_pressure_and_transition_times_without_messages() -> None:
    props = diagnostic_properties(
        resource_type="kubernetes.node",
        spec=None,
        status={
            "conditions": [
                {
                    "type": "MemoryPressure",
                    "status": "True",
                    "reason": "KubeletHasInsufficientMemory",
                    "message": "provider-controlled text",
                    "lastTransitionTime": "2026-09-10T00:00:00Z",
                },
                {"type": "Ready", "status": "False", "reason": "KubeletNotReady"},
            ]
        },
    )

    assert props["diagnostic_conditions"] == (
        {
            "type": "MemoryPressure",
            "status": "True",
            "reason": "KubeletHasInsufficientMemory",
            "last_transition_time": "2026-09-10T00:00:00+00:00",
        },
        {"type": "Ready", "status": "False", "reason": "KubeletNotReady"},
    )
    assert "message" not in str(props)


def test_collects_pod_scheduling_resources_probes_and_container_groups() -> None:
    props = diagnostic_properties(
        resource_type="kubernetes.pod",
        spec={
            "priorityClassName": "system-cluster-critical",
            "restartPolicy": "Always",
            "schedulerName": "default-scheduler",
            "serviceAccountName": "workload",
            "nodeSelector": {"kubernetes.io/os": "linux"},
            "tolerations": [{"key": "critical", "operator": "Exists", "effect": "NoSchedule"}],
            "affinity": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {}}},
            "containers": [
                {
                    "name": "api",
                    "livenessProbe": {"httpGet": {"path": "/health"}},
                    "readinessProbe": {"httpGet": {"path": "/ready"}},
                    "resources": {
                        "requests": {"cpu": "250m", "memory": "128Mi"},
                        "limits": {"cpu": "1", "memory": "512Mi"},
                    },
                }
            ],
            "volumes": [{"persistentVolumeClaim": {"claimName": "data"}}],
        },
        status={
            "qosClass": "Burstable",
            "conditions": [
                {
                    "type": "PodScheduled",
                    "status": "False",
                    "reason": "Unschedulable",
                    "lastTransitionTime": "2026-09-10T00:00:00Z",
                }
            ],
            "initContainerStatuses": [
                {
                    "name": "migrate",
                    "ready": False,
                    "restartCount": 2,
                    "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                }
            ],
        },
    )

    assert props["qos_class"] == "Burstable"
    assert props["pvc_claim_names"] == ("data",)
    assert props["probe_kinds"] == (
        {"container_name": "api", "probe_kind": "liveness"},
        {"container_name": "api", "probe_kind": "readiness"},
    )
    assert props["container_resources"] == (
        {
            "container_name": "api",
            "limits": {"cpu": "1", "memory": "512Mi"},
            "requests": {"cpu": "250m", "memory": "128Mi"},
        },
    )
    assert props["init_container_restart_count"] == 2
    assert props["init_container_waiting_reasons"] == ("CrashLoopBackOff",)


def test_rejects_duplicate_condition_types() -> None:
    with pytest.raises(ValueError, match="condition type is duplicated"):
        diagnostic_properties(
            resource_type="kubernetes.node",
            spec=None,
            status={
                "conditions": [
                    {"type": "Ready", "status": "True"},
                    {"type": "Ready", "status": "False"},
                ]
            },
        )


def test_collects_workload_specific_status_counts() -> None:
    props = diagnostic_properties(
        resource_type="kubernetes.daemon-set",
        spec={},
        status={
            "desiredNumberScheduled": 3,
            "numberReady": 2,
            "numberUnavailable": 1,
        },
    )

    assert props["status_counts"] == {
        "desired_number_scheduled": 3,
        "number_ready": 2,
        "number_unavailable": 1,
    }
