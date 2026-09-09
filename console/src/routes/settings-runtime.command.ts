import type { AuthContext } from "../auth";
import { GovernedCommandError, putGovernedJson } from "../governed-command";
import {
  decodeRuntimeSettings,
  type RuntimeSettingsView,
  type RuntimeSettingValue,
} from "./settings-runtime.model";

export { GovernedCommandError as RuntimeSettingsCommandError };

export interface TeamsA1PlanReceipt {
  readonly proposalId: string;
  readonly state: "plan-requested";
  readonly environment: "dev" | "staging" | "prod";
  readonly executionAuthority: false;
}

export async function saveRuntimeSettings(
  auth: AuthContext,
  operatorApiBaseUrl: string,
  changes: Readonly<Record<string, RuntimeSettingValue | null>>,
  expectedRevision: number,
): Promise<RuntimeSettingsView> {
  return decodeRuntimeSettings(
    await putGovernedJson(auth, operatorApiBaseUrl, "/runtime/settings", {
      changes: { ...changes },
      expected_revision: expectedRevision,
    }),
  );
}

export async function requestTeamsA1Plan(
  auth: AuthContext,
  operatorApiBaseUrl: string,
  environment: "dev" | "staging" | "prod",
  idempotencyKey: string,
): Promise<TeamsA1PlanReceipt> {
  const value = await putGovernedJson(
    auth,
    operatorApiBaseUrl,
    "/runtime/integrations/teams-a1/plan",
    {
      environment,
      idempotency_key: idempotencyKey,
    },
    "POST",
  );
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Teams A1 plan receipt MUST be an object");
  }
  const item = value as Record<string, unknown>;
  if (
    typeof item["proposal_id"] !== "string"
    || !item["proposal_id"]
    || item["state"] !== "plan-requested"
    || item["environment"] !== environment
    || item["execution_authority"] !== false
  ) {
    throw new Error("Teams A1 plan receipt is invalid");
  }
  return {
    proposalId: item["proposal_id"],
    state: "plan-requested",
    environment,
    executionAuthority: false,
  };
}
