from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW = (_ROOT / ".github" / "workflows" / "operational-instance-certification.yml").read_text(
    encoding="utf-8"
)


def test_oi12_workflow_binds_exact_source_and_required_ci() -> None:
    for value in (
        "commit_sha",
        "request_id",
        "window_seconds",
        "Verify protected workflow source",
        "Verify exact source and required CI",
        'select(.name == "required" and .conclusion == "success")',
        "bind_core_runtime_image.sh",
    ):
        assert value in _WORKFLOW


def test_oi12_workflow_refreshes_inventory_before_seven_axis_measurement() -> None:
    refresh = _WORKFLOW.index("- name: Refresh authoritative inventory with exact runtime")
    certify = _WORKFLOW.index("- name: Run protected seven-axis certification")
    assert refresh < certify
    assert '--image "$TF_VAR_core_image"' in _WORKFLOW
    assert "--command fdai-operational-instance-certification" in _WORKFLOW
    assert '--args protected "$CERTIFICATION_REQUEST_ID" "$TARGET_COMMIT_SHA"' in _WORKFLOW
    assert "--request-id" not in _WORKFLOW
    assert "authoritative inventory refresh exceeded its 1200-second deadline" in _WORKFLOW


def test_oi12_workflow_retains_only_sanitized_no_authority_evidence() -> None:
    assert _WORKFLOW.count("observation_authority") >= 3
    assert _WORKFLOW.count("mutation_authority") >= 3
    assert _WORKFLOW.count("execution_authority") >= 3
    assert "operational-instance-certification-${{ inputs.request_id }}" in _WORKFLOW
    assert "retention-days: 90" in _WORKFLOW
    assert "SERVICE_DEPLOY_TFVARS_JSON" not in _WORKFLOW
