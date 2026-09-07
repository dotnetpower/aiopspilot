import { createHash, randomUUID } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";

import { expect, test, type Page } from "@playwright/test";

import { restoreBrowserEntraSessionStorage } from "./browser-entra-state";

type Family = "inventory" | "gpt_configuration" | "appgw_latency" | "apim_gpt_errors";

interface OperationalCase {
  readonly id: string;
  readonly family: Family;
  readonly prompt: string;
}

interface OperationalCases {
  readonly schema_version: 1;
  readonly cases: readonly OperationalCase[];
}

interface DownloadEvidence {
  readonly status: number;
  readonly body: string;
  readonly bodySha256: string;
  readonly headerSha256: string | null;
  readonly includedRows: string | null;
  readonly expectedRows: string | null;
}

const MAX_FIRST_PROGRESS_MS = 5_000;
const MAX_ANSWER_TTFT_MS = 15_000;

const EXPECTED_OUTPUT_SHAPE: Readonly<Record<Exclude<Family, "inventory">, string>> = {
  gpt_configuration: "resource_configuration_changes",
  appgw_latency: "gateway_diagnostic_evidence",
  apim_gpt_errors: "gateway_diagnostic_evidence",
};

function loadPath(): string {
  const path = process.env.FDAI_E2E_OPERATIONAL_CASES;
  if (!path) throw new Error("FDAI_E2E_OPERATIONAL_CASES is required");
  return path;
}

async function loadCases(): Promise<readonly OperationalCase[]> {
  const parsed = JSON.parse(await readFile(loadPath(), "utf8")) as OperationalCases;
  if (
    parsed.schema_version !== 1 ||
    !Array.isArray(parsed.cases) ||
    parsed.cases.length < 8 ||
    parsed.cases.some((item) =>
      !item ||
      typeof item.id !== "string" ||
      typeof item.prompt !== "string" ||
      !Object.hasOwn(EXPECTED_OUTPUT_SHAPE, item.family) && item.family !== "inventory"
    )
  ) {
    throw new Error("operational diagnostic cases are malformed");
  }
  const ids = parsed.cases.map((item) => item.id);
  if (new Set(ids).size !== ids.length) {
    throw new Error("operational diagnostic case ids must be unique");
  }
  const locale = process.env.FDAI_E2E_OPERATIONAL_LOCALE;
  if (locale === "ko" || locale === "en") {
    return parsed.cases.filter((item) => item.id.endsWith(`-${locale}`));
  }
  return parsed.cases;
}

async function submit(page: Page, operationalCase: OperationalCase) {
  return page.evaluate(async ({ prompt, sessionId, bearer }) => {
    if (bearer) {
      const { setChatAuth } = await import("/src/deck/auth.ts");
      setChatAuth({
        devMode: true,
        interactiveSignIn: false,
        account: null,
        getAuthorizationHeader: async () => `Bearer ${bearer}`,
        signIn: async () => undefined,
        signOut: async () => undefined,
      });
    }
    const { askBackendStream } = await import("/src/deck/backend-stream.ts");
    const startedAt = performance.now();
    let firstTokenMs: number | null = null;
    let firstProgressMs: number | null = null;
    const reply = await askBackendStream(prompt, null, [], {
      onToken: () => {
        if (firstTokenMs === null) firstTokenMs = performance.now() - startedAt;
      },
      onProgress: () => {
        if (firstProgressMs === null) firstProgressMs = performance.now() - startedAt;
      },
      sessionId,
      semanticPlanningProfile: "interactive",
    });
    return { reply, firstProgressMs, firstTokenMs };
  }, {
    prompt: operationalCase.prompt,
    sessionId: randomUUID(),
    bearer: process.env.FDAI_E2E_BEARER ?? null,
  });
}

async function downloadMarkdown(
  page: Page,
  markdownUrl: string,
): Promise<DownloadEvidence> {
  return page.evaluate(async (artifactUrl) => {
    const { chatUrl, requestHeaders } = await import("/src/deck/backend-endpoints.ts");
    const operatorRoot = chatUrl().replace(/\/chat$/, "");
    const response = await fetch(`${operatorRoot}${artifactUrl}`, {
      headers: await requestHeaders(),
    });
    const body = await response.text();
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(body));
    return {
      status: response.status,
      body,
      bodySha256: Array.from(new Uint8Array(digest))
        .map((value) => value.toString(16).padStart(2, "0"))
        .join(""),
      headerSha256: response.headers.get("X-FDAI-Artifact-SHA256"),
      includedRows: response.headers.get("X-FDAI-Included-Rows"),
      expectedRows: response.headers.get("X-FDAI-Expected-Rows"),
    };
  }, markdownUrl);
}

