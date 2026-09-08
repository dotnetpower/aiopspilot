import { describe, expect, test, vi } from "vitest";
import { loadDashboardOverviewForMode } from "./dashboard.loading";
import { DASHBOARD_SAMPLE_DATA } from "./dashboard.sample";

describe("Dashboard sample mode", () => {
  test("returns the deterministic fixture without calling a live source", async () => {
    const client = {
      dashboardMetrics: vi.fn(),
      costGovernance: vi.fn(),
      panel: vi.fn(),
      autonomy: vi.fn(),
    };
    const publishBackbone = vi.fn();

    const result = await loadDashboardOverviewForMode("sample", client, publishBackbone);

    expect(result).toBe(DASHBOARD_SAMPLE_DATA);
    expect(publishBackbone).toHaveBeenCalledWith(DASHBOARD_SAMPLE_DATA);
    expect(client.dashboardMetrics).not.toHaveBeenCalled();
    expect(client.costGovernance).not.toHaveBeenCalled();
    expect(client.panel).not.toHaveBeenCalled();
    expect(client.autonomy).not.toHaveBeenCalled();
  });
});
