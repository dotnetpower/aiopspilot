import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { compileDiagram } from "../src/compiler.js";
import type { Locale } from "../src/model/types.js";
import { parseDiagram } from "../src/model/validate.js";

const lifecycleUrl = new URL(
  "../../../docs/diagrams/fdai-shadow-then-enforce-01.diagram.yaml",
  import.meta.url,
);
const perEventUrl = new URL(
  "../../../docs/diagrams/fdai-shadow-then-enforce-02.diagram.yaml",
  import.meta.url,
);

test("shadow-then-enforce lifecycle diagram only changes state through governance review", async () => {
  const spec = parseDiagram(await readFile(lifecycleUrl, "utf8"));

  assert.equal(spec.kind, "state");
  assert.deepEqual(
    spec.nodes.map((node) => node.id),
    ["observation", "evidence", "review", "enforcement"],
  );

  // Evidence alone never promotes; only a separate governance review can.
  assert.ok(
    spec.edges.some((edge) => edge.from === "evidence" && edge.to === "review"),
  );
  assert.ok(
    !spec.edges.some(
      (edge) => edge.from === "evidence" && edge.to === "enforcement",
    ),
    "evidence must not transition directly to enforcement, bypassing review",
  );
  // Rejection, stale evidence, or live regression return to observation, never
  // straight back to evidence (which would hide the review outcome).
  assert.ok(
    spec.edges.some((edge) => edge.from === "review" && edge.to === "observation"),
  );
  assert.ok(
    spec.edges.some((edge) => edge.from === "review" && edge.to === "enforcement"),
  );
  // Demotion (enforcement -> observation) stops future execution but the
  // diagram must not model a rollback edge for past runs (there is none to
  // remove; this assertion locks that absence in place).
  assert.ok(
    spec.edges.some((edge) => edge.from === "enforcement" && edge.to === "observation"),
  );
  assert.equal(spec.edges.length, 6);

  for (const node of spec.nodes) {
    assert.notEqual(
      node.label?.en,
      node.label?.ko,
      `node "${node.id}" label must be translated, not byte-identical English`,
    );
  }

  const artifacts = await compileDiagram(spec);
  for (const locale of ["en", "ko"] satisfies Locale[]) {
    const svg = artifacts.find(
      (artifact) => artifact.path === `fdai-shadow-then-enforce-01.${locale}.svg`,
    );
    assert.ok(svg);
    const source = svg.content.toString("utf8");
    assert.equal([...source.matchAll(/data-node-id=/g)].length, spec.nodes.length);
    assert.equal([...source.matchAll(/data-edge-id=/g)].length, spec.edges.length);
  }
});

test("shadow-then-enforce per-event diagram keeps risk/authority gating independent of lifecycle mode", async () => {
  const spec = parseDiagram(await readFile(perEventUrl, "utf8"));

  assert.equal(spec.kind, "flowchart");
  assert.deepEqual(
    spec.groups.map((group) => group.id),
    ["decision-context", "lifecycle-branch", "governed-outcome", "evidence-closure"],
  );
  assert.equal(spec.nodes.length, 11);
  assert.equal(spec.edges.length, 14);

  // Observation mode records the decision but never changes managed
  // resources: its only forward path is straight to the terminal audit.
  assert.ok(
    spec.edges.some(
      (edge) => edge.from === "observation-path" && edge.to === "terminal-audit",
    ),
  );
  assert.ok(
    !spec.edges.some((edge) => edge.from === "observation-path" && edge.to !== "terminal-audit"),
    "observation-path must not reach any node other than terminal-audit",
  );
  // Enforcement mode still passes through the shared risk/authority gate -
  // lifecycle mode does not bypass it.
  assert.ok(
    spec.edges.some(
      (edge) => edge.from === "lifecycle-mode" && edge.to === "risk-authority",
    ),
  );
  // Every terminal path (authorized execution, human approval, no change)
  // closes in the shared terminal audit record.
  for (const terminal of ["authorized-execution", "human-approval", "no-change"]) {
    assert.ok(
      spec.nodes.some((node) => node.id === terminal),
      `expected terminal node "${terminal}"`,
    );
  }
  assert.ok(
    spec.edges.some(
      (edge) => edge.from === "authorized-execution" && edge.to === "effect-verification",
    ),
    "authorized execution must require independent effect verification before audit",
  );
  assert.ok(
    spec.edges.some(
      (edge) => edge.from === "effect-verification" && edge.to === "terminal-audit",
    ),
  );
  assert.ok(
    spec.edges.some((edge) => edge.from === "no-change" && edge.to === "terminal-audit"),
  );
  assert.ok(
    !spec.edges.some(
      (edge) => edge.from === "authorized-execution" && edge.to === "terminal-audit",
    ),
    "authorized execution must not reach the terminal audit without passing through effect verification",
  );

  for (const node of spec.nodes) {
    assert.notEqual(
      node.label?.en,
      node.label?.ko,
      `node "${node.id}" label must be translated, not byte-identical English`,
    );
  }
  for (const group of spec.groups) {
    assert.notEqual(
      group.label?.en,
      group.label?.ko,
      `group "${group.id}" label must be translated, not byte-identical English`,
    );
  }

  const artifacts = await compileDiagram(spec);
  for (const locale of ["en", "ko"] satisfies Locale[]) {
    const svg = artifacts.find(
      (artifact) => artifact.path === `fdai-shadow-then-enforce-02.${locale}.svg`,
    );
    assert.ok(svg);
    const source = svg.content.toString("utf8");
    assert.equal([...source.matchAll(/data-node-id=/g)].length, spec.nodes.length);
    assert.equal([...source.matchAll(/data-edge-id=/g)].length, spec.edges.length);
    assert.equal(
      [...source.matchAll(/class="diagram-group\b/g)].length,
      spec.groups.length,
    );
  }
});
