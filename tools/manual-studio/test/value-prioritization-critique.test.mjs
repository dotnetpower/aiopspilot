import assert from "node:assert/strict";
import { test } from "node:test";

import { buildValuePrioritizationDeck } from "../value-prioritization.js";

const slides = buildValuePrioritizationDeck();
const byId = Object.fromEntries(slides.map((slide) => [slide.priority.id, slide]));
const text = (id) => `${byId[id].title} ${byId[id].lead} ${byId[id].content}`;

const rounds = [
  [
    "01 cover hierarchy",
    () => {
      assert.equal(byId.cover.layout, "briefing-value-cover deck-value-prioritization");
      assert.doesNotMatch(byId.cover.content, /<(?:img|article|ol|ul|table|figure)\b/);
      assert.match(byId.cover.title, /Use Case &<br>Value Prioritization/);
    },
  ],
  [
    "02 one accountable workshop decision",
    () => {
      assert.match(text("selection"), /첫 관찰 모드 후보 1건/);
      assert.match(text("commitment"), /오늘 결정할 것은 단 하나/);
    },
  ],
  [
    "03 decision type rather than project scope",
    () => {
      assert.match(text("decision-anatomy"), /프로젝트가 아니라 반복되는 의사결정 유형/);
      assert.match(text("decision-anatomy"), /무조치 기준선/);
    },
  ],
  [
    "04 five portfolio questions",
    () => {
      assert.equal((byId.questions.content.match(/data-vp-primary/g) ?? []).length, 5);
      assert.match(text("questions"), /결과를 독립적으로 확인/);
    },
  ],
  [
    "05 three operating domains stay distinct",
    () => {
      assert.match(text("domains"), /RESILIENCE/);
      assert.match(text("domains"), /CHANGE SAFETY/);
      assert.match(text("domains"), /COST GOVERNANCE/);
      assert.match(text("domains"), /성과 의미는 섞지 않습니다/);
    },
  ],
  [
    "06 candidate brief is decision-ready",
    () => {
      for (const field of ["운영 문제", "판단 문장", "정확한 범위", "무조치 기준선", "기대 효과", "보호 목표", "책임자", "재검토 시점"]) {
        assert.match(text("brief"), new RegExp(field));
      }
    },
  ],
  [
    "07 baseline is fair and explicit",
    () => {
      assert.match(text("baseline"), /같은 후보 자격/);
      assert.match(text("baseline"), /같은 측정 기간/);
      assert.match(text("baseline"), /같은 지표 정의/);
    },
  ],
  [
    "08 evidence readiness is an eligibility gate",
    () => {
      assert.match(text("evidence-gate"), /가중치가 아니라 포트폴리오의 입장 조건/);
      assert.equal((byId["evidence-gate"].content.match(/없으면 보류|오래되면 보류|다르면 보류|불완전하면 보류/g) ?? []).length, 4);
    },
  ],
  [
    "09 temporal evidence remains replayable",
    () => {
      for (const field of ["event_time", "effective_time", "recorded_time", "evidence_cutoff"]) {
        assert.match(text("evidence-clock"), new RegExp(field));
      }
      assert.match(text("evidence-clock"), /기존 결정을 수정하지 않습니다/);
    },
  ],
  [
    "10 topology preserves relationship direction",
    () => {
      assert.match(byId["scope-graph"].content, /data-vp-from="workload" data-vp-to="resource" data-vp-direction="left"/);
      assert.match(byId["scope-graph"].content, /data-vp-from="service" data-vp-to="workload" data-vp-direction="left"/);
      assert.match(byId["scope-graph"].content, /관계는 영향 탐색을 돕지만 원인을 자동으로 증명하지 않습니다/);
    },
  ],
  [
    "11 constitutional precedence comes before optimization",
    () => {
      const content = text("precedence");
      assert.ok(content.indexOf("안전 · 보안") < content.indexOf("비용 최적화"));
      assert.match(content, /가중치는 적격 후보/);
    },
  ],
  [
    "12 all seven safeguards remain visible",
    () => {
      const content = text("safeguards");
      for (const safeguard of ["중지 조건", "시험한 복구", "영향 범위", "모의 실행", "논리 대상 잠금", "중복 억제 키", "2단계 감사"]) {
        assert.match(content, new RegExp(safeguard));
      }
      assert.match(content, /7 \/ 7 확인 전 실행 불가/);
    },
  ],
  [
    "13 value metrics carry units and interpretation",
    () => {
      const content = text("metrics");
      for (const value of ["USD / 사건 · 변경 · 최적화", "완료 이벤트 / 전체 이벤트", "초 · 평균 + 중앙값 + p90", "이벤트 100건당 접점"]) {
        assert.ok(content.includes(value), value);
      }
      assert.match(content, /기준선과 처리군 · 기본 30일 또는 1회 고정 시나리오 재생/);
    },
  ],
  [
    "14 guard metrics cannot be traded away",
    () => {
      assert.equal((byId["guard-balance"].content.match(/<b>0<\/b>/g) ?? []).length, 4);
      assert.match(text("guard-balance"), /상쇄할 수 없습니다/);
    },
  ],
  [
    "15 repeatability and frequency remain separate",
    () => {
      assert.match(text("repeatability-map"), /반복 빈도/);
      assert.match(text("repeatability-map"), /판단 구조의 반복성/);
      assert.match(text("repeatability-map"), /실제 조직의 측정값이 아닙니다/);
    },
  ],
  [
    "16 tier targets are not reported as observed results",
    () => {
      assert.match(text("tier-fit"), /설계 목표 · 이벤트 비율/);
      assert.match(text("tier-fit"), /실제 운영 측정값이 아니며/);
      assert.match(text("tier-fit"), /T2.*관찰 모드/s);
    },
  ],
  [
    "17 authority stays independent from value",
    () => {
      assert.match(text("authority-ceiling"), /가장 낮은 허용 상한/);
      assert.match(text("authority-ceiling"), /권한 결정 방식을 설명하는 예시/);
      assert.match(text("authority-ceiling"), /사람의 요청도 독립된 상한을 높이지 못합니다/);
      assert.match(text("authority-ceiling"), /실제 실행 결정 아님/);
    },
  ],
  [
    "18 selection follows eligibility Pareto and trade-off order",
    () => {
      const content = text("selection-logic");
      assert.ok(content.indexOf("STAGE 01") < content.indexOf("STAGE 02"));
      assert.ok(content.indexOf("STAGE 02") < content.indexOf("STAGE 03"));
      assert.match(content, /읽기와 시뮬레이션만 수행 · 상태 변경 권한 없음/);
    },
  ],
  [
    "19 uncertainty never becomes a zero score",
    () => {
      assert.match(text("uncertainty"), /OBSERVED/);
      assert.match(text("uncertainty"), /ESTIMATED/);
      assert.match(text("uncertainty"), /UNKNOWN/);
      assert.match(text("uncertainty"), /알 수 없음은 0점이 아닙니다/);
    },
  ],
  [
    "20 worked portfolio labels synthetic examples",
    () => {
      assert.match(text("worked-portfolio"), /설명용 예시/);
      assert.match(text("worked-portfolio"), /실제 운영 근거 아님/);
      for (const decision of ["NOW", "NEXT", "HOLD"]) assert.match(text("worked-portfolio"), new RegExp(decision));
    },
  ],
  [
    "21 portfolio horizons have movement conditions",
    () => {
      const content = text("portfolio-horizon");
      for (const horizon of ["NOW", "NEXT", "LATER", "STOP"]) assert.match(content, new RegExp(horizon));
      assert.equal((byId["portfolio-horizon"].content.match(/나가기:/g) ?? []).length, 3);
      assert.match(content, /다시 보기:/);
    },
  ],
  [
    "22 final action separates observation from authority",
    () => {
      assert.match(text("promotion-path"), /포트폴리오 선정은 관찰 시작 결정/);
      assert.match(text("promotion-path"), /실제 변경 권한이나 미래 승격을 약속하지 않습니다/);
      assert.match(text("thirty-days"), /정책 위반, 대상 불일치, 근거 손실, 독립 검증 불가/);
      assert.match(text("commitment"), /Decision brief \+ Evidence map \+ Shadow review/);
    },
  ],
  [
    "23 independent editorial audit",
    () => {
      const allText = slides.map((item) => `${item.title} ${item.lead} ${item.content}`).join("\n");
      assert.match(text("evidence-gate"), /근거 준비도는 출처, 시간, 목적과 범위, 완전성을 모두 확인한 상태/);
      assert.match(text("metrics"), /지표별 표본 수 · 신뢰 구간 · 포함\/제외/);
      assert.match(text("metrics"), /확인된 복구만/);
      assert.match(text("metrics"), /병합된 변경만/);
      assert.match(text("authority-ceiling"), /등록된 작업 유형\(ActionType\)/);
      assert.match(text("promotion-path"), /합성하지 않은 실제 운영 비교 집단/);
      assert.doesNotMatch(allText, /한 리비전으로 승인합니다|승인과 결과 책임|비합성|Shadow review plan|사람 개입|계획과 시뮬레이션은 A0/);
    },
  ],
];

for (const [name, verify] of rounds) {
  test(`critique round ${name}`, verify);
}
