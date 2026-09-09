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

test("agents roadmap page embeds the agent-waves diagram with its canonical alt text", async () => {
  const [english, korean] = await Promise.all([
    readFile(new URL("../docs/roadmap/agents/README.md", root), "utf8"),
    readFile(new URL("../docs/roadmap/agents/README-ko.md", root), "utf8"),
  ]);
  const manifest = await loadManifest("fdai-agent-waves-01");

  // Exactly one diagram is embedded on this page (a plain markdown image,
  // transformed to the interactive wrapper at build time by the
  // remarkFdaiDiagrams plugin).
  assert.equal(english.match(/fdai-agent-waves-01\.en\.svg/gu)?.length, 1);
  assert.equal(korean.match(/fdai-agent-waves-01\.ko\.svg/gu)?.length, 1);

  const enAltMatch = english.match(/!\[([^\]]+)\]\([^\n)]*fdai-agent-waves-01\.en\.svg\)/u);
  const koAltMatch = korean.match(/!\[([^\]]+)\]\([^\n)]*fdai-agent-waves-01\.ko\.svg\)/u);
  assert.ok(enAltMatch, "expected an English markdown embed for fdai-agent-waves-01");
  assert.ok(koAltMatch, "expected a Korean markdown embed for fdai-agent-waves-01");
  assert.equal(enAltMatch[1], manifest.locales.en.alt);
  assert.equal(koAltMatch[1], manifest.locales.ko.alt);
});

test("fdai-agent-waves-01 gives every process node a real, translated aria description", async () => {
  const manifest = await loadManifest("fdai-agent-waves-01");
  const processNodes = manifest.nodes.filter((node) => node.kind === "process");
  assert.ok(processNodes.length >= 9);

  for (const node of processNodes) {
    for (const locale of ["en", "ko"]) {
      assert.ok(
        node.description?.[locale],
        `node "${node.id}" must declare its own ${locale} description so the renderer does not echo the label as a redundant aria-label`,
      );
      assert.notEqual(
        node.description[locale],
        node.label[locale],
        `node "${node.id}" description must not merely repeat its ${locale} label`,
      );
    }

    // Regression guard for the Round 11 defect: the Korean node description
    // was a byte-identical copy of the English one for all 9 nodes. Guard
    // against that regressing silently for every node with non-trivial
    // (non-acronym) prose content.
    assert.notEqual(
      node.description.en,
      node.description.ko,
      `node "${node.id}" Korean description must be a real translation, not a byte-identical copy of the English description`,
    );
  }

  // Same regression guard for the diagram's own title: it must not be a
  // byte-identical English copy under the Korean locale.
  assert.notEqual(
    manifest.locales.en.title,
    manifest.locales.ko.title,
    "diagram title must be translated for the Korean locale, not a byte-identical copy of English",
  );

  const [enSvg, koSvg] = await Promise.all([
    readFile(
      new URL("public/diagrams/generated/fdai-agent-waves-01.en.svg", root),
      "utf8",
    ),
    readFile(
      new URL("public/diagrams/generated/fdai-agent-waves-01.ko.svg", root),
      "utf8",
    ),
  ]);
  for (const node of processNodes) {
    const echoedEn = `${node.label.en}. ${node.label.en}`;
    const echoedKo = `${node.label.ko}. ${node.label.ko}`;
    assert.ok(
      !enSvg.includes(`aria-label="${echoedEn}"`),
      `rendered SVG must not echo node "${node.id}"'s English label as its own description`,
    );
    assert.ok(
      !koSvg.includes(`aria-label="${echoedKo}"`),
      `rendered Korean SVG must not echo node "${node.id}"'s Korean label as its own description`,
    );
  }
});

test("agents roadmap page implementation-status table links resolve to real headings, not the wrong owner document", async () => {
  const english = await readFile(new URL("../docs/roadmap/agents/README.md", root), "utf8");
  const korean = await readFile(new URL("../docs/roadmap/agents/README-ko.md", root), "utf8");

  // Regression guard for the Round 11 defect: the "Live KPI validation and
  // enforce promotion" row linked to `agent-pantheon.md#implementation-status`,
  // a heading that does not exist in that file. The correct owner document
  // is `agent-pantheon-implementation.md`.
  assert.ok(
    english.includes("agent-pantheon-implementation.md#implementation-status"),
    "English page must link the KPI-validation row to agent-pantheon-implementation.md, not agent-pantheon.md",
  );
  assert.ok(
    !/\]\(agent-pantheon\.md#implementation-status\)/u.test(english),
    "English page must not link directly to the non-existent agent-pantheon.md#implementation-status anchor",
  );
  assert.ok(
    korean.includes("agent-pantheon-implementation-ko.md#구현-상태"),
    "Korean page must link the KPI-validation row to agent-pantheon-implementation-ko.md, not agent-pantheon-ko.md",
  );
  assert.ok(
    !/\]\(agent-pantheon-ko\.md#구현-상태\)/u.test(korean),
    "Korean page must not link directly to the non-existent agent-pantheon-ko.md#구현-상태 anchor",
  );
});

test("agents roadmap page security-severity table does not claim a fixed time window for the count-bounded buffer", async () => {
  const english = await readFile(new URL("../docs/roadmap/agents/README.md", root), "utf8");

  // Regression guard for the Round 11 defect: the severity table claimed a
  // "five minutes" time window and "unusual hours" detection, neither of
  // which exists in Heimdall's actual severity-classification code (a
  // count-bounded deque, not a time-bounded one).
  assert.ok(
    !english.includes("five minutes"),
    "severity table must not re-introduce the false five-minute time-window claim",
  );
  assert.ok(
    !english.includes("unusual hours"),
    "severity table must not re-introduce the false unusual-hours detection claim",
  );
});
