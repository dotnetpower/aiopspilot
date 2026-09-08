import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { buildOntologyFoundationDeck } from "../ontology-foundation.js";

const slides = buildOntologyFoundationDeck();

test("meaning branches represent alternatives rather than object relationships", () => {
  const { content } = slides[2];
  assert.match(content, /객체 사이의 관계가 아닙니다/);
  assert.match(content, /확인 전에는/);
  assert.match(content, /대상을 선택하지 않습니다/);
  const targets = [...content.matchAll(/data-branch-to="([^"]+)"/g)].map(([, target]) => target);
  assert.deepEqual(targets, ["business", "runtime", "provider"]);
  for (const target of targets) assert.ok(content.includes(`data-meaning-node="${target}"`));
  assert.doesNotMatch(content, /depends_on|implemented_by/);
});

test("freshness example places recorded arrival after expiry without reordering time meanings", () => {
  const { lead, content } = slides[18];
  assert.match(lead, /정해진 순서의 네 점이 아니라/);
  for (const field of ["event_time", "effective_time", "recorded_time", "fresh_until"]) {
    assert.ok(content.includes(field));
  }
  assert.match(content, /class="oe-freshness-chart"/);
  assert.match(content, /role="img"[^>]+도착 시점에는 재사용할 수 없습니다/);
  assert.match(content, /oe-fresh-window/);
  assert.match(content, /oe-expired-window/);
  for (const instant of ["10:00", "10:05", "10:06"]) assert.ok(content.includes(instant));
  assert.match(content, /예시/);
  assert.match(content, /새 관측으로 확인/);
});

test("ObjectSet graph binds two returned targets to one exact root", () => {
  const { content } = slides[28];
  const nodes = [...content.matchAll(/data-diagram-node="([^"]+)"/g)].map(([, node]) => node);
  assert.deepEqual(nodes, ["root", "database", "cache"]);
  const edges = [...content.matchAll(/data-from="([^"]+)" data-to="([^"]+)"/g)]
    .map(([, from, to]) => [from, to]);
  assert.deepEqual(edges, [["root", "database"], ["root", "cache"]]);
  assert.match(content, /depends_on \/ outgoing · 깊이 1/);
  assert.match(content, /점선 안: 반환 대상/);
  assert.match(content, /최대 100개/);
  assert.match(content, /현재 cutoff · 정확한 릴리스/);
  assert.match(content, /설명용 질의 영수증/);
  assert.match(content, /실행 권한은 없습니다/);
});

test("agent diagram connects distinct accountable roles only through the event bus", () => {
  const { content } = slides[30];
  const ports = [...content.matchAll(/data-agent="([^"]+)"/g)].map(([, agent]) => agent);
  assert.deepEqual(ports, ["Huginn", "Muninn", "Forseti", "Var", "Thor", "Heimdall", "Saga"]);
  assert.equal([...content.matchAll(/class="oe-bus-connector"/g)].length, ports.length);
  assert.equal([...content.matchAll(/data-diagram-bus/g)].length, 1);
  assert.match(content, /배치는 실행 순서가 아닙니다/);
  assert.match(content, /직접 호출·공유 가변 상태·자기 승인 없이/);
  assert.doesNotMatch(content, /class="oe-edge"|Var \/ Thor/);
});

test("effect comparison distinguishes terminal results from an unscorable hold", () => {
  const { content } = slides[33];
  const states = [...content.matchAll(/data-result-state="([^"]+)" data-closure="([^"]+)"/g)]
    .map(([, state, closure]) => [state, closure]);
  assert.deepEqual(states, [
    ["MATCHED", "terminal"], ["MISMATCHED", "terminal"],
    ["TIMED_OUT", "terminal"], ["UNSCORABLE", "pending"],
  ]);
  assert.match(content, /현재 시도만 기록/);
  assert.match(content, /새 인증 관측/);
  assert.match(content, /다음 실행을 자동 승인하지 않습니다/);
});

test("diagram labels keep presentation typography and non-color cues", async () => {
  const css = await readFile(new URL("../ontology-editorial.css", import.meta.url), "utf8");
  assert.match(css, /\.oe-inline-diagram text \{ stroke: none; \}/);
  assert.match(css, /\.oe-diagram-label \{[^}]+font-size: 28px/);
  assert.match(css, /\.oe-diagram-detail \{[^}]+font-size: 24px/);
  assert.match(css, /\.oe-expired-window \{[^}]+stroke-dasharray/);
  assert.match(css, /\.oe-query-scope \{[^}]+stroke-dasharray/);
  assert.match(css, /\.oe-open-outcome \{[^}]+border: 1px dashed/);
});
