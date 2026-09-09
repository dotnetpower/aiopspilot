/** Slides 2-7: define the portfolio decision and its smallest useful unit. */
import { field, slide } from "./value-prioritization-slide-kit.js";

export function buildValuePrioritizationFoundations() {
  return [
    slide({
      index: 2,
      id: "selection",
      chapter: 1,
      state: "DECISION",
      title: "가장 큰 아이디어보다 첫 번째로 검증 가능한 결정을 고릅니다",
      lead: "후보를 넓게 모으되, 이번 포트폴리오 회의에서는 근거와 책임이 닫히는 의사결정 유형 하나만 선택합니다.",
      evidence: ["constitution", "planning"],
      takeaway: "선정 결과는 기능 목록이 아니라 기준선, 대상, 책임자, 기대 효과가 있는 한 가지 결정입니다.",
      body: `
        <div class="vp-selection-field">
          <div class="vp-selection-pool">
            <small>후보 백로그</small>
            <span>변경 검토</span><span>복구 판단</span><span>용량 조정</span><span>비용 이상</span><span>정책 편차</span><span>운영 질의</span>
          </div>
          <div class="vp-selection-gates" aria-label="후보를 줄이는 네 가지 질문">
            <div><b>01</b><strong data-vp-primary>반복되는 판단인가</strong><span>같은 입력과 선택 구조가 다시 나타나는지 확인합니다.</span></div>
            <div><b>02</b><strong data-vp-primary>현재 근거가 있는가</strong><span>출처, 시점, 범위, 완전성을 확인합니다.</span></div>
            <div><b>03</b><strong data-vp-primary>안전하게 멈출 수 있는가</strong><span>복구와 영향 범위를 실행 전에 검토합니다.</span></div>
            <div><b>04</b><strong data-vp-primary>효과를 따로 볼 수 있는가</strong><span>실행기와 다른 관측 출처를 정합니다.</span></div>
          </div>
          <article class="vp-selection-result">
            <small>이번 결정</small>
            <strong>첫 관찰 모드 후보 1건</strong>
            <span>선택 이유와 보류 이유를 같은 기준으로 기록합니다.</span>
          </article>
        </div>`,
    }),
    slide({
      index: 3,
      id: "decision-anatomy",
      chapter: 1,
      state: "GUIDE",
      title: "프로젝트가 아니라 반복되는 의사결정 유형을 단위로 삼습니다",
      lead: "도구 도입이나 거대한 업무 영역보다, 어떤 신호에서 누가 무엇을 판단하는지를 먼저 고정해야 비교와 재생이 가능합니다.",
      evidence: ["ontology", "planning"],
      takeaway: "좋은 후보는 같은 질문이 반복되고, 무조치 선택과 완료 판단까지 한 문장으로 설명할 수 있습니다.",
      body: `
        <div class="vp-anatomy-strip" role="img" aria-label="신호, 대상, 선택지, 결정, 효과로 이어지는 의사결정 구조">
          <article data-vp-node="trigger"><small>TRIGGER</small><strong data-vp-primary>무엇이 판단을 시작합니까?</strong><span>관측, 변경 요청, 일정, 운영자 요청</span></article>
          <i class="vp-arrow" data-vp-link data-vp-from="trigger" data-vp-to="target" aria-hidden="true"></i>
          <article data-vp-node="target"><small>TARGET</small><strong data-vp-primary>어떤 대상을 봅니까?</strong><span>정확한 객체 ID와 리비전</span></article>
          <i class="vp-arrow" data-vp-link data-vp-from="target" data-vp-to="options" aria-hidden="true"></i>
          <article data-vp-node="options"><small>OPTIONS</small><strong data-vp-primary>무엇을 선택할 수 있습니까?</strong><span>행동, 보류, 무조치 기준선</span></article>
          <i class="vp-arrow" data-vp-link data-vp-from="options" data-vp-to="outcome" aria-hidden="true"></i>
          <article data-vp-node="outcome"><small>OUTCOME</small><strong data-vp-primary>어떻게 완료를 압니까?</strong><span>독립 관측과 종료 조건</span></article>
        </div>
        <div class="vp-anatomy-example">
          <span><b>넓은 표현</b>비용을 최적화한다</span>
          <i aria-hidden="true">→</i>
          <strong><b>의사결정 유형</b>유휴 리소스 후보를 근거와 보호 목표에 따라 정리, 보류, 유지 중 하나로 판정한다</strong>
        </div>`,
    }),
    slide({
      index: 4,
      id: "questions",
      chapter: 1,
      state: "GUIDE",
      title: "다섯 질문에 답하면 후보의 가치와 경계가 함께 보입니다",
      lead: "가치만 묻지 말고 반복성, 근거, 안전, 측정 가능성을 같은 대화에서 확인합니다.",
      evidence: ["constitution", "metrics", "readiness"],
      takeaway: "한 질문이라도 답할 수 없으면 낮은 점수를 주는 대신 보완할 근거와 책임자를 지정합니다.",
      body: `
        <div class="vp-question-compass">
          <div class="vp-question-center"><small>PORTFOLIO QUESTION</small><strong>왜 이 판단을<br>지금 검증합니까?</strong></div>
          <ol>
            <li><b>01</b><strong data-vp-primary>어떤 운영 손실을 줄입니까?</strong><span>시간, 비용, 위험, 사람 접점을 구분합니다.</span></li>
            <li><b>02</b><strong data-vp-primary>같은 판단이 반복됩니까?</strong><span>입력과 선택지가 안정적인지 봅니다.</span></li>
            <li><b>03</b><strong data-vp-primary>판단할 근거가 있습니까?</strong><span>권위, 최신성, 범위, 완전성을 확인합니다.</span></li>
            <li><b>04</b><strong data-vp-primary>실패해도 통제할 수 있습니까?</strong><span>중지, 복구, 영향 범위를 확인합니다.</span></li>
            <li><b>05</b><strong data-vp-primary>결과를 독립적으로 확인합니까?</strong><span>기대 효과와 관측 창을 먼저 정합니다.</span></li>
          </ol>
        </div>`,
    }),
    slide({
      index: 5,
      id: "domains",
      chapter: 1,
      state: "CONTRACT",
      title: "세 운영 도메인은 서로 다른 가치와 보호 목표를 가집니다",
      lead: "SRE 운영 모델 안에서 복원력, 변경 안전성, 비용 거버넌스 후보를 같은 제어 경계로 비교하되 성과 의미는 섞지 않습니다.",
      evidence: ["constitution", "outcomes"],
      takeaway: "도메인은 후보의 이름이 아니라 보호할 목표, 필요한 근거, 확인할 효과를 정합니다.",
      body: `
        <div class="vp-domain-landscape">
          <article class="resilience">
            <header><small>RESILIENCE</small><strong>복원력</strong></header>
            <dl>${field("판단", "복구 경로와 시점", "장애, 백업, 복원, 연속성")}${field("보호", "서비스·복구 목표", "SLO와 RTO/RPO를 같은 범위에서 보호")}${field("완료", "독립적으로 확인한 복구", "재발과 복구 상태까지 관측")}</dl>
          </article>
          <article class="change">
            <header><small>CHANGE SAFETY</small><strong>변경 안전성</strong></header>
            <dl>${field("판단", "변경 허용과 조건", "정확한 리비전과 영향 범위")}${field("보호", "아키텍처 제약과 안정성", "승인과 실행을 분리")}${field("완료", "변경 후 효과 확인", "API 응답이 아닌 운영 결과")}</dl>
          </article>
          <article class="cost">
            <header><small>COST GOVERNANCE</small><strong>비용 거버넌스</strong></header>
            <dl>${field("판단", "유지, 조정, 보류", "비용과 용량 근거")}${field("보호", "가용성과 성능", "신뢰성 조건을 먼저 통과")}${field("완료", "실현된 단위 비용", "예상 절감과 실제 효과를 분리")}</dl>
          </article>
        </div>`,
    }),
    slide({
      index: 6,
      id: "brief",
      chapter: 1,
      state: "PROPOSAL",
      title: "후보 접수 단계에서 기대를 검증 가능한 문장으로 바꿉니다",
      lead: "짧은 의사결정 브리프가 범위를 줄이고, 서로 다른 팀이 같은 후보를 같은 기준으로 검토하도록 도와줍니다.",
      evidence: ["ontology", "planning", "outcomes"],
      takeaway: "후보 이름보다 대상, 기준선, 보호 목표, 관측 출처, 책임자가 먼저 채워져야 합니다.",
      body: `
        <div class="vp-brief-sheet">
          <header><span>DECISION BRIEF</span><strong>한 페이지 후보 정의</strong><small>워크숍 제안</small></header>
          <dl>
            ${field("운영 문제", "현재 무엇이 늦거나 위험합니까?", "관측 가능한 손실 또는 제약")}
            ${field("판단 문장", "누가 어떤 신호로 무엇을 선택합니까?", "행동, 보류, 무조치 포함")}
            ${field("정확한 범위", "어떤 서비스, 대상, 환경입니까?", "제외할 범위까지 명시")}
            ${field("무조치 기준선", "아무것도 하지 않으면 무엇이 일어납니까?", "비교할 현재 운영 흐름")}
            ${field("기대 효과", "어떤 지표가 어느 방향으로 변해야 합니까?", "단위, 기간, 관측 출처")}
            ${field("보호 목표", "무엇이 나빠지면 안 됩니까?", "SLO, 복구, 보안, 변경 안전")}
            ${field("책임자", "누가 결과와 보완 작업을 소유합니까?", "승인 역할과 실행 역할은 별도")}
            ${field("재검토 시점", "언제 어떤 근거로 다시 판단합니까?", "만료 없는 보류를 방지")}
          </dl>
        </div>`,
    }),
    slide({
      index: 7,
      id: "baseline",
      chapter: 1,
      state: "CONTRACT",
      title: "무조치 기준선이 있어야 개선의 크기와 부작용을 함께 볼 수 있습니다",
      lead: "현재 운영과 FDAI 처리 결과를 같은 자격 조건과 관측 창으로 비교해야 속도 향상과 안전 저하를 구분할 수 있습니다.",
      evidence: ["metrics", "planning"],
      takeaway: "기준선이 없는 기대 효과는 우선순위 근거가 아니라 아직 검증되지 않은 가설입니다.",
      body: `
        <div class="vp-baseline-compare">
          <article class="baseline">
            <header><small>BASELINE</small><strong>현재 운영 흐름</strong></header>
            <div><span>같은 후보 자격</span><i></i><span>같은 측정 기간</span><i></i><span>같은 지표 정의</span></div>
            <p>실제 비FDAI 운영 과정에서 판단, 대기, 실행, 결과 확인에 든 시간을 보존합니다.</p>
          </article>
          <div class="vp-baseline-delta"><small>COMPARE</small><strong>차이</strong><span>성과 지표 개선</span><span>안전 지표 비회귀</span></div>
          <article class="treatment">
            <header><small>TREATMENT</small><strong>FDAI 관찰 또는 적용 결과</strong></header>
            <div><span>같은 후보 자격</span><i></i><span>같은 측정 기간</span><i></i><span>같은 지표 정의</span></div>
            <p>재시도와 정정은 최신 권위 관측으로 정리하고, 미완료 사례는 분모에서 숨기지 않습니다.</p>
          </article>
        </div>`,
    }),
  ];
}
