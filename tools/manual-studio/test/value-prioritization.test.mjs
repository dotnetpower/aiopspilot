import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { access, readFile } from "node:fs/promises";
import { test } from "node:test";

import { buildValuePrioritizationDeck } from "../value-prioritization.js";

const root = new URL("../", import.meta.url);
const repositoryRoot = new URL("../../", root);

function content(slides) {
  return slides.map((slide) => `${slide.title}\n${slide.lead}\n${slide.content}`).join("\n");
}

test("value prioritization is a complete decision-oriented L200 deck", async () => {
  const slides = buildValuePrioritizationDeck();

  assert.equal(slides.length, 25);
  assert.equal(new Set(slides.map((slide) => slide.title)).size, 25);
  assert.equal(new Set(slides.map((slide) => slide.layout.split(" ")[0])).size, 25);
  assert.ok(slides.every((slide) => slide.layout.includes("deck-value-prioritization")));
  assert.deepEqual(
    Object.fromEntries([1, 2, 3, 4, 5].map((chapter) => [
      chapter,
      slides.filter((slide) => slide.priority.chapter === chapter).length,
    ])),
    { 1: 7, 2: 5, 3: 5, 4: 5, 5: 3 },
  );

  for (const slide of slides) {
    assert.ok(slide.priority.sources.length >= 1);
    for (const source of slide.priority.sources) {
      await access(new URL(source, repositoryRoot));
    }
  }
});

test("value prioritization cover stays sparse and title-led", () => {
  const [cover] = buildValuePrioritizationDeck();
  const plainText = `${cover.title} ${cover.lead} ${cover.content}`
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  assert.equal(cover.title, "Use Case &<br>Value Prioritization");
  assert.equal(cover.lead, "검증 가능한 첫 결정을 선택하는 포트폴리오 워크숍");
  assert.equal(cover.layout, "briefing-value-cover deck-value-prioritization");
  assert.ok(plainText.length < 180);
  assert.match(cover.content, /vp-cover-field/);
  assert.doesNotMatch(cover.content, /<(?:img|article|ol|ul|table|figure)\b/);
  assert.doesNotMatch(cover.content, /후보 정의|근거 기반 평가|포트폴리오 결정/);
});

