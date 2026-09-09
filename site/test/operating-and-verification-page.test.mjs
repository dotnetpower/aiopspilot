import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function loadEnKo() {
  const [english, korean] = await Promise.all([
    readFile(
      new URL(
        "../docs/roadmap/operations/operating-and-verification.md",
        root,
      ),
      "utf8",
    ),
    readFile(
      new URL(
        "../docs/roadmap/operations/operating-and-verification-ko.md",
        root,
      ),
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

test("operating-and-verification page embeds its diagram with matching manifest alt text", async () => {
  const { english, korean } = await loadEnKo();
  const id = "fdai-operating-and-verification-01";
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

test("Round 17 regression: diagram source translates all flow node labels into Korean", async () => {
  const source = await loadDiagramSource("fdai-operating-and-verification-01");
  for (const untranslated of [
    "ko: Audit id or correlation id",
    "ko: Event lookup",
    "ko: Tier decision plus confidence",
    "ko: Cited rules and their versions",
    "ko: Risk-gate decision auto or HIL",
    "ko: Approver identity when HIL",
    "ko: Action outcome plus idempotency key",
    "ko: Rollback reference when applicable",
  ]) {
    assert.ok(
      !source.includes(untranslated),
      `diagram must not leave "${untranslated}" byte-identical to English`,
    );
  }
  assert.ok(source.includes("ko: 감사 id 또는 상관관계 id"));
  assert.ok(source.includes("ko: 이벤트 조회"));
  assert.ok(source.includes("ko: 티어 결정 및 신뢰도"));
  assert.ok(source.includes("ko: 인용된 규칙과 버전"));
  assert.ok(source.includes("ko: Risk-gate 결정 (auto 또는 HIL)"));
  assert.ok(source.includes("ko: HIL 시 승인자 신원"));
  assert.ok(source.includes("ko: 액션 결과 및 멱등성 키"));
  assert.ok(source.includes("ko: 해당 시 롤백 참조"));
});

test("Round 17 regression: Korean H1 title typo is fixed to the full English gloss", async () => {
  const { korean } = await loadEnKo();
  assert.ok(!korean.includes("# 운영과 검증(Operating and 검증)"));
  assert.ok(korean.includes("# 운영과 검증(Operating and Verification)"));
});

test("Round 17 regression: duplicated-syllable typos are fixed", async () => {
  const { korean } = await loadEnKo();
  assert.ok(!korean.includes("예행 실행 실행 장치에서"));
  assert.ok(korean.includes("예행 실행 장치에서"));
  assert.ok(!korean.includes("실제 실제 운영 `429`"));
  assert.ok(korean.includes("실제 운영 `429`"));
});

test("Round 17 regression: broken cross-page anchors are fixed to their real heading slugs", async () => {
  const { english, korean } = await loadEnKo();
  for (const staleAnchor of [
    "#always-on-rules-must",
    "#implementation-status",
    "#safety-invariants",
  ]) {
    assert.ok(
      !english.includes(staleAnchor),
      `English page must not re-introduce the broken anchor "${staleAnchor}"`,
    );
  }
  assert.ok(english.includes("#fdai-core-principles-must"));
  assert.ok(english.includes("#verification-and-release-evidence"));
  assert.ok(english.includes("#seven-autonomous-action-safeguards"));

  for (const staleAnchor of [
    "#always-on-rules-must",
    "#제공되는-runtime-경계",
    "#구현-상태",
    "#cold-start-scale-to-zero-specifics",
    "deployment-ko.md#release-and-rollback",
    "deployment-ko.md#observability-slos-and-alerting",
    "#safety-invariants",
  ]) {
    assert.ok(
      !korean.includes(staleAnchor),
      `Korean page must not re-introduce the broken anchor "${staleAnchor}"`,
    );
  }
  assert.ok(korean.includes("#fdai-core-principles-must"));
  assert.ok(korean.includes("#제공되는-런타임-경계"));
  assert.ok(korean.includes("#검증-및-release-근거"));
  assert.ok(korean.includes("#콜드-스타트-scale-to-zero-세부사항"));
  assert.ok(korean.includes("deployment-ko.md#릴리스와-롤백release-and-rollback"));
  assert.ok(korean.includes("deployment-ko.md#관측성-slo-알림"));
  assert.ok(korean.includes("#seven-autonomous-action-safeguards"));
});
