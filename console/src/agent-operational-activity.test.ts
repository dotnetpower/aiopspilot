import { describe, expect, it } from "vitest";
import { decodeAgentOperationalActivity } from "./agent-operational-activity";

const OBSERVATION = {
  type: "agent.operational-activity",
  schema_version: "1.1.0",
  activity_id: "observation:resource-health:campaign-1:completed",
  idempotency_key: "observation:resource-health:campaign-1:completed",
  kind: "observation",
  status: "completed",
  owner_agent: "Heimdall",
  producer: "observation-campaign-job",
  observation_domain: "resource-health",
  observed_at: "2026-08-14T00:00:00+00:00",
  source: "resource-health",
  freshness: "fresh",
  evidence_count: 2,
  duration_ms: 50,
  correlation_id: "campaign-1",
  reason_codes: [],
  execution_authority: false,
};

describe("agent operational activity v1.1", () => {
  it("accepts a bounded observation with matching ownership", () => {
    expect(decodeAgentOperationalActivity(OBSERVATION)).toMatchObject({
      kind: "observation",
      observation_domain: "resource-health",
      owner_agent: "Heimdall",
    });
  });

  it("rejects an observation whose domain owner is forged", () => {
    expect(decodeAgentOperationalActivity({ ...OBSERVATION, owner_agent: "Njord" })).toBeNull();
  });

  it("rejects observation reason text that can carry provider identifiers", () => {
    expect(decodeAgentOperationalActivity({
      ...OBSERVATION,
      status: "degraded",
      freshness: "unavailable",
      reason_codes: ["resource /subscriptions/example failed"],
    })).toBeNull();
  });

  it("normalizes a legacy payload without a domain", () => {
    const legacy = decodeAgentOperationalActivity({
      ...OBSERVATION,
      schema_version: "1.0.0",
      kind: "inventory.scan",
      owner_agent: "Huginn",
      producer: "inventory-sync-job",
      observation_domain: undefined,
    });

    expect(legacy?.observation_domain).toBeNull();
  });
});

const ASSURANCE_TWIN_POSTURE = {
  type: "agent.operational-activity",
  schema_version: "1.2.0",
  activity_id: "assurance-twin.change-review:Review_Key-1:completed",
  idempotency_key: "assurance-twin.change-review:Review_Key-1:completed",
  kind: "assurance-twin.posture",
  status: "completed",
  owner_agent: "Heimdall",
  producer: "assurance-twin",
  observation_domain: null,
  observed_at: "2026-08-14T00:00:00+00:00",
  source: "assurance-twin:review:owner/repo#1",
  freshness: "fresh",
  evidence_count: 1,
  duration_ms: null,
  correlation_id: "correlation-1",
  reason_codes: [],
  execution_authority: false,
};

describe("agent operational activity v1.2 assurance twin posture", () => {
  it("accepts the Heimdall-owned twin tip the Core runtime publishes", () => {
    expect(decodeAgentOperationalActivity(ASSURANCE_TWIN_POSTURE)).toMatchObject({
      kind: "assurance-twin.posture",
      producer: "assurance-twin",
      owner_agent: "Heimdall",
      schema_version: "1.2.0",
      execution_authority: false,
    });
  });

  it("accepts an explicit unavailable conflict tip with its reason code", () => {
    expect(decodeAgentOperationalActivity({
      ...ASSURANCE_TWIN_POSTURE,
      status: "failed",
      freshness: "unavailable",
      reason_codes: ["assurance_twin_review_key_conflict"],
    })).toMatchObject({ freshness: "unavailable", status: "failed" });
  });

  it("rejects a twin tip that claims an older schema version", () => {
    expect(decodeAgentOperationalActivity({
      ...ASSURANCE_TWIN_POSTURE,
      schema_version: "1.1.0",
    })).toBeNull();
  });

  it("rejects a twin tip owned by an agent other than Heimdall", () => {
    expect(decodeAgentOperationalActivity({
      ...ASSURANCE_TWIN_POSTURE,
      owner_agent: "Njord",
    })).toBeNull();
  });

  it("rejects the twin producer on any other activity kind", () => {
    expect(decodeAgentOperationalActivity({
      ...ASSURANCE_TWIN_POSTURE,
      kind: "current-state.read",
    })).toBeNull();
  });

  it("rejects a twin tip that smuggles an observation domain", () => {
    expect(decodeAgentOperationalActivity({
      ...ASSURANCE_TWIN_POSTURE,
      observation_domain: "resource-health",
    })).toBeNull();
  });

  it("rejects unbounded reason text on a twin tip", () => {
    expect(decodeAgentOperationalActivity({
      ...ASSURANCE_TWIN_POSTURE,
      reason_codes: ["resource /subscriptions/example conflicted"],
    })).toBeNull();
  });
});
