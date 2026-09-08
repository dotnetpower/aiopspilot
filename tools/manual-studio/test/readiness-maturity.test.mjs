import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { access, readFile } from "node:fs/promises";
import { test } from "node:test";
import { buildReadinessMaturityDeck } from "../readiness-maturity.js";
import { illustrativeProfile, maturityLevels } from "../readiness-maturity-model.js";
import { workshopAgenda } from "../readiness-action-plan.js";
import { agendaRing, maturityPosition } from "../readiness-diagrams.js";

const root = new URL("../", import.meta.url);
const slides = buildReadinessMaturityDeck();
const byId = (id) => {
  const found = slides.find(slide => slide.readiness.id === id);
  assert.ok(found, `Missing readiness slide: ${id}`);
  return found;
};
const text = (slide) => `${slide.title}\n${slide.lead}\n${slide.content}`.replace(/<[^>]+>/g, " ");

test("readiness ships 32 unique slides across five decision-oriented chapters", async () => {
  const catalog = JSON.parse(await readFile(new URL("catalog.json", root), "utf8"));
  const manual = catalog.manuals.find(item => item.id === "readiness-maturity");
  const { additionalManualSlides } = await import("../manual-content.js");
  assert.equal(slides.length, 32);
  assert.equal(manual.slideCount, slides.length);
  assert.equal(manual.level, "L200");
  assert.equal(manual.stageId, "understand-align");
  assert.deepEqual(additionalManualSlides[manual.id], slides);
  assert.equal(new Set(slides.map(slide => slide.title)).size, 32);
  assert.equal(new Set(slides.map(slide => slide.readiness.id)).size, 32);
  assert.deepEqual([1, 2, 3, 4, 5].map(chapter => slides.filter(slide => slide.readiness.chapter === chapter).length), [6, 8, 7, 6, 5]);
  assert.deepEqual(buildReadinessMaturityDeck(), slides);
});

