import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("architecture pages keep localized static fallbacks", async () => {
  const [english, korean] = await Promise.all([
    readFile(new URL("src/content/docs/architecture.md", root), "utf8"),
    readFile(new URL("src/content/docs/ko/architecture.md", root), "utf8"),
  ]);

  assert.match(english, /diagrams\/generated\/fdai-system-overview\.manifest\.json/);
  assert.match(
    english,
    /diagrams\/generated\/fdai-conceptual-control-loop\.manifest\.json/,
  );
  assert.match(english, /fdai-system-overview\.en\.svg/);
  assert.match(english, /fdai-conceptual-control-loop\.en\.svg/);
  assert.match(english, /locale="en"/);
  assert.match(korean, /diagrams\/generated\/fdai-system-overview\.ko\.svg/);
  assert.match(korean, /fdai-conceptual-control-loop\.ko\.svg/);
  assert.match(korean, /locale="ko"/);
});

test("generated viewer and bilingual manifest are present", async () => {
  const [viewer, manifestSource, conceptualManifestSource] = await Promise.all([
    readFile(new URL("public/diagrams/architecture-diagram.js", root), "utf8"),
    readFile(
      new URL(
        "public/diagrams/generated/fdai-system-overview.manifest.json",
        root,
      ),
      "utf8",
    ),
    readFile(
      new URL(
        "public/diagrams/generated/fdai-conceptual-control-loop.manifest.json",
        root,
      ),
      "utf8",
    ),
  ]);
  const manifest = JSON.parse(manifestSource);
  const conceptualManifest = JSON.parse(conceptualManifestSource);

  assert.match(viewer, /fdai-architecture-diagram/);
  assert.equal(manifest.assets.en.svg, "fdai-system-overview.en.svg");
  assert.equal(manifest.assets.ko.svg, "fdai-system-overview.ko.svg");
  assert.ok(manifest.nodes.length > 10);
  assert.equal(
    conceptualManifest.assets.ko.svg,
    "fdai-conceptual-control-loop.ko.svg",
  );
  assert.ok(conceptualManifest.nodes.some((node) => node.content?.length));
});

test("diagram gallery publishes every visual strategy example", async () => {
  const gallery = await readFile(
    new URL("src/content/docs/diagram-gallery.md", root),
    "utf8",
  );
  const diagramIds = [
    "fdai-conceptual-control-loop",
    "fdai-delivery-roadmap",
    "fdai-decision-mix",
    "fdai-assurance-radar",
    "fdai-capability-quadrant",
    "fdai-governance-kanban",
    "fdai-evidence-sankey",
  ];

  for (const diagramId of diagramIds) {
    assert.match(gallery, new RegExp(`${diagramId}\\.manifest\\.json`));
    const manifest = JSON.parse(
      await readFile(
        new URL(`public/diagrams/generated/${diagramId}.manifest.json`, root),
        "utf8",
      ),
    );
    assert.ok(manifest.nodes.length > 0);
  }
});

test("diagram gallery embed alt text matches each diagram's own canonical alt", async () => {
  const [english, korean] = await Promise.all([
    readFile(new URL("src/content/docs/diagram-gallery.md", root), "utf8"),
    readFile(new URL("src/content/docs/ko/diagram-gallery.md", root), "utf8"),
  ]);
  const diagramIds = [
    "fdai-conceptual-control-loop",
    "fdai-delivery-roadmap",
    "fdai-decision-mix",
    "fdai-assurance-radar",
    "fdai-capability-quadrant",
    "fdai-governance-kanban",
    "fdai-evidence-sankey",
  ];

  for (const diagramId of diagramIds) {
    const manifest = JSON.parse(
      await readFile(
        new URL(`public/diagrams/generated/${diagramId}.manifest.json`, root),
        "utf8",
      ),
    );
    const escape = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

    assert.match(
      english,
      new RegExp(`${diagramId}\\.en\\.svg" alt="${escape(manifest.locales.en.alt)}"`),
      `English gallery embed for ${diagramId} must reuse the diagram's own canonical alt text`,
    );
    assert.match(
      korean,
      new RegExp(`${diagramId}\\.ko\\.svg" alt="${escape(manifest.locales.ko.alt)}"`),
      `Korean gallery embed for ${diagramId} must reuse the diagram's own canonical alt text`,
    );
  }
});

test("diagram gallery's solely-owned diagrams give every node a real, translated aria description", async () => {
  const solelyOwnedDiagramIds = [
    "fdai-decision-mix",
    "fdai-assurance-radar",
    "fdai-capability-quadrant",
    "fdai-governance-kanban",
    "fdai-evidence-sankey",
  ];

  for (const diagramId of solelyOwnedDiagramIds) {
    const manifest = JSON.parse(
      await readFile(
        new URL(`public/diagrams/generated/${diagramId}.manifest.json`, root),
        "utf8",
      ),
    );

    for (const node of manifest.nodes) {
      assert.notEqual(
        node.label.ko,
        node.label.en,
        `${diagramId} node "${node.id}" must have a translated Korean label, not a copy of the English label`,
      );

      for (const locale of ["en", "ko"]) {
        assert.ok(
          node.description?.[locale],
          `${diagramId} node "${node.id}" must declare its own ${locale} description so the renderer does not echo the label as a redundant aria-label`,
        );
        assert.notEqual(
          node.description[locale],
          node.label[locale],
          `${diagramId} node "${node.id}" description must not merely repeat its ${locale} label`,
        );
      }

      const [enSvg, koSvg] = await Promise.all([
        readFile(
          new URL(`public/diagrams/generated/${diagramId}.en.svg`, root),
          "utf8",
        ),
        readFile(
          new URL(`public/diagrams/generated/${diagramId}.ko.svg`, root),
          "utf8",
        ),
      ]);
      const echoedLabel = `${node.label.en}. ${node.label.en}`;
      assert.ok(
        !enSvg.includes(`aria-label="${echoedLabel}"`),
        `${diagramId} rendered SVG must not echo node "${node.id}"'s label as its own description`,
      );
      assert.ok(
        !koSvg.includes(`aria-label="${node.label.ko}. ${node.label.ko}"`),
        `${diagramId} rendered Korean SVG must not echo node "${node.id}"'s label as its own description`,
      );
    }
  }
});
