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

test("ontology-driven-automation pages preserve bilingual diagram parity", async () => {
  const [english, korean, manifest01, manifest02] = await Promise.all([
    readFile(new URL("src/content/docs/concepts/ontology-driven-automation.md", root), "utf8"),
    readFile(
      new URL("src/content/docs/ko/concepts/ontology-driven-automation.md", root),
      "utf8",
    ),
    loadManifest("fdai-ontology-driven-automation-01"),
    loadManifest("fdai-ontology-driven-automation-02"),
  ]);

  assert.equal(english.match(/!\[/gu)?.length, 2);
  assert.equal(korean.match(/!\[/gu)?.length, 2);

  assert.equal(
    manifest01.locales.en.alt,
    imageAlt(english, "fdai-ontology-driven-automation-01", "en"),
  );
  assert.equal(
    manifest01.locales.ko.alt,
    imageAlt(korean, "fdai-ontology-driven-automation-01", "ko"),
  );
  assert.equal(
    manifest02.locales.en.alt,
    imageAlt(english, "fdai-ontology-driven-automation-02", "en"),
  );
  assert.equal(
    manifest02.locales.ko.alt,
    imageAlt(korean, "fdai-ontology-driven-automation-02", "ko"),
  );

  // The "Denied" outcome added to diagram 2 must be reflected in both the
  // alt text and the surrounding prose in each locale.
  assert.match(manifest02.locales.en.alt, /\bDenied\b/u);
  assert.match(manifest02.locales.ko.alt, /거부됨/u);
  assert.match(english, /deny outright/u);
  assert.match(korean, /즉시 거부/u);
});

test("operating model diagram keeps the ObjectType identity chain intact", async () => {
  const manifest = await loadManifest("fdai-ontology-driven-automation-01");

  assert.equal(manifest.nodes.length, 8);
  assert.equal(manifest.edges.length, 6);

  // Every node must declare a tone so the rendered stages are visually
  // distinguishable, and none may carry a "When:" description - the
  // LinkType relationship belongs on the edge label instead. The
  // compiler back-fills an unset description with the node's own label,
  // so only a description that diverges from the label is a real one.
  for (const node of manifest.nodes) {
    assert.ok(node.tone, `node ${node.id} must declare a tone`);
    assert.ok(
      !node.description || node.description.en === node.label.en,
      `node ${node.id} must not carry a "When:" description`,
    );
  }

  const expectedEdges = [
    ["bc", "bs", "delivered_by"],
    ["bs", "w", "implemented_by"],
    ["w", "r", "workload_runs_on"],
    ["bs", "o", "service_has_service_objective"],
    ["bs", "ow", "service_owned_by"],
    ["rl", "at", "remediates"],
  ];
  for (const [from, to, label] of expectedEdges) {
    assert.ok(
      manifest.edges.some(
        (edge) => edge.from === from && edge.to === to && edge.label?.en === label,
      ),
      `expected edge ${from} -> ${to} labeled "${label}"`,
    );
  }

  for (const locale of ["en", "ko"]) {
    const svg = await loadSvg("fdai-ontology-driven-automation-01", locale);
    assert.equal([...svg.matchAll(/data-node-id=/g)].length, manifest.nodes.length);
    assert.equal([...svg.matchAll(/data-edge-id=/g)].length, manifest.edges.length);
  }
});

test("action instantiation diagram routes every safety outcome to the audit record", async () => {
  const manifest = await loadManifest("fdai-ontology-driven-automation-02");

  assert.equal(manifest.nodes.length, 9);
  assert.equal(manifest.edges.length, 12);

  const denied = manifest.nodes.find((node) => node.id === "d");
  assert.ok(denied);
  assert.equal(denied.label.en, "Denied");
  assert.equal(denied.label.ko, "거부됨");

  for (const source of ["g", "h"]) {
    assert.ok(
      manifest.edges.some((edge) => edge.from === source && edge.to === "d"),
      `expected an edge from ${source} to the denied outcome`,
    );
  }
  for (const source of ["d", "r"]) {
    assert.ok(
      manifest.edges.some((edge) => edge.from === source && edge.to === "a"),
      `expected ${source} to reach the audit and outcome node`,
    );
  }

  for (const node of manifest.nodes) {
    assert.ok(node.tone, `node ${node.id} must declare a tone`);
    // Every descriptive pipeline-stage label must be a real Korean
    // translation, not a copy of the English text - this page previously
    // shipped an untranslated .ko.svg for this diagram.
    assert.notEqual(node.label.ko, node.label.en, `node ${node.id} label must be translated`);
    if (node.description) {
      assert.notEqual(
        node.description.ko,
        node.description.en,
        `node ${node.id} description must be translated`,
      );
    }
  }

  for (const locale of ["en", "ko"]) {
    const svg = await loadSvg("fdai-ontology-driven-automation-02", locale);
    assert.equal([...svg.matchAll(/data-node-id=/g)].length, manifest.nodes.length);
    assert.equal([...svg.matchAll(/data-edge-id=/g)].length, manifest.edges.length);
    assert.match(svg, /data-node-id="d"/u);
    assert.match(svg, /class="diagram-legend/u);
  }

  const koSvg = await loadSvg("fdai-ontology-driven-automation-02", "ko");
  assert.match(koSvg, /거부됨/u);
  assert.match(koSvg, /검토 보류/u);
  assert.doesNotMatch(koSvg, /Held for review/u);
  assert.doesNotMatch(koSvg, /Executor/u);
});
