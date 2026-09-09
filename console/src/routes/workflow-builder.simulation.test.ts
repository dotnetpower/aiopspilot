import { describe, expect, test } from "vitest";
import type { ProcessListResponse } from "./processes.model";
import {
  loadWorkflowBehaviorSimulation,
  simulationIsCurrent,
  simulateWorkflowBehavior,
  STRUCTURAL_VALIDATION_BOUNDARY,
} from "./workflow-builder.simulation";

function history(
  items: ProcessListResponse["items"],
  changes: Partial<ProcessListResponse> = {},
): ProcessListResponse {
  return {
    source: "postgres:process-runtime",
    synthetic: false,
    durable: true,
    principal_scoped: true,
    items,
    ...changes,
  };
}

function process(
  id: string,
  status: string,
  currentStep: string,
  target: string,
  updatedAt: string,
  workflowRef = "review-service",
) {
  return {
    id,
    workflow_ref: workflowRef,
    workflow_version: "1.0.0",
    status,
    current_step: currentStep,
    target_resource_id: target,
    updated_at: updatedAt,
    has_view: true,
  };
}

describe("workflow behavior simulation", () => {
  test("loads only the authenticated workflow-filtered Process projection", async () => {
    const calls: string[] = [];
    const result = await loadWorkflowBehaviorSimulation({
      panel: async (path: string) => {
        calls.push(path);
        return history([
          process(
            "process-1",
            "completed",
            "done",
            "service-a",
            "2026-09-01T00:00:00Z",
            "review service",
          ),
        ]);
      },
    } as never, "review service", "1.0.0");

    expect(calls).toEqual(["/views/process?workflow_ref=review+service"]);
    expect(result.status).toBe("ready");
  });

  test("summarizes exact principal-scoped durable historical behavior", () => {
    const result = simulateWorkflowBehavior("review-service", "1.0.0", history([
      process("process-1", "completed", "notify", "service-a", "2026-09-01T00:00:00Z"),
      process("process-2", "completed", "notify", "service-b", "2026-09-02T00:00:00Z"),
      process("process-3", "waiting", "approve", "service-a", "2026-09-03T00:00:00Z"),
      process("other", "completed", "done", "service-c", "2026-09-04T00:00:00Z", "other"),
    ]));

    expect(result).toMatchObject({
      status: "ready",
      basis: "principal_scoped_durable_process_history",
      workflow_ref: "review-service",
      workflow_version: "1.0.0",
      sample_count: 3,
      target_refs: ["service-a", "service-b"],
      mutation_preview: false,
      execution_authority: false,
      unavailable_reason: null,
    });
    expect(result.observations).toEqual([
      {
        status: "completed",
        current_step: "notify",
        count: 2,
        process_refs: ["/processes/process-2", "/processes/process-1"],
      },
      {
        status: "waiting",
        current_step: "approve",
        count: 1,
        process_refs: ["/processes/process-3"],
      },
    ]);
  });

  test.each([
    [history([], { synthetic: true }), "synthetic_history_not_eligible"],
    [history([], { durable: false }), "durable_history_unavailable"],
    [history([process("other", "completed", "done", "service-a", "2026-09-01T00:00:00Z", "other")]), "no_matching_historical_processes"],
  ])("fails closed when historical evidence is not eligible", (payload, reason) => {
    const result = simulateWorkflowBehavior("review-service", "1.0.0", payload);

    expect(result.status).toBe("unavailable");
    expect(result.unavailable_reason).toBe(reason);
    expect(result.target_refs).toEqual([]);
    expect(result.observations).toEqual([]);
  });

  test("keeps structural validation separate from simulation and mutation preview", () => {
    expect(STRUCTURAL_VALIDATION_BOUNDARY).toEqual({
      scope: "schema_and_catalog_only",
      executes: false,
      simulates: false,
      mutation_preview: false,
    });
    expect(simulateWorkflowBehavior(
      "review-service",
      "1.0.0",
      history([process("process-1", "completed", "done", "service-a", "2026-09-01T00:00:00Z")]),
    ).mutation_preview).toBe(false);
  });

  test("never reuses a prior validation result after the draft changes", () => {
    expect(simulationIsCurrent(true, "draft-a", "draft-a")).toBe(true);
    expect(simulationIsCurrent(true, "draft-a", "draft-b")).toBe(false);
    expect(simulationIsCurrent(false, "draft-a", "draft-a")).toBe(false);
    expect(simulationIsCurrent(true, null, "draft-a")).toBe(false);
  });

  test("does not mix observations from a different workflow version", () => {
    const result = simulateWorkflowBehavior("review-service", "2.0.0", history([
      process("old", "completed", "done", "service-a", "2026-09-01T00:00:00Z"),
    ]));

    expect(result.status).toBe("unavailable");
    expect(result.unavailable_reason).toBe("no_matching_historical_processes");
  });

  test("limits evidence to the newest 20 matching processes", () => {
    const items = Array.from({ length: 25 }, (_, index) =>
      process(
        `process-${index}`,
        "completed",
        "done",
        `service-${index}`,
        `2026-09-${String(index + 1).padStart(2, "0")}T00:00:00Z`,
      )
    );

    const result = simulateWorkflowBehavior("review-service", "1.0.0", history(items));

    expect(result.sample_count).toBe(20);
    expect(result.evidence_links).toHaveLength(20);
    expect(result.evidence_links[0]).toBe("/processes/process-24");
  });
});
