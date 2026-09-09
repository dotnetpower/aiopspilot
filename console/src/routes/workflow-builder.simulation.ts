import type { OperatorApiClient } from "../api";
import { decodeProcessList, processHref, type ProcessListResponse } from "./processes.model";

const MAX_HISTORY_SAMPLES = 20;

export const STRUCTURAL_VALIDATION_BOUNDARY = {
  scope: "schema_and_catalog_only",
  executes: false,
  simulates: false,
  mutation_preview: false,
} as const;

export interface WorkflowBehaviorObservation {
  readonly status: string;
  readonly current_step: string;
  readonly count: number;
  readonly process_refs: readonly string[];
}

export interface WorkflowBehaviorSimulation {
  readonly status: "ready" | "unavailable";
  readonly basis: "principal_scoped_durable_process_history";
  readonly workflow_ref: string;
  readonly workflow_version: string;
  readonly sample_count: number;
  readonly target_refs: readonly string[];
  readonly observations: readonly WorkflowBehaviorObservation[];
  readonly evidence_links: readonly string[];
  readonly mutation_preview: false;
  readonly execution_authority: false;
  readonly limitations: readonly string[];
  readonly unavailable_reason: string | null;
}

export function simulationIsCurrent(
  validationPassed: boolean,
  validatedDraftIdentity: string | null,
  draftIdentity: string,
): boolean {
  return validationPassed
    && validatedDraftIdentity !== null
    && validatedDraftIdentity === draftIdentity;
}

export async function loadWorkflowBehaviorSimulation(
  client: Pick<OperatorApiClient, "panel">,
  workflowRef: string,
  workflowVersion: string,
): Promise<WorkflowBehaviorSimulation> {
  const query = new URLSearchParams({ workflow_ref: workflowRef });
  const payload = await client.panel<unknown>(`/views/process?${query.toString()}`);
  return simulateWorkflowBehavior(workflowRef, workflowVersion, decodeProcessList(payload));
}

export function simulateWorkflowBehavior(
  workflowRef: string,
  workflowVersion: string,
  history: ProcessListResponse,
): WorkflowBehaviorSimulation {
  const normalized = workflowRef.trim();
  if (!normalized) throw new Error("workflow_ref MUST be non-empty");
  const normalizedVersion = workflowVersion.trim();
  if (!normalizedVersion) throw new Error("workflow_version MUST be non-empty");
  const base = {
    basis: "principal_scoped_durable_process_history" as const,
    workflow_ref: normalized,
    workflow_version: normalizedVersion,
    mutation_preview: false as const,
    execution_authority: false as const,
    limitations: [
      "historical_observations_only",
      "workflow_state_only",
      "no_substrate_mutation_prediction",
      "no_execution_or_promotion_authority",
    ],
  };
  if (history.synthetic !== false) {
    return unavailable(base, "synthetic_history_not_eligible");
  }
  if (history.durable !== true) {
    return unavailable(base, "durable_history_unavailable");
  }

  const samples = history.items
    .filter((item) =>
      item.workflow_ref === normalized && item.workflow_version === normalizedVersion
    )
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
    .slice(0, MAX_HISTORY_SAMPLES);
  if (samples.length === 0) {
    return unavailable(base, "no_matching_historical_processes");
  }

  const groups = new Map<string, { status: string; currentStep: string; ids: string[] }>();
  for (const sample of samples) {
    const key = `${sample.status}\u0000${sample.current_step}`;
    const group = groups.get(key) ?? {
      status: sample.status,
      currentStep: sample.current_step,
      ids: [],
    };
    group.ids.push(sample.id);
    groups.set(key, group);
  }
  const observations = [...groups.values()]
    .map((group) => ({
      status: group.status,
      current_step: group.currentStep,
      count: group.ids.length,
      process_refs: group.ids.map(processHref),
    }))
    .sort((left, right) =>
      right.count - left.count
      || left.status.localeCompare(right.status)
      || left.current_step.localeCompare(right.current_step)
    );

  return {
    ...base,
    status: "ready",
    sample_count: samples.length,
    target_refs: [...new Set(samples.map((item) => item.target_resource_id))].sort(),
    observations,
    evidence_links: samples.map((item) => processHref(item.id)),
    unavailable_reason: null,
  };
}

function unavailable(
  base: Pick<
    WorkflowBehaviorSimulation,
    | "basis"
    | "workflow_ref"
    | "workflow_version"
    | "mutation_preview"
    | "execution_authority"
    | "limitations"
  >,
  reason: string,
): WorkflowBehaviorSimulation {
  return {
    ...base,
    status: "unavailable",
    sample_count: 0,
    target_refs: [],
    observations: [],
    evidence_links: [],
    unavailable_reason: reason,
  };
}
