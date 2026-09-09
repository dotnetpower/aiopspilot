import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function loadEnKo() {
  const [english, korean] = await Promise.all([
    readFile(
      new URL(
        "../docs/roadmap/decisioning/escalation-and-standing-authority.md",
        root,
      ),
      "utf8",
    ),
    readFile(
      new URL(
        "../docs/roadmap/decisioning/escalation-and-standing-authority-ko.md",
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

test("escalation-and-standing-authority page embeds both diagrams with matching manifest alt text", async () => {
  const { english, korean } = await loadEnKo();
  for (const id of [
    "fdai-escalation-and-standing-authority-01",
    "fdai-escalation-and-standing-authority-02",
  ]) {
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
  }
});

test("Round 13 regression: standing authorization example matches the shipped schema/parser field names", async () => {
  const { english, korean } = await loadEnKo();
  const block = english.match(/```yaml\n# Matches the shipped schema[\s\S]*?\n```/u);
  assert.ok(block, "expected the corrected standing-authorization example block");
  const yaml = block[0];

  // Real schema/record.py field names that must be present.
  for (const mustHave of [
    'schema_version: "1.0.0"',
    "approvals:",
    "role: service_owner",
    "role: owner",
    "pins:",
    "evidence_revisions:",
    "level: resource_group",
    "confirmed_at:",
    "history_reviewed: true",
    "stop_conditions:",
  ]) {
    assert.ok(yaml.includes(mustHave), `expected corrected example to include ${mustHave}`);
  }

  // Fictional fields that do not exist in the real schema/parser must never reappear
  // in either locale's standing-authorization example.
  for (const mustNotHave of [
    "approved_by:",
    "revocation_ref",
    "precondition:",
    "resolved_at:",
    "history_review_ref",
    "handover_confirmation_ref",
    "max_blast_radius: resource_group",
    "trigger:\n  after: ladder_unanswered",
  ]) {
    assert.ok(
      !english.includes(mustNotHave),
      `English page must not re-introduce the non-existent ${mustNotHave}`,
    );
    assert.ok(
      !korean.includes(mustNotHave),
      `Korean page must not re-introduce the non-existent ${mustNotHave}`,
    );
  }
});

test("Round 13 regression: 'precondition' is never claimed as a schema-encoded concept", async () => {
  const { english, korean } = await loadEnKo();
  assert.ok(
    !english.toLowerCase().includes("precondition"),
    "English page must not reference the non-existent standing-authorization precondition field",
  );
  assert.ok(
    !korean.includes("전제조건"),
    "Korean page must not reference the non-existent standing-authorization precondition field",
  );
});

test("Round 13 regression: diagram-02 edge label describes pinned revisions, not a fictional precondition", async () => {
  const source = await loadDiagramSource("fdai-escalation-and-standing-authority-02");
  assert.ok(!source.includes("precondition"), "diagram-02 must not claim a precondition field");
  assert.ok(source.includes("SA pins + envelope verified"));
});

test("Round 13 regression: both diagram sources have fully translated, non-English-identical Korean node labels", async () => {
  for (const id of [
    "fdai-escalation-and-standing-authority-01",
    "fdai-escalation-and-standing-authority-02",
  ]) {
    const source = await loadDiagramSource(id);
    assert.ok(
      !source.includes("ko: approval still pending?"),
      `${id} must not leave narrative node labels untranslated in ko:`,
    );
  }
  const source01 = await loadDiagramSource("fdai-escalation-and-standing-authority-01");
  assert.ok(source01.includes("승인이 아직 보류 중인가?"));
  assert.ok(source01.includes("무대응 시 영향 범위는?"));
  const source02 = await loadDiagramSource("fdai-escalation-and-standing-authority-02");
  assert.ok(source02.includes("에스컬레이션 supervisor"));
  assert.ok(source02.includes("승인된 HIL 액션 실행"));
});

test("Round 13 regression: Korean page has no space-detached particles at the previously broken locations", async () => {
  const { korean } = await loadEnKo();
  for (const broken of [
    "묶음 로",
    "계층 로",
    "정족수 으로",
    "경계 으로",
    "거부 로",
  ]) {
    assert.ok(
      !korean.includes(broken),
      `Korean page must not re-introduce the broken particle usage "${broken}"`,
    );
  }
});

test("Round 13 regression: garbled bilingual gloss and broken code-switch are fixed", async () => {
  const { korean } = await loadEnKo();
  assert.ok(
    !korean.includes("standing 권한 확인"),
    "Korean page must not re-introduce the garbled standing-authorization gloss",
  );
  assert.ok(
    !korean.includes("규모 out"),
    "Korean page must not re-introduce the broken 'scale out' code-switch",
  );
  assert.ok(korean.includes("스케일 아웃"));
});
