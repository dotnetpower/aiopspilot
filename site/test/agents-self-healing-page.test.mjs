import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);
const agentNames = [
  "Odin",
  "Forseti",
  "Thor",
  "Var",
  "Vidar",
  "Huginn",
  "Heimdall",
  "Njord",
  "Freyr",
  "Loki",
  "Mimir",
  "Norns",
  "Muninn",
  "Saga",
  "Bragi",
];

test("agents and self-healing pages preserve bilingual diagram parity", async () => {
  const [english, korean, manifestSource] = await Promise.all([
    readFile(new URL("src/content/docs/concepts/agents-and-self-healing.md", root), "utf8"),
    readFile(new URL("src/content/docs/ko/concepts/agents-and-self-healing.md", root), "utf8"),
    readFile(
      new URL(
        "public/diagrams/generated/fdai-agents-and-self-healing-02.manifest.json",
        root,
      ),
      "utf8",
    ),
  ]);
  const manifest = JSON.parse(manifestSource);

  assert.equal(english.match(/!\[/gu)?.length, 2);
  assert.equal(korean.match(/!\[/gu)?.length, 2);
  assert.match(english, /fdai-agent-driven-runtime\.en\.svg/);
  assert.match(korean, /fdai-agent-driven-runtime\.ko\.svg/);
  assert.match(english, /fdai-agents-and-self-healing-02\.en\.svg/);
  assert.match(korean, /fdai-agents-and-self-healing-02\.ko\.svg/);
  assert.equal(manifest.version, 2);
  assert.equal(manifest.locales.en.alt, imageAlt(english, "en"));
  assert.equal(manifest.locales.ko.alt, imageAlt(korean, "ko"));
});

test("page and diagram expose all fixed agents without authority shortcuts", async () => {
  const [english, korean, manifestSource] = await Promise.all([
    readFile(new URL("src/content/docs/concepts/agents-and-self-healing.md", root), "utf8"),
    readFile(new URL("src/content/docs/ko/concepts/agents-and-self-healing.md", root), "utf8"),
    readFile(
      new URL(
        "public/diagrams/generated/fdai-agents-and-self-healing-02.manifest.json",
        root,
      ),
      "utf8",
    ),
  ]);
  const manifest = JSON.parse(manifestSource);
  const nodeIds = new Set(manifest.nodes.map((node) => node.id));
  const edgeIds = new Set(manifest.edges.map((edge) => edge.id));

  for (const agent of agentNames) {
    assert.match(english, new RegExp(`^\\| ${agent} \\|`, "mu"));
    assert.match(korean, new RegExp(`^\\| ${agent} \\|`, "mu"));
  }
  for (const node of ["odin", "forseti", "thor", "var", "vidar", "huginn", "heimdall", "njord", "freyr", "loki", "saga", "norns"]) {
    assert.ok(nodeIds.has(node), `missing accountable diagram node ${node}`);
  }
  assert.ok(edgeIds.has("flow-10b"), "denied no-op audit path is missing");
  assert.match(manifest.nodes.find((node) => node.id === "norns").label.en, /proposes candidate/u);
  assert.doesNotMatch(manifest.locales.ko.alt, /\b(?:discovery|coverage|failover)\b/iu);
  assert.match(english, /configured\s+and promoted approval channel/u);
  assert.match(korean, /구성되고 승격된 승인 채널/u);
});

function imageAlt(source, locale) {
  const pattern = new RegExp(
    `!\\[([^\\]]+)\\]\\([^\\n)]*fdai-agents-and-self-healing-02\\.${locale}\\.svg\\)`,
    "u",
  );
  const match = source.match(pattern);
  assert.ok(match, `missing ${locale} self-healing image`);
  return match[1];
}
