const SAMPLE_AT = "2026-09-01T09:00:00Z";

export function sampleOnboarding() {
  return {
    probe_mode: "configured",
    ready: false,
    blocked: true,
    missing_resources: ["sample-private-endpoint"],
    missing_role_assignments: [["sample-reader", "Reader", "sample-scope"]],
    present_resource_count: 18,
    present_role_count: 7,
    error: null,
  };
}

export function sampleDetectionReadiness() {
  return {
    source: "synthetic-preview",
    observed_at: SAMPLE_AT,
    target_count: 2,
    counts: { ready: 1, partial: 1, blocked: 0, stale: 0, unauthorized: 0, unknown: 0 },
    targets: [
      {
        resource_ref: "sample-cluster-1",
        generated_at: SAMPLE_AT,
        decision: "ready",
        authority_ceiling: "shadow",
        observations: [
          { dimension: "discovered", status: "passed" },
          { dimension: "collector_configured", status: "passed" },
        ],
        missing_dimensions: [],
        stale_dimensions: [],
      },
      {
        resource_ref: "sample-cluster-2",
        generated_at: SAMPLE_AT,
        decision: "partial",
        authority_ceiling: "shadow",
        observations: [{ dimension: "discovered", status: "passed" }],
        missing_dimensions: ["collector_configured"],
        stale_dimensions: [],
      },
    ],
    lifecycle: {
      source: "synthetic-preview",
      observed_at: SAMPLE_AT,
      target_count: 0,
      assessment_count: 0,
      evidence_counts: { complete: 0, incomplete: 0, conflicting: 0, missed: 0 },
      targets: [],
    },
    pod_lifecycle: {
      schema_version: 1,
      status: "unavailable",
      unavailable_reason: "sample_preview_omits_pod_lifecycle",
      cause_claim_supported: false,
      execution_authority: false,
    },
  };
}

export function sampleConfigurationBaselines() {
  return {
    baseline: {
      version: "sample-v3",
      scope: "sample-scope",
      created_at: SAMPLE_AT,
      document_name: "sample-baseline.yaml",
      lifecycle: "active-pinned",
      resource_count: 18,
      topology_count: 27,
      unknown_count: 2,
    },
    versions: [
      {
        version: "sample-v3",
        status: "active",
        created_at: SAMPLE_AT,
        resource_count: 18,
        topology_count: 27,
        unknown_count: 2,
        comparison: {
          baseline_version: "sample-v2",
          verdict: "attention",
          finding_count: 2,
        },
      },
    ],
    drift: { verdict: "attention", observed_at: SAMPLE_AT, finding_count: 2 },
    knowledge: {
      status: "cited",
      citation_count: 2,
      citations: ["sample-knowledge-1", "sample-knowledge-2"],
    },
    safety: {
      mutation_count: 0,
      approval_request_count: 0,
      mitigation_execution_count: 0,
      unsupported_claim_count: 0,
    },
    performance: { total_ms: 84, observation_ms: 62, knowledge_ms: 12 },
    review: {
      configured: true,
      state: "collecting",
      completed_runs: 2,
      required_runs: 3,
      failed_attempts: 0,
    },
  };
}
