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

function tableRowNumbers(source) {
  return [...source.matchAll(/^\| ([0-9]+[a-z]?(?:\.[0-9]+)?) \|/gmu)].map(
    (match) => match[1],
  );
}

test("roadmap index page embeds the delivery-roadmap diagram with its canonical alt text", async () => {
  const [english, korean] = await Promise.all([
    readFile(new URL("../docs/roadmap/README.md", root), "utf8"),
    readFile(new URL("../docs/roadmap/README-ko.md", root), "utf8"),
  ]);
  const manifest = await loadManifest("fdai-delivery-roadmap");

  // Exactly one diagram is embedded on this page (a plain markdown image,
  // transformed to the interactive wrapper at build time by the
  // remarkFdaiDiagrams plugin).
  assert.equal(english.match(/fdai-delivery-roadmap\.en\.svg/gu)?.length, 1);
  assert.equal(korean.match(/fdai-delivery-roadmap\.ko\.svg/gu)?.length, 1);

  const enAltMatch = english.match(/!\[([^\]]+)\]\([^\n)]*fdai-delivery-roadmap\.en\.svg\)/u);
  const koAltMatch = korean.match(/!\[([^\]]+)\]\([^\n)]*fdai-delivery-roadmap\.ko\.svg\)/u);
  assert.ok(enAltMatch, "expected an English markdown embed for fdai-delivery-roadmap");
  assert.ok(koAltMatch, "expected a Korean markdown embed for fdai-delivery-roadmap");
  assert.equal(enAltMatch[1], manifest.locales.en.alt);
  assert.equal(koAltMatch[1], manifest.locales.ko.alt);
});

test("fdai-delivery-roadmap gives every process node a real, translated aria description", async () => {
  const manifest = await loadManifest("fdai-delivery-roadmap");
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
  }

  const [enSvg, koSvg] = await Promise.all([
    readFile(
      new URL("public/diagrams/generated/fdai-delivery-roadmap.en.svg", root),
      "utf8",
    ),
    readFile(
      new URL("public/diagrams/generated/fdai-delivery-roadmap.ko.svg", root),
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

test("roadmap reference index has no duplicate document ordinal numbers, and English/Korean tables agree", async () => {
  const [english, korean] = await Promise.all([
    readFile(new URL("../docs/roadmap/README.md", root), "utf8"),
    readFile(new URL("../docs/roadmap/README-ko.md", root), "utf8"),
  ]);

  const enNumbers = tableRowNumbers(english);
  const koNumbers = tableRowNumbers(korean);

  assert.ok(enNumbers.length > 100, "expected the full reference table to be present");
  assert.deepEqual(
    koNumbers,
    enNumbers,
    "Korean reference table must list the same document ordinals, in the same order, as English",
  );

  const duplicates = (numbers) => {
    const seen = new Set();
    const dupes = new Set();
    for (const n of numbers) {
      if (seen.has(n)) dupes.add(n);
      seen.add(n);
    }
    return [...dupes];
  };
  assert.deepEqual(
    duplicates(enNumbers),
    [],
    `English reference table must not reuse a document ordinal number: ${duplicates(enNumbers)}`,
  );
});
