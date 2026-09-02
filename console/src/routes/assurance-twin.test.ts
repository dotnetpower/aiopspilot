import { describe, expect, it, vi } from "vitest";
import { OperatorApiError } from "../api";
import type { OperatorApiClient } from "../api";
import {
  buildAssuranceTwinViewSnapshot,
  loadAssuranceTwinReviewDetail,
  loadAssuranceTwinState,
} from "./assurance-twin";

const finding = {
  rule_id: "r-1",
  resource_type: "compute.vm",
  resource_ref: "vm-a",
  severity: "high",
  reason: "reason",
  evidence_refs: [],
};

const report = {
  scope: "sub/00000000-0000-0000-0000-000000000001",
  generated_at: "2026-07-07T00:00:00Z",
  mode: "shadow",
  verdict: "blocked",
  blocks_action: false,
  resource_count: 1,
  rule_count: 1,
  highest_severity: "high",
  severity_counts: { low: 0, medium: 0, high: 1, critical: 0 },
  finding_count: 1,
  findings: [finding],
  freshness: "fresh",
  reason_codes: [],
};

const postureResponse = () => ({
  surface: "assurance-twin-posture",
  available: true,
  source: "postgresql:state_kv:assurance-twin-posture",
  reports: [report],
});

const reviewSummary = {
  review_key: "k-1",
  pr_ref: "owner/repo#1",
  generated_at: "2026-07-07T00:00:00Z",
  mode: "shadow",
  verdict: "needs_review",
  finding_count: 1,
  freshness: "fresh",
  reason_codes: [],
};

const reviewsResponse = () => ({
  surface: "assurance-twin-review",
  available: true,
  source: "postgresql:state_kv:assurance-twin-review",
  reviews: [reviewSummary],
});

const reviewDetailResponse = () => ({ ...reviewSummary, findings: [finding] });

function panelClient(
  handler: (path: string) => Promise<unknown>,
): Pick<OperatorApiClient, "panel"> {
  return {
    async panel<T>(path: string): Promise<T> {
      return await handler(path) as T;
    },
  };
}

describe("assurance twin decoder", () => {
  it("decodes a posture report and review list into one ready state", async () => {
    const handler = vi.fn(async (path: string) => {
      if (path === "/assurance-twin/posture") return postureResponse();
      if (path === "/assurance-twin/reviews") return reviewsResponse();
      throw new Error(`unexpected path ${path}`);
    });
    const state = await loadAssuranceTwinState(panelClient(handler));
    expect(state.status).toBe("ready");
    if (state.status !== "ready") throw new Error("expected ready state");
    expect(state.data.posture.reports[0]?.verdict).toBe("blocked");
    expect(state.data.reviews.reviews[0]?.review_key).toBe("k-1");

    const snapshot = buildAssuranceTwinViewSnapshot(state.data);
    expect(snapshot).toMatchObject({
      routeId: "assurance-twin",
      facts: expect.arrayContaining([
        expect.objectContaining({ key: "verdict", value: "blocked" }),
      ]),
    });
  });

  it("classifies an unavailable Operator API as unavailable, not an error", async () => {
    const handler = vi.fn(async () => {
      throw new OperatorApiError(503, "unavailable");
    });
    await expect(loadAssuranceTwinState(panelClient(handler))).resolves.toMatchObject({
      status: "unavailable",
    });
  });

  it("rejects a posture report with an incomplete severity_counts shape", async () => {
    const handler = vi.fn(async (path: string) => {
      if (path === "/assurance-twin/posture") {
        return {
          ...postureResponse(),
          reports: [{ ...report, severity_counts: { low: 0 } }],
        };
      }
      return reviewsResponse();
    });
    await expect(loadAssuranceTwinState(panelClient(handler))).resolves.toMatchObject({
      status: "error",
    });
  });

  it("rejects a posture report whose finding_count does not match its findings", async () => {
    const handler = vi.fn(async (path: string) => {
      if (path === "/assurance-twin/posture") {
        return { ...postureResponse(), reports: [{ ...report, finding_count: 2 }] };
      }
      return reviewsResponse();
    });
    await expect(loadAssuranceTwinState(panelClient(handler))).resolves.toMatchObject({
      status: "error",
    });
  });

  it("decodes one review detail with its finding evidence", async () => {
    const handler = vi.fn(async (path: string) => {
      expect(path).toBe("/assurance-twin/reviews/k-1");
      return reviewDetailResponse();
    });
    const state = await loadAssuranceTwinReviewDetail(panelClient(handler), "k-1");
    expect(state.status).toBe("ready");
    if (state.status !== "ready") throw new Error("expected ready state");
    expect(state.data.findings[0]?.rule_id).toBe("r-1");
  });

  it("classifies a not-found review detail as unavailable", async () => {
    const handler = vi.fn(async () => {
      throw new OperatorApiError(404, "not found");
    });
    await expect(
      loadAssuranceTwinReviewDetail(panelClient(handler), "missing"),
    ).resolves.toMatchObject({ status: "unavailable" });
  });
});
