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
  today: "오늘의 운영 부담",
  scenes: "가능한 하루의 장면",
  boundary: "경계와 첫 결정",
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
      eyebrow: "FDAI / ART OF THE POSSIBLE",
      title: "같은 운영 조직이 어떤 하루를 보낼 수 있는지 살펴봅니다",
      lead: "FDAI는 반복되는 판단을 검증된 규칙으로 처리하고, 사람에게는 승인과 방향 결정을 남기며, 결과를 독립 관측으로 마감합니다.",
      layout: "briefing-cover deck-art-of-possible",
      content: `
        <figure class="briefing-cover-art">
          <img src="assets/art-possible.jpeg" alt="">
          <figcaption>POSSIBILITIES</figcaption>
        </figure>
        <ol class="briefing-cover-index" aria-label="Art of the Possible의 주요 구성">
          <li><small>01</small><span>${chapters.today}</span></li>
          <li><small>02</small><span>${chapters.scenes}</span></li>
          <li><small>03</small><span>${chapters.boundary}</span></li>
        </ol>
        <div class="aop-cover-promise" aria-label="설명서가 다루는 전환">
          <span>SIGNAL TO OUTCOME</span>
          <strong><b>01</b>흩어진 신호를 하나의 대응 후보로 정리합니다</strong>
          <strong><b>02</b>판단을 경험이 아니라 근거와 규칙으로 바꿉니다</strong>
          <strong><b>03</b>결과를 독립 관측으로 마감합니다</strong>
        </div>
        ${sourceLabel(sourceList("constitution", "pantheon", "metrics"))}`,
    },
    slide({
      index: 2,
      state: "GAP",
      chapter: chapters.today,
      title: "오늘은 하루의 대부분이 신호를 잇는 일에 쓰입니다",
      lead: "운영자는 알림을 분류하고, 근거를 모으고, 승인을 기다립니다. 실제 복구와 결과 확인에 쓰는 시간은 가장 적게 남습니다.",
      layout: "aop-today",
      source: sourceList("operator", "constitution"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-today-board" aria-label="예시로 표현한 현재 운영 하루의 시간 구성">
          <header>
            <b>예시</b>
            <strong>운영자 1인의 하루</strong>
            <span>업무 시간 100% 기준 · 측정 창 24시간 · 실제 조직 측정값이 아닙니다</span>
          </header>
          <figure class="aop-today-strip">
            <figcaption>업무 시간의 구성</figcaption>
            <div>
              <span class="triage" style="--aop-span:34"><b>알림 분류</b><i>34%</i></span>
              <span class="gather" style="--aop-span:26"><b>근거 수집</b><i>26%</i></span>
              <span class="wait" style="--aop-span:18"><b>승인 대기</b><i>18%</i></span>
              <span class="fix" style="--aop-span:12"><b>실제 복구</b><i>12%</i></span>
              <span class="report" style="--aop-span:10"><b>보고와 기록</b><i>10%</i></span>
            </div>
          </figure>
          <div class="aop-today-pain">
            <article><small>연결</small><strong>신호는 사람이 잇습니다</strong><span>같은 장애 구간의 지표, 로그, 최근 변경을 사람의 기억과 경험으로 연결합니다.</span><b>그래서 · 같은 장애가 반복돼도 판단 근거가 남지 않습니다</b></article>
            <article><small>권한</small><strong>승인은 대화로 흙어집니다</strong><span>누가 언제 무엇을 허용했는지가 실제 실행 기록과 분리되어 남습니다.</span><b>그래서 · 권한이 적절했는지 나중에 재현하기 어렵습니다</b></article>
            <article><small>결과</small><strong>효과는 증명되지 않습니다</strong><span>조치를 끝냈다는 보고는 있지만 실제 효과를 독립 근거로 마감하지 못합니다.</span><b>그래서 · 개선을 수치로 주장할 근거가 없습니다</b></article>
          </div>
        </section>`,
    }),
    slide({
      index: 3,
      state: "TARGET",
      chapter: chapters.scenes,
      title: "같은 하루가 이렇게 바뀔 수 있습니다",
      lead: "FDAI는 감지, 상관, 판단, 마감을 맡고 사람은 승인 한 번과 방향 결정에 집중합니다. 권한이 필요한 단계는 그대로 사람에게 남습니다.",
      layout: "aop-day",
      source: sourceList("constitution", "execution"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-day-compare" aria-label="오늘의 대응 단계와 목표 대응 단계 비교">
          <div class="aop-day-legend">
            <span class="human">사람이 하는 일</span>
            <span class="auto">FDAI가 처리하는 일</span>
            <b>다섯 단계를 같은 순서로 비교합니다</b>
          </div>
          <ol class="aop-day-lane now" aria-label="오늘의 대응">
            <li class="lane-tag"><small>지금</small><strong>사람이 전 단계를 잇습니다</strong></li>
            <li class="human"><small>감지</small><strong>알림 폭주</strong><span>사람이 분류</span></li>
            <li class="human"><small>상관</small><strong>대시보드 순회</strong><span>사람이 연결</span></li>
            <li class="human"><small>판단</small><strong>경험에 의존</strong><span>사람이 결정</span></li>
            <li class="human"><small>승인</small><strong>대화로 요청</strong><span>사람이 추적</span></li>
            <li class="human"><small>마감</small><strong>완료 보고</strong><span>사람이 주장</span></li>
          </ol>
          <ol class="aop-day-lane next" aria-label="가능한 대응">
            <li class="lane-tag"><small>가능한 하루</small><strong>사람은 승인과 방향에 집중합니다</strong></li>
            <li class="auto"><small>감지</small><strong>중복 제거된 이벤트</strong><span>FDAI가 정규화</span></li>
            <li class="auto"><small>상관</small><strong>관계와 시간으로 연결</strong><span>FDAI가 근거화</span></li>
            <li class="auto"><small>판단</small><strong>규칙 우선 판정과 선택지</strong><span>FDAI가 제시</span></li>
            <li class="human"><small>승인</small><strong>근거가 붙은 승인 한 번</strong><span>사람이 결정</span></li>
            <li class="auto"><small>마감</small><strong>독립 관측으로 확인</strong><span>FDAI가 검증</span></li>
          </ol>
          <p class="aop-day-summary"><b>남는 일</b>사람의 접점은 다섯 단계에서 한 단계로 줄고, 남은 한 번의 결정은 영향 범위와 복구 계획을 확인한 뒤 내립니다.</p>
        </section>`,
    }),
    slide({
      index: 4,
      state: "TARGET",
      chapter: chapters.scenes,
      title: "장면 1 · 새벽에는 알림 대신 근거와 선택지가 도착합니다",
      lead: "Huginn(이벤트 수집 담당) 에이전트가 신호를 정리하고 Forseti(판정 담당) 에이전트가 검증된 규칙으로 판정하면, 운영자는 확인하고 승인하는 일만 맡습니다.",
      layout: "aop-scene",
      source: sourceList("pantheon", "constitution", "llmStrategy"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-scene" aria-label="새벽 장애 대응 장면의 근거, 판단, 사람의 역할">
          <header><b>예시 시나리오</b><strong>03:14 결제 서비스 지연 증가</strong><span>같은 장애 구간의 신호만 하나의 대응 후보로 묶입니다</span></header>
          <div class="aop-scene-grid">
            <article class="evidence">
              <small>도착한 것 · 근거</small>
              <strong>무엇을 보고 판단했는지가 함께 옵니다</strong>
              <ul>
                <li>같은 구간의 신호와 직전 변경 리비전</li>
                <li>영향 서비스와 SLO 소진 상태</li>
                <li>근거 기준 시점과 최신성</li>
                <li>같은 증상을 닫았던 과거 사례</li>
              </ul>
              <b>오래되거나 충돌하는 근거는 판단에 쓰지 않습니다</b>
            </article>
            <i aria-hidden="true"></i>
            <article class="judge">
              <small>FDAI 판단 · Forseti</small>
              <strong>검증된 규칙을 먼저 적용합니다</strong>
              <ul>
                <li>T0 규칙과 정책으로 반복 판단 처리</li>
                <li>기대 효과가 붙은 선택지를 함께 제시</li>
                <li>영향 범위와 복구 계획을 같이 계산</li>
                <li>근거가 부족하면 판단을 보류</li>
              </ul>
              <b>모델 추론 결과는 관찰 모드 상한을 넘지 않습니다</b>
            </article>
            <i aria-hidden="true"></i>
            <article class="human">
              <small>사람이 하는 일 · 승인</small>
              <strong>확인하고 한 번 결정합니다</strong>
              <ul>
                <li>영향 범위와 검증된 복구 계획 확인</li>
                <li>승인 또는 거절, 침묵은 승인이 아님</li>
                <li>실행은 승인자와 다른 주체가 수행</li>
                <li>판단 근거는 감사 기록으로 보존</li>
              </ul>
              <b>승인에는 만료가 있고 정족수가 필요할 수 있습니다</b>
            </article>
          </div>
        </section>`,
    }),
    slide({
      index: 5,
      state: "TARGET",
      chapter: chapters.scenes,
      title: "장면 2 · 변경 회의는 영향 그래프에서 시작합니다",
      lead: "변경 대상 리소스에서 보호해야 할 목표까지 관계를 따라가면, 회의는 인상이 아니라 영향 범위와 조건을 놓고 결정할 수 있습니다.",
      layout: "aop-change",
      source: sourceList("operator", "ontology", "actionOntology"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-change-view" aria-label="변경 영향 그래프와 검토 조건">
          <div class="aop-change-legend"><b>예시 토폴로지</b><span>화살표는 저장된 관계 방향이며, 관계만으로 원인을 단정하지 않습니다</span></div>
          <figure class="aop-impact-map">
            <article class="target"><small>변경 대상</small><strong>결제 데이터베이스</strong><span>계획 리비전 1842</span></article>
            <i aria-hidden="true"><em>runs_on</em></i>
            <article class="workload"><small>워크로드</small><strong>checkout-api</strong><span>배포와 운영 단위</span></article>
            <i aria-hidden="true"><em>implemented_by</em></i>
            <article class="service"><small>비즈니스 서비스</small><strong>결제</strong><span>소유자와 중요도</span></article>
            <i aria-hidden="true"><em>governed_by</em></i>
            <article class="objective"><small>보호 목표</small><strong>가용성 SLO</strong><span>측정 구간과 목표값</span></article>
          </figure>
          <ol class="aop-change-check">
            <li><small>01</small><strong>정확한 리비전</strong><span>어떤 변경본을 평가했는지 고정합니다</span></li>
            <li><small>02</small><strong>관계 기반 영향 범위</strong><span>추정 대신 관계를 따라 대상을 셉니다</span></li>
            <li><small>03</small><strong>조건과 책임 기록</strong><span>승인 조건과 책임자를 함께 남깁니다</span></li>
          </ol>
          <p class="aop-change-boundary"><b>경계</b>검토 승인은 리소스 변경 권한이 아닙니다. 승인된 변경도 일반 ActionType 경로에서 정책, 위험, 승인, 안전장치를 다시 통과합니다.</p>
        </section>`,
    }),
    slide({
      index: 6,
      state: "TARGET",
      chapter: chapters.scenes,
      title: "장면 3 · 절감은 신뢰성 목표를 지킨 선택지 안에서만 비교합니다",
      lead: "Njord(비용 담당) 에이전트는 상위 제약을 위반하는 선택지를 먼저 제외하고, 남은 적격 선택지만 비용으로 비교합니다.",
      layout: "aop-cost",
      source: sourceList("constitution", "execution", "metrics"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-cost-view" aria-label="비용 결정의 제약 순서와 적격 선택지 비교">
          <figure class="aop-cost-ladder">
            <figcaption>먼저 통과해야 하는 순서</figcaption>
            <div style="--aop-step:0"><small>01</small><strong>안전과 보안</strong><span>위반하면 비교 대상이 아닙니다</span></div>
            <div style="--aop-step:1"><small>02</small><strong>신뢰성 목표</strong><span>SLO, RTO, RPO를 지킵니다</span></div>
            <div style="--aop-step:2"><small>03</small><strong>변경 안전</strong><span>검증과 복구가 가능해야 합니다</span></div>
            <div style="--aop-step:3"><small>04</small><strong>비용 비교</strong><span>여기서만 절감을 비교합니다</span></div>
          </figure>
          <div class="aop-cost-options">
            <header><b>예시</b><strong>적격 판정과 절감 후보</strong><span>표시된 비율은 설명을 위한 예시입니다</span></header>
            <article class="excluded">
              <span class="verdict">제외</span>
              <div class="option-copy"><strong>운영 인스턴스 축소</strong><em>가용성 SLO 여유가 목표 아래로 내려갑니다</em></div>
              <div class="option-save"><b>절감 예시 18%</b><i style="--aop-save:100" aria-hidden="true"></i></div>
            </article>
            <article class="eligible">
              <span class="verdict">적격</span>
              <div class="option-copy"><strong>예약 용량 재구성</strong><em>신뢰성 목표에 영향이 없습니다</em></div>
              <div class="option-save"><b>절감 예시 12%</b><i style="--aop-save:67" aria-hidden="true"></i></div>
            </article>
            <article class="eligible">
              <span class="verdict">적격</span>
              <div class="option-copy"><strong>유휴 리소스 정리</strong><em>영향 범위가 리소스 단위로 제한됩니다</em></div>
              <div class="option-save"><b>절감 예시 6%</b><i style="--aop-save:33" aria-hidden="true"></i></div>
            </article>
            <footer>실현된 절감은 제안이 아니라 독립 관측으로 확인합니다.</footer>
          </div>
        </section>`,
    }),
    slide({
      index: 7,
      state: "PRINCIPLE",
      chapter: chapters.boundary,
      title: "요청은 대화로 받고 판단, 승인, 실행은 서로 다른 책임자가 맡습니다",
      lead: "Bragi(대화 변환 담당) 에이전트는 자연어를 형식화된 의도로 바꿀 뿐 판단하거나 승인하거나 실행하지 않습니다. 언어는 권한을 만들지 않습니다.",
      layout: "aop-lanes",
      source: sourceList("pantheon", "security"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-lane-board" aria-label="요청부터 실행까지의 책임 분리">
          <div class="aop-lane-row">
            <article class="person"><small>요청</small><strong>사람</strong><span>목표와 질문을 말합니다</span><b><i>남기는 기록</i>자연어 요청</b><em>권한은 요청으로 생기지 않습니다</em></article>
            <i aria-hidden="true"></i>
            <article class="narrator"><small>변환 · Bragi</small><strong>의도 형식화</strong><span>대상, 범위, 시간, 제약을 채웁니다</span><b><i>남기는 기록</i>형식화된 의도</b><em>판단하지 않습니다</em></article>
            <i aria-hidden="true"></i>
            <article class="judge"><small>판정 · Forseti</small><strong>근거로 판정</strong><span>규칙과 정책을 먼저 적용합니다</span><b><i>남기는 기록</i>Verdict</b><em>실행하지 않습니다</em></article>
            <i aria-hidden="true"></i>
            <article class="approver"><small>승인 전달 · Var</small><strong>사람 결정 전달</strong><span>정족수와 만료를 확인합니다</span><b><i>남기는 기록</i>Approval</b><em>자기 승인은 금지됩니다</em></article>
            <i aria-hidden="true"></i>
            <article class="executor"><small>실행 · Thor</small><strong>적격 작업만 실행</strong><span>비대화형 실행 신원을 사용합니다</span><b><i>남기는 기록</i>ActionRun</b><em>승인자와 신원이 다릅니다</em></article>
          </div>
          <div class="aop-lane-rail">
            <span class="rail-key">correlation_id</span>
            <p>요청부터 복구 확인까지 한 식별자로 연결되어, 어떤 요청이 어떤 승인과 어떤 실행으로 이어졌는지 나중에 다시 볼 수 있습니다.</p>
          </div>
          <div class="aop-lane-support">
            <article><strong>Saga(감사 담당) 에이전트</strong><span>모든 단계를 추가만 가능한 원장에 남깁니다</span></article>
            <article><strong>Vidar(복구 담당) 에이전트</strong><span>되돌리기와 복구 작업을 맡습니다</span></article>
            <article><strong>15개 고정 에이전트</strong><span>역할 배치는 설정으로 바꿀 수 없습니다</span></article>
          </div>
        </section>`,
    }),
    slide({
      index: 8,
      state: "BOUNDARY",
      chapter: chapters.boundary,
      title: "가장 낮은 권한 상한이 이기고 일곱 안전장치는 실행 전에 증명됩니다",
      lead: "여러 축이 각각 상한을 계산하고 그중 가장 낮은 값이 실제 권한이 됩니다. 어느 축도 다른 축의 권한을 높이지 못합니다.",
      layout: "aop-ceiling",
      source: sourceList("execution", "constitution", "security"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-ceiling-view" aria-label="권한 상한 축과 실행 안전장치">
          <figure class="aop-ceiling-chart">
            <figcaption>
              <b>예시 판정</b>
              <span class="scale"><i>차단</i><i>관찰 모드</i><i>사람 승인</i><i>자동 실행</i></span>
            </figcaption>
            <div class="rows">
              <div><strong>위험 표</strong><span class="track"><i style="--aop-cap:4">자동 실행</i></span></div>
              <div><strong>Tier 상한</strong><span class="track"><i style="--aop-cap:4">자동 실행</i></span></div>
              <div><strong>ActionType 상한</strong><span class="track"><i style="--aop-cap:3">사람 승인</i></span></div>
              <div class="lowest"><strong>영향 범위</strong><span class="track"><i style="--aop-cap:3">사람 승인</i></span></div>
              <div><strong>실시간 부하</strong><span class="track"><i style="--aop-cap:4">자동 실행</i></span></div>
              <div><strong>역할 권한</strong><span class="track"><i style="--aop-cap:4">자동 실행</i></span></div>
              <div><strong>환경 하향</strong><span class="track"><i style="--aop-cap:4">자동 실행</i></span></div>
            </div>
            <p class="aop-ceiling-result"><b>결과</b>사람 승인. 가장 낮은 상한 하나가 전체 권한을 정합니다.</p>
          </figure>
          <aside class="aop-safeguards">
            <small>자율 상태 변경 전에 모두 증명하는 일곱 안전장치</small>
            <ul>
              <li><b>01</b>중지 조건</li>
              <li><b>02</b>검증된 복구</li>
              <li><b>03</b>영향 범위 제한</li>
              <li><b>04</b>가상 실행</li>
              <li><b>05</b>대상 잠금</li>
              <li><b>06</b>중복 억제</li>
              <li><b>07</b>2단계 감사</li>
            </ul>
            <p>하나라도 빠지면 실행하지 않고 사람 검토로 돌아갑니다.</p>
          </aside>
        </section>`,
    }),
    slide({
      index: 9,
      state: "METRIC",
      chapter: chapters.boundary,
      title: "전달 성공은 운영 성과가 아니며 독립 관측이 결과를 마감합니다",
      lead: "실행기와 다른 관측자가 권위 있는 출처를 정해진 관측 구간에서 확인해야 성공이라고 말할 수 있습니다.",
      layout: "aop-closure",
      source: sourceList("constitution", "ontology", "metrics"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-closure-view" aria-label="효과 검증 절차와 안전 지표">
          <figure class="aop-closure-chain">
            <figcaption>결과가 마감되는 순서</figcaption>
            <div class="steps">
              <article><small>실행 전</small><strong>ExpectedEffect</strong><span>지표, 방향, 허용 범위, 관측 구간을 먼저 정합니다</span><em>예시 · 오류율 2% 이하, 관측 구간 15분</em></article>
              <i aria-hidden="true"></i>
              <article><small>실행</small><strong>ActionRun</strong><span>시도와 전달 증적을 남깁니다</span><em>예시 · 중복 억제 키 고정, 대상 잠금 유지</em></article>
              <i aria-hidden="true"></i>
              <article class="observed"><small>독립 관측</small><strong>ObservedOutcome</strong><span>실행기와 다른 관측자가 효과를 확인합니다</span><em>예시 · 오류율 0.6%, SLO 회복 확인</em></article>
            </div>
            <p class="aop-closure-note"><b>인정하지 않음</b>API 응답 성공, 메시지 브로커 수락, PR 병합만으로는 성공으로 마감하지 않습니다. 출처가 충돌하면 평균 내지 않고 검토 상태로 남깁니다.</p>
          </figure>
          <aside class="aop-closure-guards">
            <small>정확히 0이어야 하는 안전 지표</small>
            <div class="zeros">
              <article><b>0</b><span>정책 위반 유출</span></article>
              <article><b>0</b><span>잘못된 대상 또는 오래된 리비전 실행</span></article>
              <article><b>0</b><span>권한 밖 실행</span></article>
              <article><b>0</b><span>검증되지 않은 성공 주장</span></article>
            </div>
            <p><b>30건 이상</b>기준선과 처리군 각각의 비합성 최소 표본입니다. 같은 시나리오와 기간, 같은 리비전에서만 비교합니다.</p>
          </aside>
        </section>`,
    }),
    slide({
      index: 10,
      state: "DECISION",
      chapter: chapters.boundary,
      title: "현재와 목표를 구분한 다음 좁은 시나리오 하나를 고릅니다",
      lead: "이 설명서의 장면은 목표 운영 경험입니다. 다음 단계는 오늘 측정할 수 있는 의사결정 유형 하나를 골라 우선순위 평가로 넘기는 것입니다.",
      layout: "aop-decision",
      source: sourceList("deployment", "standingAuthority", "execution"),
      sourceLabel,
      statusLabel,
      content: `
        <section class="aop-decision-view" aria-label="구현 상태 구분과 다음 결정">
          <div class="aop-status-band">
            <article class="now"><small>현재 구현</small><strong>관찰 모드 판단과 감사</strong><span>규칙 기반 판정, 근거 보존, 분리된 신원과 보호된 배포 경로</span></article>
            <article class="wip"><small>진행 중</small><strong>실행 경로의 종단 증적</strong><span>워크플로 적용 경로와 격리 실행기의 동등한 안전장치 증적</span></article>
            <article class="target"><small>목표</small><strong>사전 조건부 승인과 점진적 배포</strong><span>A3-E 실행 연결과 자동 환경 승격은 아직 사용할 수 없습니다</span></article>
          </div>
          <div class="aop-decision-cards">
            <article><small>01 선택</small><strong>의사결정 유형 하나</strong><span>반복되고 경계가 분명한 판단을 고릅니다</span><em>확인 질문: 같은 판단이 한 달에 30번 이상 발생합니까?</em></article>
            <article><small>02 조건</small><strong>기준선과 복구</strong><span>무조치 기준선, 안전장치, 검증된 복구를 확인합니다</span><em>확인 질문: 되돌리기를 실제로 시험해 보았습니까?</em></article>
            <article><small>03 측정</small><strong>독립 효과 관측</strong><span>기대 효과와 관측 구간을 먼저 정합니다</span><em>확인 질문: 실행기와 다른 출처로 효과를 볼 수 있습니까?</em></article>
            <article class="next"><small>04 다음</small><strong>가치 우선순위화</strong><span>선택한 시나리오를 다음 설명서로 넘깁니다</span><em>산출물: 책임자와 재검토 날짜가 적힌 후보 한 건</em></article>
          </div>
        </section>`,
    }),
  ];
}
