/** Slides 13-17: translate the eligible decision into measurable value and bounded authority. */
import { slide } from "./value-prioritization-slide-kit.js";

export function buildValuePrioritizationValue() {
  return [
    slide({
      index: 13,
      id: "metrics",
      chapter: 3,
      state: "CONTRACT",
      title: "가치를 다섯 가지 관측 가능한 운영 결과로 번역합니다",
      lead: "모든 지표는 같은 비교 규약에서 단위, 기간, 기준선, 포함과 제외 기준, 의사결정 목적을 함께 기록합니다.",
      evidence: ["metrics", "outcomes"],
      takeaway: "측정할 수 없는 편익은 제거하지 말고 가설로 표시하며, 포트폴리오 판정의 확정 근거로 사용하지 않습니다.",
      body: `
        <div class="vp-metric-system">
          <header><span>공통 측정 계약</span><strong>기준선과 처리군 · 기본 30일 또는 1회 고정 시나리오 재생</strong><small>지표별 표본 수 · 신뢰 구간 · 포함/제외</small></header>
          <div>
            <article><small>VALUE 01</small><strong data-vp-primary>업무 단위 비용</strong><b>USD / 사건 · 변경 · 최적화</b><span>모델, 계산, 저장, 이벤트 처리는 포함하고 공유 고정비는 제외합니다.</span></article>
            <article><small>VALUE 02</small><strong data-vp-primary>자동 해결 비율</strong><b>완료 이벤트 / 전체 이벤트</b><span>사람 접점과 사후 복구 없이 독립 검증까지 닫힌 결과만 포함합니다.</span></article>
            <article><small>VALUE 03</small><strong data-vp-primary>MTTR</strong><b>초 · 평균 + 중앙값 + p90 · 확인된 복구만</b><span>미해결 사건은 0초로 넣지 않고 별도 미해결 건수로 남깁니다.</span></article>
            <article><small>VALUE 04</small><strong data-vp-primary>변경 리드 타임</strong><b>초 · 평균 + 중앙값 + p90 · 병합된 변경만</b><span>변경 요청부터 병합까지의 흐름을 같은 변경 자격 집합에서 비교합니다.</span></article>
            <article><small>VALUE 05</small><strong data-vp-primary>사람 접점</strong><b>이벤트 100건당 접점</b><span>승인, 수동 편집, 수동 복구를 세고 단순 조회는 제외합니다.</span></article>
          </div>
        </div>`,
    }),
    slide({
      index: 14,
      id: "guard-balance",
      chapter: 3,
      state: "CONTRACT",
      title: "성과가 좋아져도 안전 지표 한 건을 상쇄할 수 없습니다",
      lead: "성공 지표와 안전 지표를 같은 측정 창에서 보되, 정확히 0이어야 하는 위반은 평균이나 가중치로 희석하지 않습니다.",
      evidence: ["constitution", "metrics"],
      takeaway: "빠르거나 저렴해진 후보라도 정책, 대상, 권한, 효과 검증 경계를 넘으면 포트폴리오에서 즉시 보류합니다.",
      body: `
        <div class="vp-guard-balance-layout">
          <section class="outcomes">
            <header><small>SUCCESS METRICS</small><strong>개선 방향을 보는 지표</strong></header>
            <ul><li>업무 단위 비용 ↓</li><li>자동 해결 비율 ↑</li><li>MTTR ↓</li><li>변경 리드 타임 ↓</li><li>사람 접점 ↓</li></ul>
            <p>기준선과 같은 관측 기간, 같은 자격 규칙, 각 지표의 실제 표본 수와 신뢰 구간을 사용합니다.</p>
          </section>
          <div class="vp-balance-pivot"><span>AND</span><strong>함께<br>통과</strong><i aria-hidden="true"></i></div>
          <section class="guards">
            <header><small>ZERO-TOLERANCE GUARDS</small><strong>정확히 0이어야 하는 위반</strong></header>
            <ol>
              <li><b>0</b><span>정책 위반의 적용 모드 유출</span></li>
              <li><b>0</b><span>잘못된 대상 또는 오래된 리비전 실행</span></li>
              <li><b>0</b><span>등록 범위 밖의 무권한 실행</span></li>
              <li><b>0</b><span>독립 확인 없는 성공 주장</span></li>
            </ol>
          </section>
        </div>`,
    }),
    slide({
      index: 15,
      id: "repeatability-map",
      chapter: 3,
      state: "EXAMPLE",
      title: "빈도보다 반복 가능한 판단 구조가 첫 파일럿을 만듭니다",
      lead: "자주 발생해도 입력과 선택지가 매번 달라지면 자동화 근거를 모으기 어렵습니다. 반복성과 빈도를 나누어 후보를 배치합니다.",
      evidence: ["deterministic", "metrics"],
      takeaway: "오른쪽 위 후보부터 검토하되, 근거 적격성과 안전 계약을 통과했다는 전제가 먼저입니다.",
      body: `
        <div class="vp-repeatability-layout">
          <header><b>설명용 예시</b><span>정성적 위치이며 실제 조직의 측정값이 아닙니다</span></header>
          <figure>
            <span class="axis-y"><b>높음</b>반복 빈도<b>낮음</b></span>
            <span class="axis-x"><b>낮음</b>판단 구조의 반복성<b>높음</b></span>
            <div class="quadrant q1"><small>발견</small><strong>규칙 후보를 먼저 찾습니다</strong></div>
            <div class="quadrant q2"><small>우선 검토</small><strong>관찰 모드 표본을 모으기 좋습니다</strong></div>
            <div class="quadrant q3"><small>보류</small><strong>빈도와 운영 손실을 다시 확인합니다</strong></div>
            <div class="quadrant q4"><small>사람 중심</small><strong>일회성 판단은 구조화만 지원합니다</strong></div>
            <article class="candidate drift" aria-label="정책 편차 검토 예시"><b>변경 정책 편차</b><span>같은 규칙과 대상군</span></article>
            <article class="candidate restore" aria-label="복구 준비도 점검 예시"><b>복구 준비도 점검</b><span>정기 점검과 고정 기준</span></article>
            <article class="candidate resize" aria-label="용량 조정 예시"><b>용량 조정</b><span>맥락 변동이 큼</span></article>
            <article class="candidate migration" aria-label="일회성 마이그레이션 예시"><b>대규모 이전</b><span>한 번뿐인 계획</span></article>
          </figure>
        </div>`,
    }),
    slide({
      index: 16,
      id: "tier-fit",
      chapter: 3,
      state: "CONTRACT",
      title: "판단 Tier는 예상 비용과 설명 가능성, 보류 지점을 함께 바꿉니다",
      lead: "충분한 판단이 가능한 가장 낮은 Tier를 사용합니다. Tier 선택은 판단 방식일 뿐 실행 권한을 부여하지 않습니다.",
      evidence: ["deterministic", "execution"],
      takeaway: "첫 후보는 T0 규칙 또는 검증된 T1 재사용으로 설명할 수 있을수록 빠르게 학습하고 감사하기 쉽습니다.",
      body: `
        <div class="vp-tier-fit-layout">
          <header><b>설계 목표 · 이벤트 비율</b><span>실제 운영 측정값이 아니며, 배포별 관측 창과 표본 수를 함께 보고해야 합니다</span></header>
          <div class="vp-tier-ramp">
            <article class="t0" style="--vp-share:78">
              <small>T0 · 목표 70-80%</small><strong data-vp-primary>규칙과 정책</strong><span>반복 가능한 입력을 같은 규칙 버전으로 판단합니다.</span><em>보류: 규칙 없음 · 충돌 · 잘못된 맥락</em>
            </article>
            <article class="t1" style="--vp-share:48">
              <small>T1 · 목표 15-20%</small><strong data-vp-primary>검증된 사례 재사용</strong><span>유사도와 이전 결과, 재사용 작업 버전을 남깁니다.</span><em>보류: 낮은 유사도 · 출처 없음</em>
            </article>
            <article class="t2" style="--vp-share:28">
              <small>T2 · 목표 5-10%</small><strong data-vp-primary>근거 기반 추론</strong><span>서로 다른 모델의 제안과 결정론적 검증을 요구합니다.</span><em>상한: 관찰 모드 · 자동 실행 불가</em>
            </article>
          </div>
          <div class="vp-tier-axis"><span>더 반복 가능하고 저렴함</span><i></i><span>더 모호하고 검증 비용이 큼</span></div>
        </div>`,
    }),
    slide({
      index: 17,
      id: "authority-ceiling",
      chapter: 3,
      state: "EXAMPLE",
      title: "실행 권한은 가치 점수가 아니라 가장 낮은 허용 상한이 정합니다",
      lead: "위험 기준표와 Tier, 등록된 작업 유형(ActionType), 영향 범위, 역할, 환경을 각각 평가하고 가장 보수적인 결과를 최종 상한으로 사용합니다.",
      evidence: ["execution", "constitution"],
      takeaway: "이 그림은 권한 결정 방식을 설명하는 예시입니다. 기대 가치나 사람의 요청도 독립된 상한을 높이지 못합니다.",
      body: `
        <div class="vp-authority-layout">
          <header><b>설명용 판정</b><strong>비운영 환경의 리소스 그룹 변경 후보</strong><span>범주형 권한 예시 · 실제 실행 결정 아님</span></header>
          <div class="vp-authority-scale"><span>차단</span><span>관찰 모드</span><span>사람 승인</span><span>자동 실행</span></div>
          <div class="vp-authority-rows">
            <div style="--vp-cap:4"><strong>위험 기준표</strong><span><i>자동 실행</i></span><small>정책 위반 없음</small></div>
            <div style="--vp-cap:4"><strong>Tier</strong><span><i>자동 실행</i></span><small>T0 규칙 판정</small></div>
            <div style="--vp-cap:4"><strong>ActionType</strong><span><i>자동 실행</i></span><small>등록된 상한</small></div>
            <div class="limiting" style="--vp-cap:3"><strong>영향 범위</strong><span><i>사람 승인</i></span><small>리소스 그룹</small></div>
            <div style="--vp-cap:4"><strong>실시간 영향</strong><span><i>자동 실행</i></span><small>추가 하향 없음</small></div>
            <div style="--vp-cap:4"><strong>역할</strong><span><i>자동 실행</i></span><small>최소 역할 충족</small></div>
            <div style="--vp-cap:4"><strong>환경</strong><span><i>자동 실행</i></span><small>비운영 범위</small></div>
          </div>
          <aside><span>최종 상한</span><strong>사람 승인</strong><small>가장 낮은 독립 상한이 전체 결과를 결정합니다</small></aside>
        </div>`,
    }),
  ];
}
