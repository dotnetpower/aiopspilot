const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const html = readFileSync(join(__dirname, "..", "incident-conversation.html"), "utf8");
const styles = readFileSync(join(__dirname, "..", "assets", "incident-conversation.css"), "utf8");
const script = readFileSync(join(__dirname, "..", "assets", "incident-conversation.js"), "utf8");

test("incident specimen owns a thin shell over shared semantic primitives", () => {
  assert.match(html, /assets\/calm-slate\.css/);
  assert.match(html, /assets\/incident-conversation\.css/);
  ["ic-header", "ic-scroll", "ic-messages", "ic-answer", "ic-composer", "cs-deck-user-bubble", "cs-control-textarea", "cs-control-button"]
    .forEach(role => assert.match(html, new RegExp(`class="[^"]*${role}`)));
  assert.match(html, /Design preview.*Synthetic records/);
  assert.doesNotMatch(html, /data-schema="3"|verified_semantic_result/);
});

test("incident narrative leads with historical facts and explicit uncertainty", () => {
  ["Open at last record", "Current status unknown", "Historical evidence", "Not live",
    "Customer impact", "Not established", "Not verified", "Response owner", "Not recorded"]
    .forEach(label => assert.ok(html.includes(label), label));
  assert.match(html, /The shadow evaluation found no usable alert channel\./);
  assert.match(html, /No probability estimate or complete root-cause claim/);
  assert.doesNotMatch(html, /No recorded evidence gaps\./);
  assert.match(html, /Analysis completed.*not incident resolution/);
});

test("three exact records never imply delivery or independent recovery", () => {
  ["68858", "68881", "68882"].forEach(id => {
    assert.match(html, new RegExp(`id="audit-${id}"`));
    assert.match(html, new RegExp(`href="#audit-${id}"`));
  });
  assert.equal((html.match(/id="audit-\d+"/g) || []).length, 3);
  assert.match(html, /Observation window: 3m 45s/);
  assert.match(html, /span between records, not the incident duration/);
  assert.match(html, /No human acknowledgement is included/);
  assert.match(html, /No current binding readback, delivery receipt, or recovery observation is included/);
  assert.match(html, /Dispatch alone is not success/);
});

test("technical evidence starts collapsed and every citation resolves", () => {
  for (const id of ["incident-timeline", "incident-evidence", "analysis-details"]) {
    const details = html.match(new RegExp(`<details[^>]*id="${id}"[^>]*>`));
    assert.ok(details, id);
    assert.doesNotMatch(details[0], /\sopen(?:\s|>|=)/);
  }
  const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map(match => match[1]));
  for (const [, id] of html.matchAll(/href="#([^"]+)"/g)) assert.ok(ids.has(id), id);
  assert.match(script, /while \(disclosure\)/);
  assert.match(script, /focusTarget\.focus/);
  assert.match(html, /10\.8 seconds/);
});

test("responsive and local-only interaction boundaries remain explicit", () => {
  assert.match(styles, /grid-template-rows: auto minmax\(0, 1fr\) auto/);
  assert.match(styles, /@media \(max-width: 680px\)/);
  assert.match(styles, /prefers-reduced-motion: reduce/);
  assert.match(styles, /:focus-visible/);
  assert.match(html, /maxlength="2000" required/);
  assert.match(script, /body\.textContent = text/);
  assert.match(script, /No request was sent and no incident state changed/);
  assert.doesNotMatch(script, /fetch\s*\(|XMLHttpRequest|WebSocket|EventSource|innerHTML\s*=/);
  assert.match(html, /Channel configuration and delivery retries are changes, not read-only checks/);
  assert.match(html, /This checklist grants no approval or execution authority/);
});

test("incident specimen keeps unique element ids", () => {
  const ids = Array.from(html.matchAll(/\sid="([^"]+)"/g), (match) => match[1]);
  const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
  assert.deepEqual(Array.from(new Set(duplicates)), []);
});
