import { createHash, randomUUID } from "node:crypto";

import { expect, test } from "@playwright/test";

import { restoreBrowserEntraSessionStorage } from "./browser-entra-state";

const LOCAL_CLI_AUTH = process.env.FDAI_E2E_LOCAL_CLI_AUTH === "1";
const AUTHENTICATED_STACK = Boolean(
  process.env.FDAI_E2E_BEARER ||
    (process.env.FDAI_E2E_BASE_URL && (process.env.FDAI_E2E_STORAGE_STATE || LOCAL_CLI_AUTH)),
);
const PROMPT = "배포된 llm 모델이 뭐야";

test("deployed LLM collection reaches verified inventory without identity clarification", async ({
  page,
}) => {
  test.skip(!AUTHENTICATED_STACK, "requires an authenticated Console stack");
  test.setTimeout(120_000);
  if (!LOCAL_CLI_AUTH && !process.env.FDAI_E2E_BEARER) {
    await restoreBrowserEntraSessionStorage(page);
  }
  await page.goto("/overview", { waitUntil: "domcontentloaded", timeout: 30_000 });
  await expect(page.locator(".shell")).toBeVisible({ timeout: 30_000 });
  const testBearer = process.env.FDAI_E2E_BEARER;
  await page.route("**/chat/stream", async (route) => {
    expect(new URL(route.request().url()).port).not.toBe("8010");
    const authorization = route.request().headers()["authorization"];
    expect(authorization?.startsWith("Bearer ")).toBe(true);
    if (testBearer) {
      expect(authorization?.length).toBe("Bearer ".length + testBearer.length);
      expect(
        createHash("sha256").update(authorization?.slice("Bearer ".length) ?? "").digest("hex"),
      ).toBe(createHash("sha256").update(testBearer).digest("hex"));
    }
    await route.continue();
  });

  const result = await page.evaluate(async ({ prompt, sessionId }) => {
    const { askBackendStream } = await import("/src/deck/backend-stream.ts");
    const startedAt = performance.now();
    let firstTokenMs: number | null = null;
    const reply = await askBackendStream(prompt, null, [], {
      onToken: () => {
        if (firstTokenMs === null) firstTokenMs = performance.now() - startedAt;
      },
      sessionId,
      semanticPlanningProfile: "interactive",
    });
    return {
      reply,
      firstTokenMs,
      elapsedMs: performance.now() - startedAt,
    };
  }, {
    prompt: PROMPT,
    sessionId: randomUUID(),
  });

  const receipt = result.reply.semanticReceipt;
  const diagnostic = JSON.stringify({
    source: result.reply.source,
    verificationStatus: result.reply.verification?.status ?? null,
    verificationReason: result.reply.verification?.reason_code ?? null,
    hasSemanticReceipt: receipt !== undefined,
  });
  expect(receipt?.execution_authority, diagnostic).toBe(false);
  expect(receipt?.disposition, receipt?.reason_code).toBe("answered");
  expect(receipt?.assurance_observation?.frame?.output_shape).toBe(
    "property_filtered_resources",
  );
  expect(receipt?.assurance_observation?.read_performed).toBe(true);
  expect(result.reply.text).not.toContain("어떤 주장이나 대상을 먼저 확인할까요");
  expect(result.firstTokenMs).not.toBeNull();
  expect(result.firstTokenMs).toBeLessThanOrEqual(5_000);
});