test("every readiness slide exposes one visual, traceable sources, and explicit teaching state", async () => {
  for (const slide of slides) {
    assert.equal([...slide.content.matchAll(/<section class="rm-visual /g)].length, 1);
    assert.match(slide.layout, /^briefing-readiness-[a-z-]+ deck-readiness-maturity$/);
    assert.match(slide.content, /class="rm-source" title="docs\/roadmap\//);
    assert.ok(slide.readiness.sources.length > 0);
    for (const source of slide.readiness.sources) {
      assert.ok(slide.content.includes(source));
      await access(new URL(`../../${source}`, root));
    }
    if (slide.readiness.id !== "cover") {
      assert.equal([...slide.content.matchAll(/class="rm-takeaway"/g)].length, 1);
      assert.ok(slide.content.includes(`data-state="${slide.readiness.state}"`));
    }
  }
  assert.ok(new Set(slides.map(slide => slide.readiness.visual)).size >= 25);
});

test("the illustrative scope never loses unknown targets or becomes an approval", () => {
  const coverage = byId("coverage");
  assert.equal(coverage.readiness.state, "EXAMPLE");
  assert.match(coverage.content, /확인 14개, 미매핑 3개, 접근 불가 2개, 오래된 근거 1개/);
  assert.equal(14 + 3 + 2 + 1, 20);
  assert.match(text(coverage), /14 \/ 20 = 70%/);
  assert.match(text(coverage), /제외 0개/);
  assert.match(text(coverage), /성숙도 점수나 파일럿 승인 기준이 아닙니다/);
  assert.match(text(byId("good-abstention")), /전체 영향은 아직 판단할 수 없습니다/);
  assert.match(text(byId("decision-memo")), /같은 20개 범위를 재평가/);
  assert.match(text(byId("decision-memo")), /모델 전송, 전체 영향 확정, 변경 승인과 실행/);
  assert.match(text(byId("gap-register")), /미매핑 3개[\s\S]*접근 불가 2개[\s\S]*오래된 근거 1개/);
});

test("time and semantic diagrams retain the documented direction and uncertainty", () => {
  const timeline = byId("time").content;
  const instants = ["09:50 UTC", "09:55 UTC", "09:58 UTC", "10:00 UTC"];
  const positions = instants.map(instant => timeline.indexOf(instant));
  assert.ok(positions.every(position => position >= 0));
  assert.deepEqual([...positions].sort((a, b) => a - b), positions);
  const graph = byId("semantic-spine").content;
  assert.match(graph, /BusinessService[\s\S]*implemented_by[\s\S]*Workload[\s\S]*workload_runs_on[\s\S]*Resource/);
  assert.equal([...graph.matchAll(/data-rm-from=/g)].length, 2);
  assert.doesNotMatch(graph, /business_service_contains_workload|workload_contains_resource/);
  assert.match(text(byId("semantic-spine")), /관계는 원인이나 권한이 아닙니다/);
});

test("AI readiness covers failure cases, minimization, fair evaluation, and unit economics", () => {
  const cases = byId("evaluation-cases");
  assert.equal(cases.readiness.state, "PROPOSAL");
  assert.equal([...cases.content.matchAll(/class="rm-entry rm-test-case"/g)].length, 6);
  for (const phrase of ["모호한 대상", "누락·만료·충돌", "권한 부족", "문서 속 지시", "지연·실패"]) {
    assert.ok(text(cases).includes(phrase), phrase);
  }
  assert.match(text(byId("decision-charter")), /필요 없는 데이터를 모으지/);
  assert.match(text(byId("data-lifecycle")), /충분히 비식별화할 수 없는 입력도 보내지 않습니다/);
  const baseline = text(byId("fair-baseline"));
  assert.match(baseline, /업무 진단[\s\S]*현재 운영 절차 vs 파일럿/);
  assert.match(baseline, /고정 기준 시스템 vs FDAI[\s\S]*단일 모델·비계층/);
  assert.match(baseline, /최소 표본은 30개[\s\S]*통계적 충분성이나 개선이 입증되지는 않습니다/);
  assert.match(baseline, /개선에 사용한 사례와 최종 평가 사례를 분리/);
  assert.match(text(byId("unit-economics")), /미완료 비용과 공통 간접비/);
  assert.match(text(byId("ai-lifecycle")), /자기 채점만으로 통과시키지 않습니다/);
});

test("maturity is a qualitative proposal with evidence, not an autonomy score", () => {
  assert.deepEqual(maturityLevels.map(level => level[0]), ["M1", "M2", "M3", "M4", "M5"]);
  assert.equal(illustrativeProfile.length, 6);
  assert.ok(illustrativeProfile.every(item => item.evidence && item.next));
  assert.equal(illustrativeProfile.filter(item => item.level === null).length, 1);
  const ladder = text(byId("maturity-ladder"));
  assert.match(ladder, /공인 등급이나 FDAI의 실행 권한 단계가 아닙니다/);
  assert.match(ladder, /낮은 등급이 아니라 미평가/);
  assert.match(ladder, /측정 구간, 필요한 표본, 허용 오류/);
  assert.match(text(byId("profile")), /70% 관계 확인 비율을 성숙도 점수로 환산한 결과가 아닙니다/);
  assert.match(text(byId("assessment-confidence")), /실행 적격성 판정이 아닙니다/);
  assert.match(text(byId("operating-rubric")), /AI 평가 담당자[\s\S]*운영 책임자/);
});

test("the action plan preserves read and mutation boundaries and a real workshop agenda", () => {
  const boundaries = byId("three-boundaries").content;
  const safeguards = boundaries.match(/<ol class="rm-safeguards">([\s\S]*?)<\/ol>/)?.[1];
  assert.ok(safeguards);
  assert.equal([...safeguards.matchAll(/<li>/g)].length, 7);
  assert.match(text(byId("three-boundaries")), /읽기는 접근·범위·근거·감사/);
  assert.match(text(byId("three-boundaries")), /독립된 관측자/);
  assert.match(text(byId("thirty-days")), /완료를 보장하는 일정이 아니라/);
  assert.equal(workshopAgenda.reduce((total, item) => total + item.minutes, 0), 90);
  assert.ok(workshopAgenda.every(item => item.activity && item.output));
  assert.doesNotMatch(slides.map(slide => slide.content).join(""), /<form|<input|<button|onclick=/);
});

test("readiness typography and styles are scoped and loaded by both viewers", async () => {
  const base = await readFile(new URL("readiness-maturity.css", root), "utf8");
  const visuals = await readFile(new URL("readiness-visuals.css", root), "utf8");
  const diagrams = await readFile(new URL("readiness-diagrams.css", root), "utf8");
  assert.match(base, /font-size: 43px/);
  assert.match(base, /font-size: 24px/);
  assert.match(base, /print-color-adjust: exact/);
  assert.match(base, /--rm-paper: #f5f4ee/);
  assert.match(visuals, /repeating-linear-gradient/);
  for (const css of [base, visuals, diagrams]) {
    for (const [, selector] of css.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/([^{}]+)\{/g)) {
      if (selector.trim().startsWith("@")) continue;
      for (const part of selector.split(",")) {
        assert.match(part.trim(), /^\.(?:manual-slide\.(?:deck-readiness-maturity|slide-briefing-readiness-cover)|deck-readiness-maturity)\b/);
      }
    }
  }
  for (const entryPoint of ["index.html", "library.html"]) {
    const html = await readFile(new URL(entryPoint, root), "utf8");
    assert.match(html, /href="readiness-maturity\.css"/);
    assert.match(html, /href="readiness-visuals\.css"/);
    assert.match(html, /href="readiness-diagrams\.css"/);
  }
});

test("the readiness cover is a subject and one-line subtitle, not a teaching slide", () => {
  const cover = byId("cover");
  assert.equal(cover.title, "AI / Data<br>Readiness & Maturity");
  assert.equal(cover.lead, "첫 검증을 위한 데이터와 운영 역량");
  assert.ok(text(cover).replace(/\s/g, "").length < 100);
  assert.doesNotMatch(cover.content, /<(?:img|svg|figure|article|ol|li|blockquote)\b/);
  assert.doesNotMatch(cover.content, /rm-cover-(?:image|index|kicker|note)|FROM CAPABILITY/);
});

test("premium diagrams express assessment and evidence rather than decorative scores", () => {
  assert.equal([...byId("six-dimensions").content.matchAll(/data-rm-from=/g)].length, 6);
  assert.equal([...byId("evidence-supply").content.matchAll(/data-rm-from=/g)].length, 4);
  const cycle = byId("ai-lifecycle").content;
  for (const direction of ["right", "down", "left", "up"]) assert.ok(cycle.includes(`data-rm-direction="${direction}"`));
  assert.equal([...byId("coverage").content.matchAll(/data-rm-unit=/g)].length, 20);
  assert.deepEqual([...byId("time").content.matchAll(/data-rm-minute="(\d+)"/g)].map(match => Number(match[1])), [0, 5, 8, 10]);
  assert.match(text(byId("time")), /5분 유효 기간을 늘리지 않습니다/);
  assert.match(text(byId("knowledge")), /읽기 권한[\s\S]*허용 집합 안에서 검색/);
  assert.match(text(byId("profile")), /서열 범주이며 간격은 수치 차이가 아닙니다/);
  assert.equal([...byId("profile").content.matchAll(/class="is-current" data-category=/g)].length, 5);
  assert.match(maturityPosition(null), /미평가 \/ 근거 요청/);
  assert.doesNotMatch(maturityPosition(null), /is-current|data-category=/);
  const ring = agendaRing(workshopAgenda);
  assert.deepEqual([...ring.matchAll(/data-rm-minutes="(\d+)"/g)].map(match => Number(match[1])), [15, 20, 25, 20, 10]);
  assert.equal([...ring.matchAll(/pathLength="90"/g)].length, 5);
  assert.equal([...byId("thirty-days").content.matchAll(/data-rm-checkpoint=/g)].length, 4);
  assert.match(text(byId("thirty-days")), /완료율이 아닙니다/);
});

test("the current readiness review is digest-bound and preserves the older 25-slide evidence", async () => {
  const evidence = JSON.parse(await readFile(new URL("validation-evidence.json", root), "utf8"));
  const manual = evidence.manuals.find(item => item.id === "readiness-maturity");
  assert.equal(manual.slideCount, 25);
  assert.equal(manual.validation.pdfPages, 25);
  assert.equal(manual.hardening.length, 3);
  assert.match(manual.historicalValidationScope, /previous 25-slide deck/);
  const review = manual.slideReviews.at(-1);
  assert.deepEqual(review.slides, Array.from({ length: 32 }, (_, index) => index + 1));
  assert.deepEqual(review.modesPassed, ["desktop", "tablet", "mobile", "fullscreen", "print"]);
  assert.equal(review.deckDigest, createHash("sha256").update(JSON.stringify(slides)).digest("hex"));
  for (const [file, digest] of Object.entries(review.sourceDigests)) {
    assert.equal(createHash("sha256").update(await readFile(new URL(file, root))).digest("hex"), digest, file);
  }
  assert.equal(review.slideModeChecks, 160);
  assert.equal(review.pdf.pages, 32);
  assert.equal(review.pdf.mediaBoxesChecked, 32);
  assert.deepEqual(review.pdf.mediaBoxPoints, [1152, 648]);
  assert.equal(review.clippedTextFindings, 0);
  assert.equal(review.regionOverlapFindings, 0);
  assert.ok(review.primaryBodyFontFloorPx >= 24);
  assert.ok(review.minimumTextContrastRatio >= 4.5);
  assert.ok(review.maximumConnectorGapPx <= 1);
});
