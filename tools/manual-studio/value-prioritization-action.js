/** Slides 23-25: convert the selected candidate into a bounded first validation. */
import { slide } from "./value-prioritization-slide-kit.js";

export function buildValuePrioritizationAction() {
  return [
    slide({
      index: 23,
      id: "promotion-path",
      chapter: 5,
      state: "STATUS",
      title: "선정된 후보는 관찰 모드에서 가치와 안전을 함께 검증합니다",
      lead: "새 기능은 판단과 기록부터 시작합니다. 적용 모드는 별도의 승격 근거와 권한 심사를 통과한 뒤에만 검토합니다.",
      evidence: ["constitution", "execution", "metrics"],
      takeaway: "포트폴리오 선정은 관찰 시작 결정이며, 실제 변경 권한이나 미래 승격을 약속하지 않습니다.",
      body: `
        <div class="vp-promotion-layout">
          <div class="vp-promotion-track">
            <article data-vp-node="baseline"><small>01 · BASELINE</small><strong data-vp-primary>현재 운영 측정</strong><span>같은 자격 규칙과 지표 정의</span><b>구현된 측정 계약</b></article>
            <i class="vp-arrow" data-vp-link data-vp-from="baseline" data-vp-to="shadow" aria-hidden="true"></i>
            <article data-vp-node="shadow"><small>02 · SHADOW</small><strong data-vp-primary>판단과 기록</strong><span>실제 상태 변경 없이 결과 비교</span><b>새 기능의 기본 모드</b></article>
            <i class="vp-arrow" data-vp-link data-vp-from="shadow" data-vp-to="review" aria-hidden="true"></i>
            <article data-vp-node="review"><small>03 · REVIEW</small><strong data-vp-primary>독립 승격 검토</strong><span>표본, 정확성, 안전 지표, 효과 근거</span><b>사람의 별도 결정</b></article>
            <i class="vp-arrow" data-vp-link data-vp-from="review" data-vp-to="mode" aria-hidden="true"></i>
            <article data-vp-node="mode"><small>04 · MODE</small><strong data-vp-primary>유지 또는 제한적 적용</strong><span>현재 위험과 권한을 매번 다시 확인</span><b>회귀 시 관찰 모드로 강등</b></article>
          </div>
          <div class="vp-promotion-status">
            <span><b>현재 구현</b>결정론적 측정과 승격 평가</span>
            <span><b>열린 근거</b>합성하지 않은 실제 운영 비교 집단</span>
            <span><b>불변 경계</b>T2는 관찰 모드 상한</span>
          </div>
        </div>`,
    }),
    slide({
      index: 24,
      id: "thirty-days",
      chapter: 5,
      state: "PROPOSAL",
      title: "첫 30일은 기능 개발보다 비교 가능한 근거를 만드는 데 사용합니다",
      lead: "아래 일정은 워크숍 제안입니다. 조직의 변경 주기와 표본 발생 속도에 맞춰 기간을 조정하되 종료 조건은 유지합니다.",
      evidence: ["metrics", "readiness", "planning"],
      takeaway: "30일의 성공은 자동 실행이 아니라 재현 가능한 후보 정의와 다음 투자 결정을 위한 근거 묶음입니다.",
      body: `
        <div class="vp-thirty-days-plan">
          <header><b>워크숍 제안 · 30일</b><span>기간은 제안이며 운영 성과가 아닙니다</span></header>
          <ol>
            <li><small>DAY 01-05</small><strong data-vp-primary>결정 고정</strong><span>대상, 무조치 기준선, 보호 목표, 책임자를 합의하고 한 리비전으로 고정합니다.</span><em>산출물 · Decision brief</em></li>
            <li><small>DAY 06-10</small><strong data-vp-primary>근거 연결</strong><span>출처, 시간, 완전성, 관계, 독립 관측 창을 검증합니다.</span><em>산출물 · Evidence map</em></li>
            <li><small>DAY 11-20</small><strong data-vp-primary>관찰 모드 비교</strong><span>실제 상태를 바꾸지 않고 사람의 판단과 FDAI 제안을 같은 규약으로 비교합니다.</span><em>산출물 · Shadow review</em></li>
            <li><small>DAY 21-30</small><strong data-vp-primary>포트폴리오 재판정</strong><span>유지, 보완, 중단을 결정하고 적용 모드는 별도 심사로 남깁니다.</span><em>산출물 · Decision memo</em></li>
          </ol>
          <footer><span>중단 조건</span><strong>정책 위반, 대상 불일치, 근거 손실, 독립 검증 불가가 나타나면 다음 단계로 이동하지 않습니다.</strong></footer>
        </div>`,
    }),
    slide({
      index: 25,
      id: "commitment",
      chapter: 5,
      state: "DECISION",
      title: "오늘 결정할 것은 단 하나입니다",
      lead: "어떤 반복 의사결정을, 누구의 책임 아래, 어떤 근거로 관찰하기 시작할지 합의합니다.",
      evidence: ["constitution", "planning", "metrics"],
      takeaway: "결정이 끝나면 선택 후보와 보류 후보 모두 책임자, 다음 근거, 재검토 날짜를 갖습니다.",
      body: `
        <div class="vp-commitment-layout">
          <section>
            <small>THE DECISION</small>
            <blockquote>어떤 판단 하나를<br>첫 관찰 모드 후보로<br>선택하시겠습니까?</blockquote>
            <p>범위를 작게 시작하고, 근거를 크게 남깁니다.</p>
          </section>
          <ol aria-label="워크숍 종료 전 확인할 다섯 가지">
            <li><b>01</b><span>반복되는 의사결정 유형</span><strong>한 문장</strong></li>
            <li><b>02</b><span>정확한 대상과 하지 않을 일</span><strong>한 범위</strong></li>
            <li><b>03</b><span>무조치 기준선과 기대 효과</span><strong>한 비교</strong></li>
            <li><b>04</b><span>근거 출처와 독립 관측자</span><strong>한 증거 지도</strong></li>
            <li><b>05</b><span>책임자와 재검토 날짜</span><strong>한 약속</strong></li>
          </ol>
          <footer><span>워크숍 산출물</span><strong>Decision brief + Evidence map + Shadow review</strong></footer>
        </div>`,
    }),
  ];
}