test("every value-prioritization body slide has one visual, one takeaway, and evidence", () => {
  const [, ...slides] = buildValuePrioritizationDeck();

  for (const slide of slides) {
    assert.equal([...slide.content.matchAll(/<section class="vp-visual/g)].length, 1);
    assert.equal([...slide.content.matchAll(/<p class="vp-takeaway"/g)].length, 1);
    assert.equal([...slide.content.matchAll(/<small class="vp-source"/g)].length, 1);
    assert.match(slide.content, /class="vp-state" data-state=/);
    assert.match(slide.content, /title="docs\/(?:roadmap|user-guide)\//);
  }
});

test("value-prioritization story preserves evidence, authority, and measurement boundaries", () => {
  const slides = buildValuePrioritizationDeck();
  const text = content(slides);

  for (const marker of [
    "vp-selection-field",
    "vp-anatomy-strip",
    "vp-question-compass",
    "vp-domain-landscape",
    "vp-brief-sheet",
    "vp-baseline-compare",
    "vp-evidence-gate",
    "vp-evidence-clock",
    "vp-scope-graph",
    "vp-precedence",
    "vp-safeguard-passport",
    "vp-metric-system",
    "vp-guard-balance",
    "vp-repeatability-map",
    "vp-tier-ramp",
    "vp-authority-rows",
    "vp-selection-logic",
    "vp-uncertainty-spectrum",
    "vp-worked-portfolio",
    "vp-horizon-board",
    "vp-decision-memo",
    "vp-promotion-track",
    "vp-thirty-days",
    "vp-commitment",
  ]) {
    assert.match(text, new RegExp(marker));
  }

  assert.match(text, /무조치 기준선/);
  assert.match(text, /근거 준비도는 가중치가 아니라/);
  assert.match(text, /상위 제약을 통과한 선택지만/);
  assert.match(text, /일곱 안전장치/);
  assert.match(text, /업무 단위 비용/);
  assert.match(text, /자동 해결 비율/);
  assert.match(text, /MTTR/);
  assert.match(text, /변경 리드 타임/);
  assert.match(text, /사람 접점/);
  assert.match(text, /정확히 0이어야 하는 위반/);
  assert.match(text, /T2.*관찰 모드/s);
  assert.match(text, /가장 낮은 독립 상한/);
  assert.match(text, /읽기와 시뮬레이션만 수행 · 상태 변경 권한 없음/);
  assert.match(text, /알 수 없음은 0점이 아닙니다/);
  assert.match(text, /포트폴리오 선정은 관찰 시작 결정/);
  assert.match(text, /합성하지 않은 실제 운영 비교 집단/);
  assert.match(text, /워크숍 제안 · 30일/);
  assert.match(text, /Decision brief \+ Evidence map \+ Shadow review/);
});

test("value-prioritization examples are visibly bounded", () => {
  const slides = buildValuePrioritizationDeck();
  const byId = Object.fromEntries(slides.map((slide) => [slide.priority.id, slide]));

  for (const id of ["evidence-clock", "repeatability-map", "authority-ceiling", "worked-portfolio"]) {
    const slideText = `${byId[id].title} ${byId[id].lead} ${byId[id].content}`;
    assert.match(slideText, /예시/);
  }
  assert.match(content(slides), /실제 운영 측정값이 아니며/);
  assert.match(content(slides), /실제 조직의 측정값이 아닙니다/);
  assert.match(content(slides), /실제 운영 근거 아님/);
});

test("value-prioritization visual system meets the presentation typography contract", async () => {
  const commonCss = await readFile(new URL("value-prioritization.css", root), "utf8");
  const visualCss = await readFile(new URL("value-prioritization-visuals.css", root), "utf8");
  const portfolioCss = await readFile(new URL("value-prioritization-portfolio.css", root), "utf8");

  assert.match(commonCss, /slide-copy h2[\s\S]{0,220}font-size: 43px/);
  assert.match(commonCss, /slide-copy p[\s\S]{0,220}font-size: 24px/);
  assert.match(commonCss, /\[data-vp-primary\][\s\S]{0,100}font-size: 24px/);
  assert.match(commonCss, /\.vp-source[\s\S]{0,180}font-size: 13px/);
  assert.match(commonCss, /slide-copy h2[\s\S]{0,220}font-size: 78px/);
  assert.match(commonCss, /Minimal PowerPoint-style cover/);
  assert.match(visualCss, /\.vp-scope-graph/);
  assert.match(portfolioCss, /repeating-linear-gradient/);
  assert.match(portfolioCss, /print-color-adjust: exact/);

  for (const entry of ["index.html", "library.html"]) {
    const html = await readFile(new URL(entry, root), "utf8");
    assert.match(html, /href="value-prioritization\.css"/);
    assert.match(html, /href="value-prioritization-visuals\.css"/);
    assert.match(html, /href="value-prioritization-portfolio\.css"/);
  }
});

test("value-prioritization review records at least twenty digest-bound hardening rounds", async () => {
  const evidence = JSON.parse(await readFile(new URL("validation-evidence.json", root), "utf8"));
  const manual = evidence.manuals.find((item) => item.id === "value-prioritization");
  const review = manual.slideReviews.at(-1);
  const currentSlides = buildValuePrioritizationDeck();

  assert.equal(review.reviewId, "value-prioritization-editorial-rebuild-2026-09-09");
  assert.ok(review.critiqueRoundCount >= 20);
  assert.equal(review.critiqueRounds.length, review.critiqueRoundCount);
  assert.ok(review.critiqueRounds.every((round) => round.finding && round.correction && round.verified === "passed"));
  assert.equal(
    createHash("sha256").update(JSON.stringify(currentSlides)).digest("hex"),
    review.deckDigest,
  );
  for (const [file, digest] of Object.entries(review.sourceDigests)) {
    assert.equal(createHash("sha256").update(await readFile(new URL(file, root))).digest("hex"), digest, file);
  }
  assert.deepEqual(review.modesPassed, ["desktop", "tablet", "mobile", "fullscreen", "print"]);
  assert.equal(review.slideModeChecks, 125);
  assert.equal(review.primaryBodyFontFloorPx, 24);
  assert.ok(review.minimumTextContrastRatio >= 4.5);
  assert.equal(review.clippedTextFindings, 0);
  assert.equal(review.regionOverlapFindings, 0);
  assert.equal(review.failedRequests, 0);
  assert.equal(review.pageErrors, 0);
  assert.equal(review.pdf.pages, 25);
  assert.equal(review.pdf.mediaBoxesChecked, 25);
  assert.deepEqual(review.pdf.mediaBoxPoints, [1152, 648]);
  assert.equal(review.pdf.nonblankTextPages, 25);
});
