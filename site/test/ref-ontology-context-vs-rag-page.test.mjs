import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function loadManifest(name) {
  const source = await readFile(
    new URL(`public/diagrams/generated/${name}.manifest.json`, root),
    "utf8",
  );
  return JSON.parse(source);
}

async function loadSvg(name, locale) {
  return readFile(
    new URL(`public/diagrams/generated/${name}.${locale}.svg`, root),
    "utf8",
  );
}

function imageAlt(source, name, locale) {
  const pattern = new RegExp(
    `!\\[([^\\]]+)\\]\\([^\\n)]*${name}\\.${locale}\\.svg\\)`,
    "u",
  );
  const match = source.match(pattern);
  assert.ok(match, `missing ${locale} image embed for ${name}`);
  return match[1];
}

test("ref-ontology-context-vs-rag pages preserve bilingual diagram parity", async () => {
  const [english, korean, manifest01, manifest02] = await Promise.all([
    readFile(new URL("src/content/docs/deck/ref-ontology-context-vs-rag.md", root), "utf8"),
    readFile(
      new URL("src/content/docs/ko/deck/ref-ontology-context-vs-rag.md", root),
      "utf8",
    ),
    loadManifest("fdai-ontology-context-rag-01"),
    loadManifest("fdai-ontology-context-rag-02"),
  ]);

  assert.equal(english.match(/!\[/gu)?.length, 2);
  assert.equal(korean.match(/!\[/gu)?.length, 2);

  assert.equal(
    manifest01.locales.en.alt,
    imageAlt(english, "fdai-ontology-context-rag-01", "en"),
  );
  assert.equal(
    manifest01.locales.ko.alt,
    imageAlt(korean, "fdai-ontology-context-rag-01", "ko"),
  );
  assert.equal(
    manifest02.locales.en.alt,
    imageAlt(english, "fdai-ontology-context-rag-02", "en"),
  );
  assert.equal(
    manifest02.locales.ko.alt,
    imageAlt(korean, "fdai-ontology-context-rag-02", "ko"),
  );

  // The `GET /ontology/graph` claim must stay aligned with the precise
  // wording established in the Round 6 fix to ontology-driven-automation.md:
  // a declaration-only projection, not an "aggregate operating-model status".
  assert.doesNotMatch(english, /aggregate operating-model status/u);
  assert.doesNotMatch(korean, /집계된 운영 모델 상태/u);
  assert.match(english, /declaration-only projection/u);
  assert.match(korean, /선언 전용 변환 결과/u);
});

test("diagram 01 (how FDAI references ontology data) has translated, toned nodes", async () => {
  const manifest = await loadManifest("fdai-ontology-context-rag-01");

  assert.equal(manifest.nodes.length, 10);
  assert.equal(manifest.edges.length, 9);

  for (const node of manifest.nodes) {
    assert.ok(node.tone, `node ${node.id} must declare a tone`);
  }

  // Every descriptive pipeline-stage label must be a real Korean
  // translation, not a copy of the English text - this page previously
  // shipped an untranslated .ko.svg for this diagram. The `c` node
  // (OperationalContextSnapshot) is a bare type-identifier label, matching
  // the sitewide convention for bare ObjectType/ActionType-style names
  // (e.g. `ActionType`), so it legitimately stays identical across locales.
  for (const node of manifest.nodes) {
    if (node.id === "c") {
      assert.equal(node.label.ko, "OperationalContextSnapshot");
      continue;
    }
    assert.notEqual(node.label.ko, node.label.en, `node ${node.id} label must be translated`);
  }

  // PostgreSQL storage must remain reachable from both the declarative
  // catalog-validation path and the approved-inventory-projection path, and
  // must feed the runtime materializer alongside the triggering event.
  const g = manifest.nodes.find((node) => node.id === "g");
  assert.equal(g.kind, "store");
  assert.equal(g.tone, "store");
  for (const [from, to] of [
    ["s", "v"],
    ["v", "g"],
    ["i", "p"],
    ["p", "g"],
    ["g", "m"],
    ["e", "m"],
    ["m", "c"],
    ["c", "f"],
    ["f", "d"],
  ]) {
    assert.ok(
      manifest.edges.some((edge) => edge.from === from && edge.to === to),
      `expected an edge from ${from} to ${to}`,
    );
  }

  for (const locale of ["en", "ko"]) {
    const svg = await loadSvg("fdai-ontology-context-rag-01", locale);
    assert.equal([...svg.matchAll(/data-node-id=/g)].length, manifest.nodes.length);
    assert.equal([...svg.matchAll(/data-edge-id=/g)].length, manifest.edges.length);
  }

  const koSvg = await loadSvg("fdai-ontology-context-rag-01", "ko");
  assert.match(koSvg, /Forseti 결정/u);
  assert.doesNotMatch(koSvg, /Forseti decision/u);
  assert.doesNotMatch(koSvg, /Approved inventory and operating model/u);
});

test("diagram 02 (how RAG fits beside the ontology) has translated, toned nodes", async () => {
  const manifest = await loadManifest("fdai-ontology-context-rag-02");

  assert.equal(manifest.nodes.length, 6);
  assert.equal(manifest.edges.length, 6);

  for (const node of manifest.nodes) {
    assert.ok(node.tone, `node ${node.id} must declare a tone`);
    assert.notEqual(node.label.ko, node.label.en, `node ${node.id} label must be translated`);
  }

  for (const locale of ["en", "ko"]) {
    const svg = await loadSvg("fdai-ontology-context-rag-02", locale);
    assert.equal([...svg.matchAll(/data-node-id=/g)].length, manifest.nodes.length);
    assert.equal([...svg.matchAll(/data-edge-id=/g)].length, manifest.edges.length);
  }

  const koSvg = await loadSvg("fdai-ontology-context-rag-02", "ko");
  assert.match(koSvg, /결정 또는 질문/u);
  assert.doesNotMatch(koSvg, /Decision or question/u);
  assert.doesNotMatch(koSvg, /RAG evidence/u);
});
