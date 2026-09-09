import { afterEach, describe, expect, test, vi } from "vitest";
import type { AuthContext } from "../auth";
import { requestTeamsA1Plan } from "./settings-runtime.command";

const auth: AuthContext = {
  devMode: false,
  account: null,
  getAuthorizationHeader: async () => "******",
  signIn: async () => undefined,
  signOut: async () => undefined,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Teams A1 protected plan command", () => {
  test("submits one no-authority environment-bound request", async () => {
    const requests: unknown[] = [];
    vi.stubGlobal("fetch", vi.fn(async (_url: string | URL, init?: RequestInit) => {
      requests.push(JSON.parse(String(init?.body)));
      return new Response(JSON.stringify({
        proposal_id: "operator-teams-a1",
        state: "plan-requested",
        environment: "dev",
        execution_authority: false,
      }), { status: 200 });
    }));

    const receipt = await requestTeamsA1Plan(
      auth,
      "http://127.0.0.1:8030",
      "dev",
      "teams-a1-plan-stable",
    );

    expect(receipt.executionAuthority).toBe(false);
    expect(requests).toEqual([{
      environment: "dev",
      idempotency_key: "teams-a1-plan-stable",
    }]);
  });

  test("rejects a response that claims execution authority", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      proposal_id: "operator-teams-a1",
      state: "plan-requested",
      environment: "dev",
      execution_authority: true,
    }), { status: 200 })));

    await expect(
      requestTeamsA1Plan(
        auth,
        "http://127.0.0.1:8030",
        "dev",
        "teams-a1-plan-stable",
      ),
    ).rejects.toThrow("receipt is invalid");
  });
});
