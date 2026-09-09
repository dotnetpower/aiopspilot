/** Slides 18-22: compare eligible candidates and record one accountable portfolio decision. */
import { slide } from "./value-prioritization-slide-kit.js";

export function buildValuePrioritizationPortfolio() {
  return [
    slide({
      index: 18,
      id: "selection-logic",
      chapter: 4,
      state: "CONTRACT",
      title: "점수화는 적격 후보에만 적용하는 마지막 비교 단계입니다",
      lead: "운영 계획은 필수 제약으로 후보를 제거하고, 지배되는 선택지를 정리한 뒤, 남은 부드러운 목표만 가중 비교합니다.",
      evidence: ["constitution", "planning"],
      takeaway: "포트폴리오 점수는 선택을 설명하는 보조 근거이며 승인, 승격, 실행 권한을 만들지 않습니다.",
      body: `
        <div class="vp-selection-logic-layout">
          <article class="eligibility" data-vp-node="eligible">
            <small>STAGE 01 · ELIGIBILITY</small>
            <strong data-vp-primary>필수 제약으로 제거</strong>
            <ul><li>안전과 보안</li><li>데이터 무결성과 복구</li><li>SLO와 영향 범위</li><li>근거 최신성과 완전성</li></ul>
            <b>실패한 후보는 보류 또는 제외</b>
          </article>
          <i class="vp-arrow" data-vp-link data-vp-from="eligible" data-vp-to="pareto" aria-hidden="true"></i>
          <article class="pareto" data-vp-node="pareto">
            <small>STAGE 02 · PARETO</small>
            <strong data-vp-primary>명백히 지배되는 선택지 제거</strong>
            <p>다른 후보가 모든 목표에서 같거나 더 낫고 한 목표에서 더 좋을 때만 제거합니다.</p>
            <b>이 단계는 승자를 고르지 않음</b>
          </article>
          <i class="vp-arrow" data-vp-link data-vp-from="pareto" data-vp-to="tradeoff" aria-hidden="true"></i>
          <article class="tradeoff" data-vp-node="tradeoff">
            <small>STAGE 03 · TRADE-OFF</small>
            <strong data-vp-primary>남은 목표의 절충 비교</strong>
            <p>배포가 정한 가중치와 영향도만 사용하고 근접한 결과는 사람 검토로 보냅니다.</p>
            <b>읽기와 시뮬레이션만 수행 · 상태 변경 권한 없음</b>
          </article>
        </div>`,
    }),
    slide({
      index: 19,
      id: "uncertainty",
      chapter: 4,
      state: "GUIDE",
      title: "관측, 추정, 알 수 없음을 같은 숫자로 만들지 않습니다",
      lead: "포트폴리오 표는 값의 크기뿐 아니라 근거 상태를 보여 줘야 과도한 정밀도와 낙관적 순위를 피할 수 있습니다.",
      evidence: ["constitution", "planning", "outcomes"],
      takeaway: "알 수 없음은 0점이 아닙니다. 판단에 필요한 관측을 정의한 뒤 보류 상태로 남깁니다.",
      body: `
        <div class="vp-uncertainty-spectrum">
          <article class="observed">
            <header><span>OBSERVED</span><strong data-vp-primary>관측됨</strong></header>
            <div class="vp-confidence-shape solid" aria-hidden="true"></div>
            <p>권위 있는 출처, 정확한 기준 시점, 완전성 증적이 있습니다.</p>
            <b>사용: 기준선과 현재 상태</b>
          </article>
          <article class="estimated">
            <header><span>ESTIMATED</span><strong data-vp-primary>범위로 추정됨</strong></header>
            <div class="vp-confidence-shape range" aria-hidden="true"></div>
            <p>모델과 가정, 예측 구간, 불확실성을 함께 표시합니다.</p>
            <b>사용: 시뮬레이션과 선택지 비교</b>
          </article>
          <article class="unknown">
            <header><span>UNKNOWN</span><strong data-vp-primary>알 수 없음</strong></header>
            <div class="vp-confidence-shape unknown-mark" aria-hidden="true">?</div>
            <p>출처가 없거나 오래됐거나 충돌해 값을 책임 있게 말할 수 없습니다.</p>
            <b>결과: 보완 작업과 재검토 시점</b>
          </article>
        </div>`,
    }),
    slide({
      index: 20,
      id: "worked-portfolio",
      chapter: 4,
      state: "EXAMPLE",
      title: "세 후보를 같은 렌즈로 비교하면 첫 검증 범위가 선명해집니다",
      lead: "아래 내용은 방법을 설명하기 위한 가상 사례입니다. 실제 조직의 후보, 점수, 운영 성과 또는 FDAI 배포 상태가 아닙니다.",
      evidence: ["constitution", "readiness", "metrics"],
      takeaway: "가치가 가장 커 보이는 후보보다 현재 근거로 안전하게 학습할 수 있는 후보가 먼저입니다.",
      body: `
        <div class="vp-worked-layout">
          <header><b>설명용 예시</b><span>정성 비교 · 실제 운영 근거 아님</span><strong>동일 렌즈: 가치 · 반복성 · 근거 · 안전 · 효과 관측</strong></header>
          <div class="vp-portfolio-head"><span>후보</span><span>가치 가설</span><span>현재 준비</span><span>핵심 경계</span><span>판정</span></div>
          <article class="now">
            <strong data-vp-primary>변경 정책 편차 검토</strong><span>수동 검토 대기 감소</span><span>규칙과 리비전 근거 있음</span><span>관찰 모드 · 변경 없음</span><b>NOW</b>
          </article>
          <article class="next">
            <strong data-vp-primary>유휴 리소스 조정</strong><span>단위 비용 개선 가능성</span><span>비용 관측자 보완 필요</span><span>SLO와 용량 보호</span><b>NEXT</b>
          </article>
          <article class="hold">
            <strong data-vp-primary>운영 데이터 저장소 장애 조치</strong><span>복구 시간 개선 가능성</span><span>훈련과 독립 효과 근거 부족</span><span>높은 영향 · 사람 승인</span><b>HOLD</b>
          </article>
          <footer><span>선정 이유</span><strong>현재 리비전과 정책으로 판단을 재생할 수 있고, 상태 변경 없이 품질을 비교할 수 있습니다.</strong></footer>
        </div>`,
    }),
    slide({
      index: 21,
      id: "portfolio-horizon",
      chapter: 4,
      state: "PROPOSAL",
      title: "포트폴리오는 이동 조건으로 관리합니다",
      lead: "후보를 영구 순위로 고정하지 않고, 근거와 안전 계약이 달라질 때 다시 이동할 수 있는 포트폴리오로 운영합니다.",
      evidence: ["readiness", "planning"],
      takeaway: "각 칸에는 후보 수보다 들어오는 조건, 나가는 조건, 책임자, 재검토 날짜가 더 중요합니다.",
      body: `
        <div class="vp-horizon-board">
          <article class="now"><small>NOW</small><strong data-vp-primary>관찰 모드 시작</strong><span>기준선, 근거, 책임자, 안전 계약이 준비됨</span><b>나가기: 비교 결과와 독립 검토</b></article>
          <article class="next"><small>NEXT</small><strong data-vp-primary>한두 가지 근거 보완</strong><span>가치는 분명하지만 관측자나 범위가 덜 닫힘</span><b>나가기: 차단 근거 해소</b></article>
          <article class="later"><small>LATER</small><strong data-vp-primary>의사결정 구조 재설계</strong><span>입력과 선택지가 아직 자주 바뀜</span><b>나가기: 반복 가능한 판단 계약</b></article>
          <article class="stop"><small>STOP</small><strong data-vp-primary>현재 범위에서 중단</strong><span>상위 제약 위반, 측정 불가, 가치 없음</span><b>다시 보기: 제약 또는 목표가 변경될 때</b></article>
          <div class="vp-horizon-axis"><span>지금 검증</span><i></i><span>근거를 보완</span><i></i><span>문제를 다시 정의</span><i></i><span>투자하지 않음</span></div>
        </div>`,
    }),
    slide({
      index: 22,
      id: "decision-memo",
      chapter: 4,
      state: "GUIDE",
      title: "선정과 보류, 제외 사유를 같은 문법으로 기록합니다",
      lead: "포트폴리오 결정은 누가 보더라도 같은 근거로 재현할 수 있어야 하며, 보류 후보에는 돌아올 조건이 있어야 합니다.",
      evidence: ["planning", "constitution"],
      takeaway: "좋은 결정 메모는 선택만 정당화하지 않고 제외된 대안과 다시 검토할 조건도 보존합니다.",
      body: `
        <div class="vp-memo-layout">
          <aside>
            <small>DECISION RECORD</small>
            <strong>한 줄 판정 문법</strong>
            <p><b>후보</b>를 <b>근거</b>와 <b>상위 제약</b>에 따라 <b>처분</b>하고, <b>재검토 조건</b>을 남깁니다.</p>
          </aside>
          <article>
            <header><b>설명용 예시</b><span>2026-09-09 · Portfolio review</span></header>
            <blockquote>변경 정책 편차 검토를 첫 관찰 모드 후보로 선택합니다.</blockquote>
            <dl>
              <div><dt>왜 지금</dt><dd>현재 규칙과 변경 리비전으로 같은 판단을 재생할 수 있습니다.</dd></div>
              <div><dt>무엇을 보호</dt><dd>아키텍처 제약, 변경 안전, 승인 분리를 유지합니다.</dd></div>
              <div><dt>무엇을 하지 않음</dt><dd>승인이나 리소스 변경을 이 워크숍 결정으로 허용하지 않습니다.</dd></div>
              <div><dt>보류 후보</dt><dd>비용 관측과 복구 훈련 근거가 준비되면 다시 검토합니다.</dd></div>
              <div><dt>다음 판단</dt><dd>관찰 결과와 안전 지표를 독립 검토해 유지, 보완, 중단을 결정합니다.</dd></div>
            </dl>
          </article>
        </div>`,
    }),
  ];
}
