import { createHash, randomUUID } from "node:crypto";
import { writeFile } from "node:fs/promises";

import { expect, test, type Page } from "@playwright/test";

import { restoreBrowserEntraSessionStorage } from "./browser-entra-state";

const LOCAL_CLI_AUTH = process.env.FDAI_E2E_LOCAL_CLI_AUTH === "1";
const AUTHENTICATED_STACK = Boolean(
  process.env.FDAI_E2E_BEARER ||
    (process.env.FDAI_E2E_BASE_URL && (process.env.FDAI_E2E_STORAGE_STATE || LOCAL_CLI_AUTH)),
);
const PROMPT = "배포된 llm 모델이 뭐야";
const MAX_SUBSCRIPTION_MODEL_TOKENS = 5_000;
const ISSUE_241_VIEWPORTS = [
  { width: 1440, height: 900, label: "desktop" },
  { width: 993, height: 641, label: "constrained-desktop" },
  { width: 390, height: 844, label: "mobile" },
] as const;

async function prepareAuthenticatedPage(page: Page): Promise<void> {
  test.skip(!AUTHENTICATED_STACK, "requires an authenticated Console stack");
  if (!LOCAL_CLI_AUTH && !process.env.FDAI_E2E_BEARER) {
    await restoreBrowserEntraSessionStorage(page);
  }
  await page.goto("/overview", { waitUntil: "domcontentloaded", timeout: 30_000 });
  await expect(page.locator(".shell")).toBeVisible({ timeout: 30_000 });
  const testBearer = process.env.FDAI_E2E_BEARER;
  await page.route("**/chat/stream", async (route) => {
    if (testBearer) {
      expect(new URL(route.request().url()).port).not.toBe("8010");
    }
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
}

async function ask(page: Page, prompt: string) {
  return page.evaluate(async ({ prompt: question, sessionId }) => {
    const { askBackendStream } = await import("/src/deck/backend-stream.ts");
    const startedAt = performance.now();
    let firstTokenMs: number | null = null;
    const reply = await askBackendStream(question, null, [], {
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
    prompt,
    sessionId: randomUUID(),
  });
}

function jsonRecord(text: string | undefined, label: string): Record<string, unknown> {
  if (text === undefined) throw new Error(`${label} was not rendered`);
  const parsed: unknown = JSON.parse(text);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object`);
  }
  return parsed as Record<string, unknown>;
}

test("deployed LLM collection reaches verified inventory without identity clarification", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await prepareAuthenticatedPage(page);
  const result = await ask(page, PROMPT);

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

test("subscription identity keeps semantic model usage below the compact budget", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await prepareAuthenticatedPage(page);
  const result = await ask(page, "구독 정보 알려줘");
  const receipt = result.reply.semanticReceipt;
  const totalTokens = result.reply.modelUsage?.total_tokens;
  const diagnostic = JSON.stringify({
    source: result.reply.source,
    verificationStatus: result.reply.verification?.status ?? null,
    verificationReason: result.reply.verification?.reason_code ?? null,
    hasSemanticReceipt: receipt !== undefined,
    totalTokens: totalTokens ?? null,
    elapsedMs: Math.round(result.elapsedMs),
  });

  expect(receipt?.execution_authority, diagnostic).toBe(false);
  expect(receipt?.disposition, diagnostic).toBe("answered");
  expect(receipt?.assurance_observation?.frame?.output_shape, diagnostic).toBe(
    "subscription_scope_identity",
  );
  expect(receipt?.assurance_observation?.read_performed, diagnostic).toBe(true);
  expect(totalTokens, diagnostic).toBeDefined();
  expect(totalTokens, diagnostic).toBeLessThanOrEqual(MAX_SUBSCRIPTION_MODEL_TOKENS);
});

test("subscription inventory produces one complete document", async ({ page }) => {
  test.setTimeout(120_000);
  await prepareAuthenticatedPage(page);
  const result = await ask(page, "구독에 배포된 리소스 상세 정보를 문서화하자.");
  const receipt = result.reply.semanticReceipt;
  const document = result.reply.documentArtifact;
  const diagnostic = JSON.stringify({
    source: result.reply.source,
    disposition: receipt?.disposition ?? null,
    reason: receipt?.reason_code ?? null,
    hasDocument: document !== undefined,
  });

  expect(receipt?.disposition, diagnostic).toBe("answered");
  expect(receipt?.assurance_observation?.frame?.output_shape, diagnostic).toBe("resource_list");
  expect(document?.complete, diagnostic).toBe(true);
  expect(document?.includedRows, diagnostic).toBe(document?.expectedRows);
});

test("fdai resource-group collection renders names without authorization artifacts", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await prepareAuthenticatedPage(page);
  const result = await ask(page, "지금 fdai 가 포함된 리소스 그룹은?");
  const receipt = result.reply.semanticReceipt;
  const totalTokens = result.reply.modelUsage?.total_tokens;
  const diagnostic = JSON.stringify({
    source: result.reply.source,
    disposition: receipt?.disposition ?? null,
    reason: receipt?.reason_code ?? null,
    totalTokens: totalTokens ?? null,
  });

  expect(receipt?.disposition, diagnostic).toBe("answered");
  expect(receipt?.assurance_observation?.frame?.output_shape, diagnostic).toBe(
    "property_filtered_resources",
  );
  expect(receipt?.assurance_observation?.read_performed, diagnostic).toBe(true);
  expect(result.reply.text, diagnostic).toContain("resource-group");
  expect(result.reply.text, diagnostic).not.toContain("authorization.role-assignment");
  expect(result.reply.text.toLowerCase(), diagnostic).not.toContain(
    "microsoft.authorization/roleassignments",
  );
  expect(totalTokens, diagnostic).toBeDefined();
  expect(totalTokens, diagnostic).toBeLessThanOrEqual(MAX_SUBSCRIPTION_MODEL_TOKENS);
});

test("fdai resource-group Run record stays exact and responsive", async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  await page.setViewportSize(ISSUE_241_VIEWPORTS[0]);
  await prepareAuthenticatedPage(page);
  await page.locator(".deck-invoke").click();
  const deck = page.getByRole("complementary", { name: "Command deck" });
  await expect(deck).toBeVisible();
  const historyDismiss = deck.locator(".deck-conversations-dismiss");
  if (await historyDismiss.isVisible()) await historyDismiss.click();
  await deck.locator(".deck-input").fill("지금 fdai 가 포함된 리소스 그룹은?");
  await deck.locator(".cs-deck-composer-send").click();
  const presentation = deck.locator(".cs-deck-answer").last();
  await expect(presentation).toContainText("resource-group", { timeout: 90_000 });
  await expect(presentation).not.toContainText("authorization.role-assignment");
  await expect(presentation).not.toContainText("microsoft.authorization/roleassignments");
  if (await historyDismiss.isVisible()) await historyDismiss.click();

  const runRecord = deck.locator(".deck-trajectory").last();
  await expect(runRecord).toBeVisible();
  await runRecord.locator(":scope > summary").click();
  await expect(runRecord).toHaveAttribute("open", "");
  await runRecord.locator("details").evaluateAll((details) => {
    for (const detail of details) {
      if (detail instanceof HTMLDetailsElement) detail.open = true;
    }
  });
  const queryActivity = runRecord.locator(".deck-trajectory-evidence > li")
    .filter({ hasText: "query.object_set" })
    .first();
  await expect(queryActivity).toBeVisible();
  const records = await queryActivity.locator("pre code").allTextContents();
  const query = jsonRecord(
    records.find((record) => record.includes("\"object_set\"")),
    "verified ObjectSet",
  );
  const objectSet = query.object_set;
  if (typeof objectSet !== "object" || objectSet === null || Array.isArray(objectSet)) {
    throw new Error("verified ObjectSet definition must be an object");
  }
  const predicates = (objectSet as Record<string, unknown>).predicates;
  expect(query.capability).toBe("query.object_set");
  expect(query.execution_authority).toBe(false);
  expect((objectSet as Record<string, unknown>).selector).toEqual({
    kind: "object_type",
    name: "Resource",
  });
  expect(predicates).toEqual(expect.arrayContaining([
    { equals: "fdai", operator: "contains", property: "name" },
    { equals: "resource-group", operator: "equals", property: "type" },
  ]));
  const output = jsonRecord(
    records.find((record) => record.includes("\"returned_rows\"")),
    "verified ObjectSet row counts",
  );
  expect(output.status).toBe("completed");
  const returnedRows = output.returned_rows;
  const totalRows = output.total_rows;
  if (typeof returnedRows !== "number" || typeof totalRows !== "number") {
    throw new Error("verified ObjectSet row counts must be numeric");
  }
  expect(returnedRows).toBeGreaterThan(0);
  expect(totalRows).toBeGreaterThanOrEqual(returnedRows);
  expect(typeof output.source_complete).toBe("boolean");
  if (output.source_complete === false) {
    expect(typeof output.source_truncation_reason).toBe("string");
  }

  const viewports: Record<string, unknown>[] = [];
  for (const viewport of ISSUE_241_VIEWPORTS) {
    await page.setViewportSize(viewport);
    await runRecord.scrollIntoViewIfNeeded();
    const measurements = await page.locator("html, .deck-overlay, .deck-transcript").evaluateAll(
      (elements) => elements.map((element) => ({
        name: element.className || element.tagName.toLowerCase(),
        client_width: element.clientWidth,
        scroll_width: element.scrollWidth,
        overflow: element.scrollWidth > element.clientWidth,
      })),
    );
    expect(measurements.map((measurement) => measurement.overflow)).toEqual([
      false,
      false,
      false,
    ]);
    viewports.push({ ...viewport, measurements });
    await page.screenshot({
      path: testInfo.outputPath(`issue-241-${viewport.label}.png`),
      fullPage: false,
    });
  }
  await page.setViewportSize(ISSUE_241_VIEWPORTS[0]);
  expect(await page.locator("html, .deck-overlay, .deck-transcript").evaluateAll(
    (elements) => elements.every((element) => element.scrollWidth <= element.clientWidth),
  )).toBe(true);

  const evidence = {
    schema_version: "1.0.0",
    issue: 241,
    source_revision: process.env.FDAI_E2E_SOURCE_REVISION ?? null,
    authenticated: true,
    query,
    row_counts: {
      returned_rows: returnedRows,
      total_rows: totalRows,
      source_complete: output.source_complete,
      source_truncation_reason: output.source_truncation_reason ?? null,
    },
    viewports,
    execution_authority: false,
    passed: true,
  };
  const evidencePath = testInfo.outputPath("issue-241-run-record.json");
  await writeFile(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  await testInfo.attach("issue-241-run-record", {
    path: evidencePath,
    contentType: "application/json",
  });
});

test("deployed GPT configuration change uses a type-scoped recent comparison", async ({ page }) => {
  test.setTimeout(120_000);
  await prepareAuthenticatedPage(page);
  const result = await ask(
    page,
    "구독에 배포된 GPT 리소스의 변경이 있는지 확인해보자. 변경이 있다면 알려주고 이로 인해 발생될 수 있는 문제를 알려줘",
  );
  const receipt = result.reply.semanticReceipt;
  const diagnostic = JSON.stringify({
    source: result.reply.source,
    disposition: receipt?.disposition ?? null,
    reason: receipt?.reason_code ?? null,
  });

  expect(receipt?.disposition, diagnostic).toBe("answered");
  expect(receipt?.assurance_observation?.frame?.output_shape, diagnostic).toBe(
    "resource_configuration_changes",
  );
  expect(receipt?.assurance_observation?.read_performed, diagnostic).toBe(true);
});

for (const [label, prompt] of [
  [
    "AppGW",
    "SRE-AppGW-01을 통해 서비스를 하고 있는데 갑자기 Client들이 느려짐을 보고하고 있어. AppGW의 상태가 이상한지? Backend Instance 상태가 이상한지 메트릭 기반으로 확인하자. 혹시 Backend 리소스의 변화가 있는지도 확인하자",
  ],
  [
    "APIM/GPT",
    "SRE-APIM을 통해 GPT 5.4로 연결된 서비스에 500 Error가 발생하고 있어. GPT 리소스의 문제인지 API Management 서비스의 문제인지 메트릭 기반으로 확인하고 APIM 또는 GPT 리소스의 구성 변화가 있는지 확인하자",
  ],
] as const) {
  test(`${label} SRE diagnostic returns evidence or an explicit target gap`, async ({ page }) => {
    test.setTimeout(120_000);
    await prepareAuthenticatedPage(page);
    const result = await ask(page, prompt);
    const receipt = result.reply.semanticReceipt;
    const diagnostic = JSON.stringify({
      source: result.reply.source,
      disposition: receipt?.disposition ?? null,
      reason: receipt?.reason_code ?? null,
    });

    expect(receipt?.assurance_observation?.frame?.output_shape, diagnostic).toBe(
      "gateway_diagnostic_evidence",
    );
    expect(receipt?.assurance_observation?.read_performed, diagnostic).toBe(true);
    expect(["answered", "held"], diagnostic).toContain(receipt?.disposition);
    if (receipt?.disposition === "held") {
      expect(receipt.reason_code, diagnostic).toBe("semantic_evidence_held");
      expect(result.reply.text, diagnostic).toContain("execution_authority=false");
    }
  });
}
