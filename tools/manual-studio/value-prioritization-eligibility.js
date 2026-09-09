/** Slides 8-12: prove that a candidate is eligible before comparing value. */
import { slide } from "./value-prioritization-slide-kit.js";

export function buildValuePrioritizationEligibility() {
  return [
    slide({
      index: 8,
      id: "evidence-gate",
      chapter: 2,
      state: "CONTRACT",
      title: "근거 준비도는 가중치가 아니라 포트폴리오의 입장 조건입니다",
      lead: "근거 준비도는 출처, 시간, 목적과 범위, 완전성을 모두 확인한 상태입니다. 하나라도 부족하면 점수화하지 않고 보완으로 돌립니다.",
      evidence: ["constitution", "readiness"],
      takeaway: "준비되지 않은 후보는 낮은 점수가 아니라 명확한 보류 사유와 보완 작업을 받습니다.",
      body: `
        <div class="vp-evidence-gate-layout">
          <div class="vp-evidence-input"><small>CANDIDATE</small><strong>높은 기대 가치</strong><span>아직 자격을 의미하지 않습니다</span></div>
          <ol aria-label="근거 적격성 네 단계">
            <li><b>01</b><strong data-vp-primary>출처 권위</strong><span>인증된 생산자와 정확한 리비전</span><em>없으면 보류</em></li>
            <li><b>02</b><strong data-vp-primary>시간 적합성</strong><span>판단 시점과 최신성 정책 충족</span><em>오래되면 보류</em></li>
            <li><b>03</b><strong data-vp-primary>목적과 범위</strong><span>해당 판단에 허용된 대상과 용도</span><em>다르면 보류</em></li>
            <li><b>04</b><strong data-vp-primary>완전성</strong><span>누락과 관측 범위를 설명하는 증적</span><em>불완전하면 보류</em></li>
          </ol>
          <div class="vp-evidence-output"><small>ELIGIBLE</small><strong>가치 비교로 이동</strong><span>네 조건을 모두 통과한 후보만</span></div>
        </div>`,
    }),
    slide({
      index: 9,
      id: "evidence-clock",
      chapter: 2,
      state: "CONTRACT",
      title: "같은 사실도 언제 발생하고 기록됐는지에 따라 판단 가치가 달라집니다",
      lead: "이벤트 시각, 유효 구간, 기록 시각, 증거 기준 시점을 분리하면 늦게 도착한 자료가 과거 결정을 덮어쓰지 않습니다.",
      evidence: ["constitution", "ontology"],
      takeaway: "최신성은 화면에 보이는 마지막 갱신 시간이 아니라 출처별 정책과 판단 기준 시점으로 확인합니다.",
      body: `
        <div class="vp-evidence-clock-layout">
          <header><span>하나의 판단 맥락</span><strong>2026-09-09T09:15:00Z 기준</strong><small>설명용 예시</small></header>
          <div class="vp-clock-track">
            <article class="event"><small>09:08</small><strong data-vp-primary>event_time</strong><span>원천 사건이 발생한 시각</span></article>
            <i aria-hidden="true"></i>
            <article class="effective"><small>09:08-09:18</small><strong data-vp-primary>effective_time</strong><span>사실이 유효한 구간</span></article>
            <i aria-hidden="true"></i>
            <article class="recorded"><small>09:10</small><strong data-vp-primary>recorded_time</strong><span>FDAI가 사실을 기록한 시각</span></article>
            <i aria-hidden="true"></i>
            <article class="cutoff"><small>09:15</small><strong data-vp-primary>evidence_cutoff</strong><span>결정에 포함한 마지막 시각</span></article>
          </div>
          <div class="vp-clock-rules">
            <span><b>늦은 근거</b>새 리비전을 만들고 기존 결정을 수정하지 않습니다.</span>
            <span><b>만료된 근거</b>이전 ready 상태를 유지하지 않고 unknown으로 낮춥니다.</span>
            <span><b>충돌한 근거</b>평균으로 숨기지 않고 사람 검토로 보냅니다.</span>
          </div>
        </div>`,
    }),
    slide({
      index: 10,
      id: "scope-graph",
      chapter: 2,
      state: "CONTRACT",
      title: "대상과 관계를 확인해야 실제 영향 범위와 책임자를 찾을 수 있습니다",
      lead: "리소스 이름만으로 후보를 고르지 않습니다. 서비스, 워크로드, 목표, 소유권을 방향이 있는 관계로 따라갑니다.",
      evidence: ["ontology", "constitution"],
      takeaway: "관계가 없거나 조회가 잘리면 영향이 없다고 결론 내리지 않고 후보 범위를 줄이거나 보류합니다.",
      body: `
        <div class="vp-scope-graph-layout" role="img" aria-label="변경 후보에서 워크로드, 서비스, 목표와 책임자로 이어지는 방향성 관계">
          <article class="resource" data-vp-node="resource"><small>RESOURCE</small><strong data-vp-primary>변경 후보</strong><span>정확한 ID · revision 1842</span></article>
          <i class="vp-graph-link link-runs" data-vp-link data-vp-from="workload" data-vp-to="resource" data-vp-direction="left" aria-hidden="true"><span>runs_on</span></i>
          <article class="workload" data-vp-node="workload"><small>WORKLOAD</small><strong data-vp-primary>checkout-api</strong><span>배포와 운영의 단위</span></article>
          <i class="vp-graph-link link-implements" data-vp-link data-vp-from="service" data-vp-to="workload" data-vp-direction="left" aria-hidden="true"><span>implemented_by</span></i>
          <article class="service" data-vp-node="service"><small>BUSINESS SERVICE</small><strong data-vp-primary>결제 서비스</strong><span>중요도와 운영 범위</span></article>
          <i class="vp-graph-link link-objective" data-vp-link data-vp-from="service" data-vp-to="objective" aria-hidden="true"><span>governed_by</span></i>
          <article class="objective" data-vp-node="objective"><small>OBJECTIVE</small><strong data-vp-primary>가용성 목표</strong><span>측정 창과 허용 범위</span></article>
          <i class="vp-graph-link link-owner" data-vp-link data-vp-from="service" data-vp-to="owner" data-vp-direction="down" aria-hidden="true"><span>owned_by</span></i>
          <article class="owner" data-vp-node="owner"><small>OWNERSHIP</small><strong data-vp-primary>서비스 책임자</strong><span>운영 결과와 인계 책임</span></article>
          <aside><b>예시 토폴로지</b><span>관계는 영향 탐색을 돕지만 원인을 자동으로 증명하지 않습니다.</span></aside>
        </div>`,
    }),
    slide({
      index: 11,
      id: "precedence",
      chapter: 2,
      state: "CONTRACT",
      title: "상위 제약을 통과한 선택지만 가치와 비용을 비교합니다",
      lead: "낮은 비용이나 높은 속도가 안전, 복구, SLO, 변경 통제를 상쇄하지 못하도록 헌법의 우선순서를 먼저 적용합니다.",
      evidence: ["constitution", "planning"],
      takeaway: "가중치는 적격 후보의 부드러운 절충에만 사용하며, 실패한 필수 제약을 되살릴 수 없습니다.",
      body: `
        <div class="vp-precedence-layout">
          <ol>
            <li style="--vp-level:0"><b>01</b><strong data-vp-primary>안전 · 보안 · 규정 · 신원</strong><span>위반 후보 제거</span></li>
            <li style="--vp-level:1"><b>02</b><strong data-vp-primary>데이터 무결성 · 복구 가능성</strong><span>손실 또는 복구 불가 후보 제거</span></li>
            <li style="--vp-level:2"><b>03</b><strong data-vp-primary>SLO · RTO · RPO · 오류 예산</strong><span>보호 목표 위반 후보 제거</span></li>
            <li style="--vp-level:3"><b>04</b><strong data-vp-primary>변경 안전 · 영향 억제</strong><span>범위가 통제되지 않은 후보 제거</span></li>
            <li style="--vp-level:4"><b>05</b><strong data-vp-primary>성능 · 운영 효율</strong><span>적격 후보 안에서 비교</span></li>
            <li style="--vp-level:5"><b>06</b><strong data-vp-primary>비용 최적화</strong><span>적격 후보 안에서 비교</span></li>
          </ol>
          <div class="vp-precedence-key"><span class="hard">필수 제약</span><span class="soft">비교 가능한 목표</span><strong>위에서 아래로 적용</strong></div>
        </div>`,
    }),
    slide({
      index: 12,
      id: "safeguards",
      chapter: 2,
      state: "CONTRACT",
      title: "일곱 안전장치는 투자 이후가 아니라 후보 단계에서 확인합니다",
      lead: "상태를 바꾸는 후보는 실행 코드를 만들기 전에 중지, 복구, 영향, 검증, 잠금, 중복 억제, 감사 계약을 설명해야 합니다.",
      evidence: ["constitution", "execution"],
      takeaway: "안전장치 하나가 비어 있으면 실행 후보가 아니지만, 보완 계획을 가진 관찰 모드 진단은 계속할 수 있습니다.",
      body: `
        <div class="vp-safeguard-passport">
          <header><small>ACTION ELIGIBILITY</small><strong>상태 변경 후보의 안전 여권</strong><span>7 / 7 확인 전 실행 불가</span></header>
          <ol>
            <li><b>01</b><strong data-vp-primary>중지 조건</strong><span>기계가 평가할 수 있는 중단 기준</span></li>
            <li><b>02</b><strong data-vp-primary>시험한 복구</strong><span>되돌리기 또는 제한된 전진 복구</span></li>
            <li><b>03</b><strong data-vp-primary>영향 범위</strong><span>대상 수와 최대 범위를 계산</span></li>
            <li><b>04</b><strong data-vp-primary>성공한 모의 실행</strong><span>현재 계획과 대상 리비전에 결합</span></li>
            <li><b>05</b><strong data-vp-primary>논리 대상 잠금</strong><span>동시 작업과 오래된 대상 차단</span></li>
            <li><b>06</b><strong data-vp-primary>중복 억제 키</strong><span>재시도가 두 번째 효과를 만들지 않음</span></li>
            <li><b>07</b><strong data-vp-primary>2단계 감사</strong><span>실행 전 의도와 종료 결과를 분리 기록</span></li>
          </ol>
          <div class="vp-passport-verdict"><span>미충족</span><strong>실행 보류</strong><i></i><span>모두 충족</span><strong>별도 권한 심사</strong></div>
        </div>`,
    }),
  ];
}
