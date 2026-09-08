const sources = {
  constitution: "docs/roadmap/architecture/fdai-constitution.md",
  execution: "docs/roadmap/decisioning/execution-model.md",
  actionOntology: "docs/roadmap/decisioning/action-ontology.md",
  metrics: "docs/roadmap/architecture/goals-and-metrics.md",
  ontology: "docs/roadmap/architecture/operating-ontology.md",
  operator: "docs/roadmap/operations/operator-initiated-sre-and-arb.md",
  pantheon: "docs/roadmap/agents/agent-pantheon.md",
  llmStrategy: "docs/roadmap/architecture/llm-strategy.md",
  security: "docs/roadmap/architecture/security-and-identity.md",
  deployment: "docs/roadmap/deployment/deployment.md",
  standingAuthority: "docs/roadmap/decisioning/escalation-and-standing-authority.md",
};

const chapters = {
  today: "지금 운영자가 겪는 부담",
  scenes: "달라질 수 있는 하루",
  boundary: "안전 경계와 첫 선택",
};

function sourceList(...items) {
  return items.map((item) => sources[item]);
}

function slide({ index, state, chapter, title, lead, layout, content, source, sourceLabel, statusLabel }) {
  const number = String(index).padStart(2, "0");
  return {
    eyebrow: `${number} / ${statusLabel(state)}`,
    title,
    lead,
    layout: `briefing-${layout} deck-art-of-possible`,
    content: `
      <div class="briefing-status-row">
        <span class="manual-status" data-state="${state}" aria-label="설계 상태: ${statusLabel(state)}">${statusLabel(state)}</span>
        <span>${chapter} · ${number} / 10</span>
      </div>
      ${content}
      ${sourceLabel(source)}`,
  };
}

