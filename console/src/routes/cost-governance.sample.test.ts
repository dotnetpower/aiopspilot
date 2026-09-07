import { describe, expect, test } from "vitest";
import { sampleCostGovernance } from "./cost-governance.sample";

describe("Cost Governance Sample projection", () => {
  test.each([
    "overview",
    "resource-efficiency",
    "optimization-cases",
    "outcomes",
  ] as const)("builds the %s surface without resource identity", (surface) => {
    const projection = sampleCostGovernance(surface);

    expect(projection.surface).toBe(surface);
    expect(projection.source_authority).toBe("synthetic-preview");
    expect(projection.items).not.toHaveLength(0);
    expect(projection.analytics?.recommendations.every(
      (recommendation) => recommendation.resource_ref === null,
    )).toBe(true);
  });
});