async function persistResults(
  path: string,
  results: readonly Record<string, unknown>[],
): Promise<void> {
  await writeFile(
    path,
    `${JSON.stringify({
      schema_version: 1,
      source_revision: process.env.FDAI_E2E_SOURCE_REVISION ?? null,
      workspace_patch_sha256: process.env.FDAI_E2E_WORKSPACE_PATCH_SHA256 ?? null,
      cases: results,
    }, null, 2)}\n`,
    { encoding: "utf8", mode: 0o600 },
  );
}

test("interactive operational diagnostics retain evidence across varied questions", async ({
  page,
}, testInfo) => {
  test.skip(
    !process.env.FDAI_E2E_BEARER &&
      (!process.env.FDAI_E2E_BASE_URL || !process.env.FDAI_E2E_STORAGE_STATE),
    "requires an authenticated isolated Console stack",
  );
  test.setTimeout(45 * 60 * 1_000);
  const cases = await loadCases();
  if (!process.env.FDAI_E2E_BEARER) {
    await restoreBrowserEntraSessionStorage(page);
  }
  await page.route("**/chat/stream", async (route) => {
    const authorization = route.request().headers()["authorization"];
    expect(authorization?.startsWith("Bearer ")).toBe(true);
    expect(authorization?.length).toBeGreaterThan(16);
    await route.continue();
  });
  await page.goto("/architecture", { waitUntil: "domcontentloaded", timeout: 30_000 });
  await expect(page.locator(".shell")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("FDAI could not verify your access.")).toHaveCount(0);

  const results: Array<Record<string, unknown>> = [];
  const resultsPath = testInfo.outputPath("operational-diagnostic-results.json");
  for (const operationalCase of cases) {
    const startedAt = Date.now();
    const { reply, firstProgressMs, firstTokenMs } = await submit(page, operationalCase);
    const receipt = reply.semanticReceipt;
    const frame = receipt?.assurance_observation?.frame;
    const document = reply.documentArtifact;
    const download = document ? await downloadMarkdown(page, document.markdownUrl) : null;
    results.push({
      id: operationalCase.id,
      family: operationalCase.family,
      elapsed_ms: Date.now() - startedAt,
      first_progress_ms: firstProgressMs,
      first_answer_token_ms: firstTokenMs,
      prompt_sha256: createHash("sha256").update(operationalCase.prompt).digest("hex"),
      answer: reply.text,
      source: reply.source,
      receipt,
      verification: reply.verification,
      document,
      download,
    });
    await persistResults(resultsPath, results);

    expect.soft(receipt?.execution_authority).toBe(false);
    expect.soft(
      firstProgressMs,
      `${operationalCase.id} emitted no progress signal`,
    ).not.toBeNull();
    expect.soft(
      firstProgressMs,
      `${operationalCase.id} exceeded ${MAX_FIRST_PROGRESS_MS}ms first progress`,
    ).toBeLessThanOrEqual(MAX_FIRST_PROGRESS_MS);
    const evidenceHeld = receipt?.disposition === "held" &&
      receipt.reason_code === "semantic_evidence_held" &&
      receipt.assurance_observation?.read_performed === true;
    if (!evidenceHeld) {
      expect.soft(firstTokenMs, `${operationalCase.id} emitted no answer token`).not.toBeNull();
      expect.soft(
        firstTokenMs,
        `${operationalCase.id} exceeded ${MAX_ANSWER_TTFT_MS}ms answer TTFT`,
      ).toBeLessThanOrEqual(MAX_ANSWER_TTFT_MS);
      expect.soft(receipt?.disposition, `${operationalCase.id} ${receipt?.reason_code}`).toBe(
        "answered",
      );
    } else {
      expect.soft(reply.text).toContain("execution_authority=false");
    }
    if (operationalCase.family === "inventory") {
      expect.soft(frame?.operation).toBe("select");
      expect.soft(frame?.output_shape).toBe("resource_list");
      expect.soft(document?.complete).toBe(true);
      expect.soft(document?.includedRows).toBe(document?.expectedRows);
      expect.soft(download?.status).toBe(200);
      expect.soft(download?.bodySha256).toBe(download?.headerSha256);
      expect.soft(download?.includedRows).toBe(download?.expectedRows);
      expect.soft(download?.body).toContain("- Source complete: `true`");
      expect.soft(download?.body).toContain("## Evidence references");
    } else {
      expect.soft(frame?.output_shape).toBe(EXPECTED_OUTPUT_SHAPE[operationalCase.family]);
      expect.soft(receipt?.assurance_observation?.read_performed).toBe(true);
    }
  }
});