export function buildArtOfPossibleDeck({ sourceLabel, statusLabel }) {
  return [
    {
      brandLogo: "assets/microsoft-logo.png",
      eyebrow: "FUTURE EXPERIENCE",
      deckTitle: "FDAI / FUTURE EXPERIENCE",
      title: "Art of the Possible",
      lead: `
        <strong class="aop-cover-subtitle">FDAI와 함께 운영 조직의 하루가 어떻게 달라질지 살펴봅니다</strong>
        <span class="aop-cover-summary">FDAI는 반복되는 판단에 검증된 규칙을 적용합니다. 사람은 승인과 방향 설정에 집중하고, 실행 결과는 독립된 관측으로 확인합니다.</span>
        <small class="aop-cover-principles" aria-label="검증된 규칙으로 판단, 사람이 승인, 독립된 관측으로 확인">
          <span>검증된 규칙으로 판단</span><i aria-hidden="true"></i><span>사람이 승인</span><i aria-hidden="true"></i><span>독립된 관측으로 확인</span>
        </small>`,
      layout: "briefing-cover deck-art-of-possible",
      content: `
        <figure class="briefing-cover-art">
          <img src="assets/art-possible.jpeg" alt="">
        </figure>
        ${sourceLabel(sourceList("constitution"))}`,
    },
    slide({
      index: 2,
      state: "CURRENT",
      chapter: chapters.today,
      title: "운영자는 하루의 대부분을 흩어진 신호를 연결하는 데 씁니다",
      lead: "운영자는 알림을 분류하고 근거를 찾은 뒤 승인을 기다립니다. 정작 복구하고 결과를 확인할 시간은 얼마 남지 않습니다.",
      layout: "aop-today",
      source: sourceList("operator", "constitution"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-today-board" aria-label="현재 운영자의 하루를 예시로 나타낸 시간 구성">
          <header>
            <b>예시</b>
            <strong>운영자 한 사람의 하루</strong>
            <span>업무 시간 100% 기준 · 측정 기간 24시간 · 실제 조직에서 측정한 값이 아닙니다</span>
          </header>
          <figure class="aop-today-strip">
            <figcaption>업무 시간은 이렇게 나뉩니다</figcaption>
            <div>
              <span class="triage" style="--aop-span:34"><b>알림 분류</b><i>34%</i></span>
              <span class="gather" style="--aop-span:26"><b>근거 수집</b><i>26%</i></span>
              <span class="wait" style="--aop-span:18"><b>승인 대기</b><i>18%</i></span>
              <span class="fix" style="--aop-span:12"><b>실제 복구</b><i>12%</i></span>
              <span class="report" style="--aop-span:10"><b>보고와 기록</b><i>10%</i></span>
            </div>
          </figure>
          <div class="aop-today-pain">
            <article><small>신호 연결</small><strong>흩어진 신호를 사람이 직접 연결합니다</strong><span>같은 장애 구간에서 나온 지표와 로그, 최근 변경 내역을 운영자가 기억과 경험에 기대어 연결합니다.</span><b>결과 · 비슷한 장애가 반복돼도 이전 판단의 근거를 되짚기 어렵습니다</b></article>
            <article><small>승인과 권한</small><strong>승인 과정이 대화 속에 흩어집니다</strong><span>누가 언제 무엇을 허용했는지 보여 주는 기록과 실제 실행 기록이 따로 남습니다.</span><b>결과 · 당시 승인과 권한이 적절했는지 나중에 확인하기 어렵습니다</b></article>
            <article><small>결과 확인</small><strong>조치의 효과를 따로 확인하지 못합니다</strong><span>조치를 마쳤다는 보고는 남지만, 실제로 무엇이 나아졌는지 독립된 관측으로 확인하지 못합니다.</span><b>결과 · 개선 여부를 수치와 근거로 설명하기 어렵습니다</b></article>
          </div>
        </section>`,
    }),
    slide({
      index: 3,
      state: "TARGET",
      chapter: chapters.scenes,
      title: "FDAI와 함께하면 운영자의 하루가 이렇게 달라질 수 있습니다",
      lead: "FDAI는 감지부터 신호 연결, 판단, 결과 확인까지 지원합니다. 사람은 영향 범위와 복구 계획을 살피고, 권한이 필요한 결정을 직접 내립니다.",
      layout: "aop-day",
      source: sourceList("constitution", "execution"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-day-compare" aria-label="현재 대응 방식과 FDAI를 활용한 대응 방식 비교">
          <div class="aop-day-legend">
            <span class="human">사람이 맡는 일</span>
            <span class="auto">FDAI가 지원하는 일</span>
            <b>같은 다섯 단계를 순서대로 비교합니다</b>
          </div>
          <ol class="aop-day-lane now" aria-label="현재 대응 방식">
            <li class="lane-tag"><small>현재</small><strong>사람이 모든 단계를 직접 이어 갑니다</strong></li>
            <li class="human"><small>감지</small><strong>쏟아지는 알림</strong><span>운영자가 분류</span></li>
            <li class="human"><small>연결</small><strong>여러 화면 확인</strong><span>운영자가 연결</span></li>
            <li class="human"><small>판단</small><strong>개인 경험에 의존</strong><span>운영자가 결정</span></li>
            <li class="human"><small>승인</small><strong>대화로 승인 요청</strong><span>운영자가 추적</span></li>
            <li class="human"><small>확인</small><strong>완료 보고에 의존</strong><span>운영자가 추정</span></li>
          </ol>
          <ol class="aop-day-lane next" aria-label="FDAI를 활용한 대응 방식">
            <li class="lane-tag"><small>FDAI와 함께</small><strong>사람은 승인과 방향 결정에 집중합니다</strong></li>
            <li class="auto"><small>감지</small><strong>중복을 정리한 이벤트</strong><span>FDAI가 이벤트를 정리</span></li>
            <li class="auto"><small>연결</small><strong>관계와 시간 흐름으로 연결</strong><span>FDAI가 근거를 구성</span></li>
            <li class="auto"><small>판단</small><strong>규칙에 따른 판단과 선택지</strong><span>FDAI가 제안</span></li>
            <li class="human"><small>승인</small><strong>근거를 확인하고 승인</strong><span>사람이 결정</span></li>
            <li class="auto"><small>확인</small><strong>독립된 관측으로 효과 확인</strong><span>FDAI가 검증</span></li>
          </ol>
          <p class="aop-day-summary"><b>달라지는 점</b>사람은 반복 작업에서 벗어나 영향 범위와 복구 계획을 확인하고, 필요한 승인과 방향 결정에 집중합니다.</p>
        </section>`,
    }),
    slide({
      index: 4,
      state: "TARGET",
      chapter: chapters.scenes,
      title: "장면 1 · 새벽, 운영자는 쏟아지는 알림 대신 근거와 선택지를 받습니다",
      lead: "Huginn(이벤트 수집 담당) 에이전트는 흩어진 신호를 정리하고, Forseti(판정 담당) 에이전트는 검증된 규칙을 적용합니다. 운영자는 근거와 영향 범위를 살핀 뒤 필요한 결정을 내립니다.",
      layout: "aop-scene",
      source: sourceList("pantheon", "constitution", "llmStrategy"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-scene" aria-label="새벽 장애 대응에서 전달되는 근거와 판단, 운영자의 역할">
          <header><b>예시 시나리오</b><strong>03:14 결제 서비스 지연 증가</strong><span>같은 장애 구간에서 나온 신호만 하나의 대응 후보로 묶습니다</span></header>
          <div class="aop-scene-grid">
            <article class="evidence">
              <small>운영자에게 전달되는 근거</small>
              <strong>운영자는 판단 근거와 선택지를 함께 받습니다</strong>
              <ul>
                <li>같은 시간대의 신호와 직전 변경 이력</li>
                <li>영향받는 서비스와 SLO 소진 상태</li>
                <li>근거를 수집한 시점과 최신성</li>
                <li>같은 증상을 해결한 이전 사례</li>
              </ul>
              <b>오래되었거나 서로 맞지 않는 근거는 판단에서 제외합니다</b>
            </article>
            <i aria-hidden="true"></i>
            <article class="judge">
              <small>FDAI의 판단 · Forseti</small>
              <strong>검증된 규칙부터 적용합니다</strong>
              <ul>
                <li>반복되는 판단은 T0 규칙과 정책으로 처리</li>
                <li>선택지마다 기대 효과를 함께 설명</li>
                <li>영향 범위와 복구 계획을 함께 계산</li>
                <li>근거가 부족하면 판단을 보류</li>
              </ul>
              <b>모델이 추론한 결과만으로는 관찰 모드 상한을 넘을 수 없습니다</b>
            </article>
            <i aria-hidden="true"></i>
            <article class="human">
              <small>운영자가 맡는 일 · 승인</small>
              <strong>근거를 살핀 뒤 필요한 결정을 내립니다</strong>
              <ul>
                <li>영향 범위와 검증된 복구 계획을 확인</li>
                <li>승인하거나 거절하며, 침묵은 승인이 아님을 확인</li>
                <li>승인한 사람과 다른 주체가 실행</li>
                <li>모든 판단 근거를 감사 기록에 보존</li>
              </ul>
              <b>승인은 정해진 시간이 지나면 만료되며, 경우에 따라 여러 사람의 동의가 필요합니다</b>
            </article>
          </div>
        </section>`,
    }),
    slide({
      index: 5,
      state: "TARGET",
      chapter: chapters.scenes,
      title: "장면 2 · 변경 회의는 영향 그래프에서 시작합니다",
      lead: "변경할 리소스가 어떤 서비스와 보호 목표에 연결되는지 따라가면, 막연한 인상 대신 확인 가능한 영향 범위와 조건을 바탕으로 결정할 수 있습니다.",
      layout: "aop-change",
      source: sourceList("operator", "ontology", "actionOntology"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-change-view" aria-label="변경 영향 그래프와 회의에서 확인할 조건">
          <div class="aop-change-legend"><b>예시 토폴로지</b><span>화살표는 저장된 관계의 방향을 보여 줍니다. 관계만으로 원인을 단정하지 않습니다</span></div>
          <figure class="aop-impact-map">
            <article class="target"><small>변경 대상</small><strong>결제 데이터베이스</strong><span>평가할 리비전 1842</span></article>
            <i aria-hidden="true"><em>runs_on</em></i>
            <article class="workload"><small>워크로드</small><strong>checkout-api</strong><span>배포와 운영의 단위</span></article>
            <i aria-hidden="true"><em>implemented_by</em></i>
            <article class="service"><small>비즈니스 서비스</small><strong>결제</strong><span>담당 조직과 중요도</span></article>
            <i aria-hidden="true"><em>governed_by</em></i>
            <article class="objective"><small>보호 목표</small><strong>가용성 SLO</strong><span>측정 구간과 목표값</span></article>
          </figure>
          <ol class="aop-change-check">
            <li><small>01</small><strong>평가할 리비전</strong><span>검토할 변경본을 정확히 지정합니다</span></li>
            <li><small>02</small><strong>관계로 확인한 영향 범위</strong><span>추측하지 않고 관계를 따라 영향 대상을 확인합니다</span></li>
            <li><small>03</small><strong>승인 조건과 담당자</strong><span>승인 조건과 담당자를 함께 기록합니다</span></li>
          </ol>
          <p class="aop-change-boundary"><b>경계</b>검토 승인은 리소스 변경 권한이 아닙니다. 검토를 마친 변경도 ActionType 실행 경로에서 정책과 위험, 승인 요건, 안전장치를 다시 확인합니다.</p>
        </section>`,
    }),
    slide({
      index: 6,
      state: "TARGET",
      chapter: chapters.scenes,
      title: "장면 3 · 신뢰성 목표를 지키는 선택지만 비용을 비교합니다",
      lead: "Njord(비용 담당) 에이전트는 안전과 신뢰성 조건을 먼저 확인합니다. 조건을 모두 충족한 선택지만 비용 절감 효과를 비교합니다.",
      layout: "aop-cost",
      source: sourceList("constitution", "execution", "metrics"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-cost-view" aria-label="비용을 비교하기 전에 확인할 조건과 후보별 적격 여부">
          <figure class="aop-cost-ladder">
            <figcaption>비용보다 먼저 확인하는 조건</figcaption>
            <div style="--aop-step:0"><small>01</small><strong>안전과 보안</strong><span>충족하지 못하면 비교 대상에서 제외합니다</span></div>
            <div style="--aop-step:1"><small>02</small><strong>신뢰성 목표</strong><span>SLO, RTO, RPO를 충족해야 합니다</span></div>
            <div style="--aop-step:2"><small>03</small><strong>변경 검증과 복구</strong><span>변경 전에 결과를 검증하고 되돌릴 수 있어야 합니다</span></div>
            <div style="--aop-step:3"><small>04</small><strong>비용 비교</strong><span>모든 조건을 통과한 뒤 절감 효과를 비교합니다</span></div>
          </figure>
          <div class="aop-cost-options">
            <header><b>예시</b><strong>후보별 적격 여부와 예상 절감</strong><span>표시된 비율은 설명을 위한 예시입니다</span></header>
            <article class="excluded">
              <span class="verdict">제외</span>
              <div class="option-copy"><strong>운영 인스턴스 축소</strong><em>가용성 SLO의 여유분이 기준 아래로 떨어집니다</em></div>
              <div class="option-save"><b>절감 예시 18%</b><i style="--aop-save:100" aria-hidden="true"></i></div>
            </article>
            <article class="eligible">
              <span class="verdict">적격</span>
              <div class="option-copy"><strong>예약 용량 재구성</strong><em>신뢰성 목표에 영향을 주지 않습니다</em></div>
              <div class="option-save"><b>절감 예시 12%</b><i style="--aop-save:67" aria-hidden="true"></i></div>
            </article>
            <article class="eligible">
              <span class="verdict">적격</span>
              <div class="option-copy"><strong>유휴 리소스 정리</strong><em>영향이 개별 리소스에만 한정됩니다</em></div>
              <div class="option-save"><b>절감 예시 6%</b><i style="--aop-save:33" aria-hidden="true"></i></div>
            </article>
            <footer>실제 절감 효과는 제안값이 아니라 독립된 관측으로 확인합니다.</footer>
          </div>
        </section>`,
    }),
    slide({
      index: 7,
      state: "PRINCIPLE",
      chapter: chapters.boundary,
      title: "요청은 대화로 받되, 판단과 승인, 실행은 서로 다른 주체가 맡습니다",
      lead: "Bragi(대화 변환 담당) 에이전트는 자연어 요청을 정형화된 의도로 바꿉니다. 판단하거나 승인하거나 실행하지 않으며, 말만으로 권한이 생기지는 않습니다.",
      layout: "aop-lanes",
      source: sourceList("pantheon", "security"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-lane-board" aria-label="자연어 요청부터 실행까지 책임을 나누는 방식">
          <div class="aop-lane-row">
            <article class="person"><small>요청</small><strong>사람</strong><span>목표와 필요한 도움을 설명합니다</span><b><i>기록</i>자연어 요청</b><em>요청만으로 권한이 생기지는 않습니다</em></article>
            <i aria-hidden="true"></i>
            <article class="narrator"><small>변환 · Bragi</small><strong>의도 정리</strong><span>대상, 범위, 시간, 제약 조건을 정리합니다</span><b><i>기록</i>정형화된 의도</b><em>판단은 내리지 않습니다</em></article>
            <i aria-hidden="true"></i>
            <article class="judge"><small>판정 · Forseti</small><strong>근거에 따라 판단</strong><span>검증된 규칙과 정책을 먼저 적용합니다</span><b><i>기록</i>Verdict</b><em>실행은 맡지 않습니다</em></article>
            <i aria-hidden="true"></i>
            <article class="approver"><small>승인 전달 · Var</small><strong>사람의 결정을 전달</strong><span>정족수와 유효 시간을 확인합니다</span><b><i>기록</i>Approval</b><em>스스로 승인할 수 없습니다</em></article>
            <i aria-hidden="true"></i>
            <article class="executor"><small>실행 · Thor</small><strong>조건을 충족한 작업만 실행</strong><span>별도의 실행 신원을 사용합니다</span><b><i>기록</i>ActionRun</b><em>승인자와 실행 신원을 분리합니다</em></article>
          </div>
          <div class="aop-lane-rail">
            <span class="rail-key">correlation_id</span>
            <p>하나의 식별자로 요청부터 복구 확인까지 연결합니다. 어떤 요청이 어떤 판단과 승인, 실행으로 이어졌는지 나중에도 추적할 수 있습니다.</p>
          </div>
          <div class="aop-lane-support">
            <article><strong>Saga(감사 담당) 에이전트</strong><span>기존 기록을 바꾸지 않는 원장에 모든 단계를 남깁니다</span></article>
            <article><strong>Vidar(복구 담당) 에이전트</strong><span>되돌리기와 복구를 담당합니다</span></article>
            <article><strong>15개 고정 에이전트</strong><span>각 에이전트의 역할은 설정으로 바꿀 수 없습니다</span></article>
          </div>
        </section>`,
    }),
    slide({
      index: 8,
      state: "BOUNDARY",
      chapter: chapters.boundary,
      title: "실제 실행 권한은 가장 낮은 허용 수준으로 정하고, 일곱 가지 안전장치를 먼저 확인합니다",
      lead: "위험, 영향 범위, 역할 권한 같은 통제 항목마다 허용 수준을 따로 계산합니다. 실제 권한은 그중 가장 낮은 수준으로 정하며, 어느 항목도 다른 항목의 상한을 높일 수 없습니다.",
      layout: "aop-ceiling",
      source: sourceList("execution", "constitution", "security"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-ceiling-view" aria-label="실제 권한을 정하는 여러 상한과 실행 전 안전장치">
          <figure class="aop-ceiling-chart">
            <figcaption>
              <b>예시 판정</b>
              <span class="scale"><i>차단</i><i>관찰 모드</i><i>사람 승인</i><i>자동 실행</i></span>
            </figcaption>
            <div class="rows">
              <div><strong>위험 기준표</strong><span class="track"><i style="--aop-cap:4">자동 실행</i></span></div>
              <div><strong>Tier 상한</strong><span class="track"><i style="--aop-cap:4">자동 실행</i></span></div>
              <div><strong>ActionType 상한</strong><span class="track"><i style="--aop-cap:3">사람 승인</i></span></div>
              <div class="lowest"><strong>영향 범위</strong><span class="track"><i style="--aop-cap:3">사람 승인</i></span></div>
              <div><strong>현재 부하</strong><span class="track"><i style="--aop-cap:4">자동 실행</i></span></div>
              <div><strong>역할 권한</strong><span class="track"><i style="--aop-cap:4">자동 실행</i></span></div>
              <div><strong>환경 제한</strong><span class="track"><i style="--aop-cap:4">자동 실행</i></span></div>
            </div>
            <p class="aop-ceiling-result"><b>결과</b>사람 승인이 필요합니다. 여러 상한 가운데 가장 낮은 상한 하나가 전체 권한을 정합니다.</p>
          </figure>
          <aside class="aop-safeguards">
            <small>자율적으로 상태를 바꾸기 전에 모두 확인할 일곱 가지 안전장치</small>
            <ul>
              <li><b>01</b>중지 조건</li>
              <li><b>02</b>시험한 복구 절차</li>
              <li><b>03</b>영향 범위 제한</li>
              <li><b>04</b>성공한 모의 실행</li>
              <li><b>05</b>대상 잠금</li>
              <li><b>06</b>고정된 중복 방지 키</li>
              <li><b>07</b>실행 전후 감사</li>
            </ul>
            <p>하나라도 확인되지 않으면 실행을 멈추고 사람에게 검토를 요청합니다.</p>
          </aside>
        </section>`,
    }),
    slide({
      index: 9,
      state: "METRIC",
      chapter: chapters.boundary,
      title: "요청이 전달됐다고 끝난 것이 아닙니다. 독립된 관측으로 효과까지 확인합니다",
      lead: "실행 주체와 분리된 관측자가 정해진 시간 동안 공식 데이터 출처를 확인해야만 성공으로 기록할 수 있습니다.",
      layout: "aop-closure",
      source: sourceList("constitution", "ontology", "metrics"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-closure-view" aria-label="효과 검증 절차와 안전 지표">
          <figure class="aop-closure-chain">
            <figcaption>성공을 확인하는 순서</figcaption>
            <div class="steps">
              <article><small>실행 전</small><strong>ExpectedEffect</strong><span>확인할 지표와 변화 방향, 허용 범위, 관측 시간을 먼저 정합니다</span><em>예시 · 오류율 2% 이하, 관측 시간 15분</em></article>
              <i aria-hidden="true"></i>
              <article><small>실행</small><strong>ActionRun</strong><span>실행을 시도하고 요청을 전달했다는 증적을 남깁니다</span><em>예시 · 중복 방지 키 고정, 대상 잠금 유지</em></article>
              <i aria-hidden="true"></i>
              <article class="observed"><small>독립 관측</small><strong>ObservedOutcome</strong><span>실행 주체와 분리된 관측자가 실제 효과를 확인합니다</span><em>예시 · 오류율 0.6%, SLO 회복 확인</em></article>
            </div>
            <p class="aop-closure-note"><b>성공 아님</b>API 응답, 메시지 브로커 수락, PR 병합만으로는 성공으로 기록하지 않습니다. 출처마다 결과가 다르면 평균값으로 합치지 않고 검토 상태로 남깁니다.</p>
          </figure>
          <aside class="aop-closure-guards">
            <small>한 건도 허용하지 않는 안전 지표</small>
            <div class="zeros">
              <article><b>0</b><span>정책 위반 결과를 통과시킨 사례</span></article>
              <article><b>0</b><span>잘못된 대상이나 오래된 리비전 실행</span></article>
              <article><b>0</b><span>권한 범위를 벗어난 실행</span></article>
              <article><b>0</b><span>검증 없이 성공으로 기록한 사례</span></article>
            </div>
            <p><b>각 30건 이상</b>합성하지 않은 실제 사례만 비교합니다. 시나리오와 기간, 리비전은 같아야 합니다.</p>
          </aside>
        </section>`,
    }),
    slide({
      index: 10,
      state: "DECISION",
      chapter: chapters.boundary,
      title: "현재 구현과 목표를 구분하고, 작게 시작할 시나리오 하나를 고릅니다",
      lead: "이 설명서에서 살펴본 장면은 목표로 하는 운영 경험입니다. 다음 단계에서는 지금 측정할 수 있고 경계가 분명한 판단 하나를 골라 가치와 실행 가능성을 평가합니다.",
      layout: "aop-decision",
      source: sourceList("deployment", "standingAuthority", "execution"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-decision-view" aria-label="현재 구현과 진행 중인 작업, 목표 상태와 다음 선택">
          <div class="aop-status-band">
            <article class="now"><small>현재 구현</small><strong>관찰 모드에서 판단하고 기록합니다</strong><span>규칙에 따라 판단하고 근거를 보존하며, 신원과 배포 경로를 안전하게 분리합니다</span></article>
            <article class="wip"><small>진행 중</small><strong>실행 전 과정을 증적으로 연결합니다</strong><span>워크플로와 격리 실행기에 같은 안전장치가 작동한다는 증적을 마련하고 있습니다</span></article>
            <article class="target"><small>목표</small><strong>사람이 미리 승인한 조건 안에서 단계적으로 배포합니다</strong><span>A3-E 실행 연결과 자동 환경 승격은 아직 사용할 수 없습니다</span></article>
          </div>
          <div class="aop-decision-cards">
            <article><small>01 선택</small><strong>반복되는 판단 하나</strong><span>반복해서 발생하고 경계가 분명한 판단을 고릅니다</span><em>확인 질문: 한 달에 30번 이상 같은 판단을 반복합니까?</em></article>
            <article><small>02 조건</small><strong>기준선과 복구 절차</strong><span>무조치 기준선과 안전장치, 시험한 복구 절차를 확인합니다</span><em>확인 질문: 실제로 되돌리기를 시험했습니까?</em></article>
            <article><small>03 측정</small><strong>독립된 효과 확인</strong><span>기대 효과와 관측 시간을 실행 전에 정합니다</span><em>확인 질문: 실행 주체와 다른 출처에서 효과를 확인할 수 있습니까?</em></article>
            <article class="next"><small>04 다음</small><strong>가치와 실행 가능성을 평가합니다</strong><span>선택한 시나리오를 다음 설명서에서 자세히 평가합니다</span><em>산출물: 담당자와 재검토 날짜를 정한 후보 1건</em></article>
          </div>
        </section>`,
    }),
  ];
}
