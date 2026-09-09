import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function loadEnKo() {
  const [english, korean] = await Promise.all([
    readFile(
      new URL("../docs/roadmap/interfaces/operator-console.md", root),
      "utf8",
    ),
    readFile(
      new URL("../docs/roadmap/interfaces/operator-console-ko.md", root),
      "utf8",
    ),
  ]);
  return { english, korean };
}

async function loadDiagramSource(id) {
  return readFile(new URL(`../docs/diagrams/${id}.diagram.yaml`, root), "utf8");
}

async function loadManifest(id) {
  const source = await readFile(
    new URL(`public/diagrams/generated/${id}.manifest.json`, root),
    "utf8",
  );
  return JSON.parse(source);
}

test("operator-console page embeds its diagram with matching manifest alt text", async () => {
  const { english, korean } = await loadEnKo();
  const id = "fdai-operator-console-01";
  const manifest = await loadManifest(id);
  const enAltMatch = english.match(
    new RegExp(`!\\[([^\\]]+)\\]\\([^\\n)]*${id}\\.en\\.svg\\)`, "u"),
  );
  const koAltMatch = korean.match(
    new RegExp(`!\\[([^\\]]+)\\]\\([^\\n)]*${id}\\.ko\\.svg\\)`, "u"),
  );
  assert.ok(enAltMatch, `expected an English markdown embed for ${id}`);
  assert.ok(koAltMatch, `expected a Korean markdown embed for ${id}`);
  assert.equal(enAltMatch[1], manifest.locales.en.alt);
  assert.equal(koAltMatch[1], manifest.locales.ko.alt);
});

test("Round 16 regression: diagram source translates group and descriptive node labels into Korean", async () => {
  const source = await loadDiagramSource("fdai-operator-console-01");
  for (const untranslated of [
    "ko: Layer 3 - Channel (thin adapter)",
    "ko: Layer 2 - Conversation Coordinator",
    "ko: Layer 1 - Existing deterministic core (unchanged)",
    "ko: Intent classify\\n(read | simulate | approve | breakglass)",
    "ko: RBAC gate\\n(per-tool role floor)",
    "ko: Verifier re-check\\n(no auto-execute)",
    "ko: Session state\\n(audit-log-backed)",
  ]) {
    assert.ok(
      !source.includes(untranslated),
      `diagram must not leave "${untranslated}" byte-identical to English`,
    );
  }
  assert.ok(source.includes("ko: 계층 3 - 채널 (얇은 어댑터)"));
  assert.ok(source.includes("ko: 계층 2 - 대화 조정기"));
  assert.ok(source.includes("ko: 계층 1 - 기존 결정론적 코어 (변경 없음)"));
  assert.ok(source.includes("ko: 의도 분류\\n(read | simulate | approve | breakglass)"));
  assert.ok(source.includes("ko: RBAC gate\\n(도구별 역할 하한)"));
  assert.ok(source.includes("ko: 검증기 re-check\\n(자동 실행 없음)"));
  assert.ok(source.includes("ko: 세션 상태\\n(감사 로그 기반)"));
  // Class/module-identifier-style labels stay English by established repo convention.
  for (const kept of [
    "ControlLoop",
    "RuleIndex / T0Engine",
    "QualityGate",
    "ShadowExecutor / RiskGate",
    "Inventory / StateStore",
    "CLI REPL",
  ]) {
    assert.ok(
      source.includes(`en: ${kept}`),
      `expected English label "${kept}" to be present`,
    );
  }
});

test("Round 16 regression: fabricated env vars are removed from both pages", async () => {
  const { english, korean } = await loadEnKo();
  for (const stale of [
    "FDAI_INVENTORY_SEMANTIC_ENABLED",
    "FDAI_CATALOG_SEARCH_ENABLED",
  ]) {
    assert.ok(!english.includes(stale), `English page must not re-introduce "${stale}"`);
    assert.ok(!korean.includes(stale), `Korean page must not re-introduce "${stale}"`);
  }
});

test("Round 16 regression: fabricated enqueue_hil(...) tool call syntax is removed", async () => {
  const { english, korean } = await loadEnKo();
  assert.ok(!english.includes("enqueue_hil("));
  assert.ok(!korean.includes("enqueue_hil("));
});

test("Round 16 regression: fabricated class names are replaced with accurate descriptions", async () => {
  const { english, korean } = await loadEnKo();
  for (const stale of ["AzureOpenAINarratorModel", "ProductionChannelRuntime"]) {
    assert.ok(!english.includes(stale), `English page must not re-introduce "${stale}"`);
    assert.ok(!korean.includes(stale), `Korean page must not re-introduce "${stale}"`);
  }
  assert.ok(english.includes("delivery-layer Azure OpenAI narrator adapter"));
  assert.ok(english.includes("delivery-layer channel runtime"));
});

test("Round 16 regression: broken #console-static-web-app anchor is fixed to the real module-boundaries slug", async () => {
  const { english, korean } = await loadEnKo();
  assert.ok(!english.includes("#console-static-web-app"));
  assert.ok(!korean.includes("#console-static-web-app"));
  assert.ok(english.includes("#module-boundaries"));
  assert.ok(korean.includes("#모듈-경계모듈-boundaries"));
});

test("Round 16 regression: duplicate 'Related docs' heading is disambiguated from section 16", async () => {
  const { english, korean } = await loadEnKo();
  assert.ok(english.includes("## 16. Further reading"));
  assert.ok(english.includes("## Related docs"));
  assert.ok(korean.includes("## 16. 추가 참고 자료"));
  assert.ok(korean.includes("## 관련 문서"));
});

test("Round 16 regression: query_operator_memory tool row is present in the Day-1 tool catalog", async () => {
  const { english, korean } = await loadEnKo();
  assert.ok(english.includes("query_operator_memory"));
  assert.ok(korean.includes("query_operator_memory"));
});

test("Round 16 regression: KO Week-1/Month-1 headings match the EN literal convention used elsewhere on the page", async () => {
  const { korean } = await loadEnKo();
  assert.ok(!korean.includes("### 9.2 주 1"));
  assert.ok(!korean.includes("### 9.3 월 1"));
  assert.ok(korean.includes("### 9.2 Week 1"));
  assert.ok(korean.includes("### 9.3 Month 1"));
});

test("Round 16 regression: fabricated TeamsBotChannel/SlackBotChannel class names are replaced with the real ingress verifier classes", async () => {
  const { english, korean } = await loadEnKo();
  for (const stale of ["TeamsBotChannel", "SlackBotChannel"]) {
    assert.ok(!english.includes(stale), `English page must not re-introduce "${stale}"`);
    assert.ok(!korean.includes(stale), `Korean page must not re-introduce "${stale}"`);
  }
  assert.ok(english.includes("TeamsIngressVerifier"));
  assert.ok(english.includes("SlackIngressVerifier"));
  assert.ok(korean.includes("TeamsIngressVerifier"));
  assert.ok(korean.includes("SlackIngressVerifier"));
});
