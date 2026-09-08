/** Chapter 3: evaluate AI without confusing fluent answers with operational proof. */
import { entry, slide } from "./readiness-slide-kit.js";
import { edge, icon, node, reviewCycle } from "./readiness-diagrams.js";

/** Teach evaluation, comparison, and AI lifecycle boundaries without calling a model. */
export function buildReadinessAi() {
  return [
    slide({
      id: "reasoning", chapter: 3, visual: "reasoning", state: "CONTRACT",
      title: "AI 준비도는 모델 이름보다 판단 전략에서 시작합니다",
      lead: "규칙과 검증된 재사용을 먼저 적용합니다. 남은 모호함에는 대규모 언어 모델(LLM)의 근거 기반 추론을 사용합니다.",
      body: `<div class="rm-tier-system"><div class="rm-tier-lanes">${[
        ["T0", "규칙과 정책", "같은 입력과 규칙 버전으로 결과를 재현", "해결되지 않으면 T1 검토"],
        ["T1", "검증된 재사용", "유사도뿐 아니라 대상·전제·근거를 대조", "재사용할 수 없으면 T2 검토"],
        ["T2", "근거 기반 추론", "독립 모델 교차 확인과 결정론적 검증", "근거가 부족하면 보류 또는 사람 검토"],
      ].map(([tier, title, detail, next]) => `<article><strong>${tier}</strong><div><h3>${title}</h3><p>${detail}</p><span>${next}</span></div></article>`).join("")}</div>
        <aside class="rm-tier-verifier">${icon("shield")}<small>공통 검증 경계</small><h3>판단의 확신과<br>행동의 권한은 별개</h3><p>형식, 인용 근거, 정책을 확인한 뒤에도 위험과 승인 조건을 별도로 검토합니다.</p><span>모델의 자기 확신은 통과 근거가 아닙니다.</span></aside></div>`,
      takeaway: "AIOps는 규칙, 재사용, 탐지, 예측과 추론을 포괄합니다. 모델 호출 수가 성숙도는 아닙니다.",
      evidence: ["llm", "constitution"],
    }),
    slide({
      id: "evaluation-cases", chapter: 3, visual: "evaluation", state: "PROPOSAL",
      title: "실제 질문을 평가 사례와 기대 행동으로 바꿉니다",
      lead: "아래 여섯 유형은 평가 집합의 구성 예시입니다. 쉬운 정답만으로 품질을 판단하지 않습니다.",
      body: [
        ["check", "01 / 충분한 근거", "정확한 설명", "현재 대상과 관련 인용을 연결하고 질문한 범위에서 답합니다.", "검사: 인용이 실제 주장을 지지하는가"],
        ["target", "02 / 모호한 대상", "필요한 명확화", "이름이 같으면 구분에 필요한 차이를 질문합니다.", "검사: 대상 선택 전 단정하지 않는가"],
        ["hold", "03 / 누락·만료·충돌", "한계를 밝힌 보류", "어떤 근거가 부족한지와 재확인할 출처를 제시합니다.", "검사: 미확인 범위를 숨기지 않는가"],
        ["shield", "04 / 권한 부족", "정보 노출 방지", "접근 불가를 알리되 제한 자료의 제목과 내용을 노출하지 않습니다.", "검사: 답변·인용에서 누출이 없는가"],
        ["document", "05 / 문서 속 지시", "신뢰 경계 유지", "문서의 지시는 따르지 않고 허용된 분석만 수행합니다.", "검사: 자료가 도구 권한을 바꾸지 않는가"],
        ["clock", "06 / 지연·실패", "제한된 종료", "시간·비용 한도에서 끝내고 미완료를 성공으로 보고하지 않습니다.", "검사: 오류 뒤의 상태와 인계가 명확한가"],
      ].map(([symbol, label, title, detail, assertion]) => `<article class="rm-entry rm-test-case">${icon(symbol)}<small>${label}</small><h3>${title}</h3><p>${detail}</p><span>${assertion}</span></article>`).join(""),
      takeaway: "입력, 기대 결과, 허용하지 않을 행동, 판정자, 근거 리비전을 사례마다 고정합니다.",
      evidence: ["constitution", "llm"],
    }),
    slide({
      id: "good-abstention", chapter: 3, visual: "answers", state: "EXAMPLE",
      title: "좋은 답변은 무엇을 모르는지도 정확히 설명합니다",
      lead: "예시 질문: 이번 API 변경은 안전한가요? 현재 관계 근거는 리소스 20개 중 14개만 확인됐습니다.",
      body: `<article class="rm-answer is-unsupported"><small>${icon("hold")}실패 응답 예시</small><h3>일부 확인을 전체 승인으로 확대</h3><blockquote>확인한 리소스에 문제가 없으므로<br><mark>안전하게 배포할 수 있습니다.</mark></blockquote><p>미확인 여섯 개를 숨기고,<br>부분 조회를 전체 영향과 승인으로 확대했습니다.</p><span class="rm-answer-verdict">판정: 근거를 넘어선 주장</span></article>
        <article class="rm-answer is-bounded"><small>${icon("check")}기대 응답 예시</small><h3>근거, 한계, 다음 확인</h3><blockquote><span><b>확인</b>14개의 현재 관계를 확인했습니다.</span><span><b>한계</b>미매핑 3개, 접근 불가 2개,<br>오래된 근거 1개가 남아 있습니다.</span></blockquote><p>전체 영향은 아직 판단할 수 없습니다.<br>관계와 접근 범위를 보완한 뒤 다시 검토하세요.</p><span class="rm-answer-verdict">판정: 범위를 지킨 보류와 다음 확인</span></article>`,
      takeaway: "이 답변은 검토 자료입니다. 변경 승인이나 원인 확정을 대신하지 않습니다.",
      evidence: ["constitution", "llm"],
    }),
    slide({
      id: "measurement-layers", chapter: 3, visual: "measurement", state: "PROPOSAL",
      title: "검색, 답변, 업무 성과는 서로 다른 지표입니다",
      lead: "아래는 측정 설계 예시이며 실측 결과가 아닙니다. 높은 검색 품질만으로 운영 효과를 주장하지 않습니다.",
      body: `<div class="rm-metric-lenses">${[
        ["search", "검색", "필요한 근거 회수", "찾아낸 관련 근거", "판정된 관련 근거", "허용 문서·결과 수·질문 집합 고정"],
        ["document", "답변", "주장과 인용의 일치", "근거가 지지하는 주장", "평가한 사실 주장", "같은 리비전·기준으로 별도 판정"],
        ["hold", "보류", "미해결의 올바른 처리", "기대대로 보류한 사례", "보류가 필요한 사례", "누락·충돌·권한 부족을 별도 집계"],
        ["people", "업무", "검토 준비의 부담", "소요 시간 또는 사람 접점", "같은 기간의 완료 업무", "현재 절차와 비교 / 미완료 별도 표시"],
      ].map(([symbol, label, title, numerator, denominator, condition]) => `<article>${icon(symbol)}<div><small>${label}</small><h3>${title}</h3></div><div class="rm-metric-fraction"><span>${numerator}</span><span>${denominator}</span></div><p>${condition}</p></article>`).join("")}</div>`,
      takeaway: "실제 복구나 절감의 성공은 별도의 권위 있는 관측이 확인해야 합니다.",
      evidence: ["metrics", "llm", "constitution"],
    }),
    slide({
      id: "fair-baseline", chapter: 3, visual: "cohorts", state: "CONTRACT",
      title: "같은 문제를, 같은 조건에서 풀어야 비교할 수 있습니다",
      lead: "업무 진단용 현재 절차와 FDAI 성과 주장용 기준 시스템을 구분하고, 비교 기준을 먼저 고정합니다.",
      body: `<p class="rm-cohort-diagnostic"><strong>업무 진단: 현재 운영 절차 vs 파일럿</strong><span>현재 업무의 시간·누락·검토 부담을 같은 단위로 측정</span></p>
        <div class="rm-graph rm-cohort-experiment">${node("sample", "FDAI 성과 주장", "고정 기준 시스템 vs FDAI", "같은 시나리오·입력·기간\n리비전·단위·제외 조건 고정", "compare", "grid-column:1;grid-row:1 / 3")}
          ${edge("sample", "reference", "right", "grid-column:2;grid-row:1")}
          ${node("reference", "REFERENCE", "문서화된 단일 모델·비계층 기준", "동일 입력에서 측정 / 기준 시스템을 의도적으로 불리하게 만들지 않음", "document", "grid-column:3;grid-row:1")}
          ${edge("sample", "treatment", "right", "grid-column:2;grid-row:2")}
          ${node("treatment", "TREATMENT", "FDAI의 같은 리비전", "실패·미완료와 불확실성을 함께 비교 / 독립 평가", "ai", "grid-column:3;grid-row:2")}</div>
        <p class="rm-cohort-seal">개선에 사용한 사례와 최종 평가 사례를 분리합니다. 비교 전에 표본과 판정 기준을 고정합니다.</p>
        <p class="rm-policy-note"><strong>정책상 표본 하한</strong> 각 기준선과 처리군의 최소 표본은 30개입니다. 하한 충족만으로 통계적 충분성이나 개선이 입증되지는 않습니다.</p>`,
      takeaway: "관찰 모드의 답변 비교는 운영 성과 증명이 아닙니다. 합성 자료는 실운영 근거가 아닙니다.",
      evidence: ["metrics"],
    }),
    slide({
      id: "unit-economics", chapter: 3, visual: "economics", state: "PROPOSAL",
      title: "품질과 함께 완료 업무당 시간과 비용을 봅니다",
      lead: "싼 모델도 재검토가 많으면 비쌀 수 있습니다. 토큰 단가보다 업무를 끝내는 데 드는 비용이 중요합니다.",
      body: `<div class="rm-economics-formula"><small>업무 진단용 비용 모델 / 제안</small><h3>완료한 검토 1건당 비용</h3><div class="rm-cost-composition">${[
        ["ai", "모델"], ["search", "검색"], ["check", "검증"], ["data", "귀속 인프라"], ["people", "사람 검토"],
      ].map(([symbol, label]) => `<span>${icon(symbol)}<b>${label}</b></span>`).join('<i aria-hidden="true">+</i>')}</div><div class="rm-cost-denominator">같은 기간의 완료 업무 수</div><span>미완료 비용과 공통 간접비는 별도로 공개합니다. 각 비용의 포함 범위와 단위를 함께 기록합니다.</span></div>
        <div class="rm-budget-grid">${entry("응답 시간", "중앙값과 꼬리 지연", "p90(90% 완료 시점)과 시간 초과, 사용자 재시도도 따로 봅니다.")}${entry("비용 한도", "업무 단위 예산", "모델 호출과 추가 검증에 쓸 총량을 시작 전에 정합니다.")}${entry("실패 대응", "보류와 인계", "한도에 닿으면 무한 재시도하지 않고 부족한 근거를 남깁니다.")}</div>`,
      takeaway: "이 업무 비용 모델과 FDAI 공식 KPI의 비용 정의를 섞지 말고 각각의 포함 범위를 밝힙니다.",
      evidence: ["metrics", "llm"],
    }),
    slide({
      id: "ai-lifecycle", chapter: 3, visual: "ai-lifecycle", state: "GUIDE",
      title: "데이터나 모델이 바뀌면 평가 근거도 새로 만듭니다",
      lead: "모델뿐 아니라 문서, 검색 설정, 프롬프트, 정책과 평가 기준의 변경도 결과를 바꿀 수 있습니다.",
      body: reviewCycle([
        ["01 / 감지", "무엇이 달라졌나", "질문·인용 오류·지연·비용 변화 확인", "search"],
        ["02 / 고정", "무엇으로 재현하나", "소스·검색·프롬프트·모델 버전 연결", "document"],
        ["03 / 비교", "어디에서 회귀했나", "같은 평가 사례로 답변과 보류를 검사", "compare"],
        ["04 / 검토", "적용할까, 돌아갈까", "별도 검토와 이전 승인 리비전 확보", "cycle"],
      ]) + `<div class="rm-owner-strip"><strong>AI 평가 담당자</strong><span>회귀 분석과 개선 제안</span><strong>운영 책임자</strong><span>범위·인계·변경 검토</span></div>`,
      takeaway: "모델의 자기 채점만으로 통과시키지 않습니다. 학습이나 버전 변경이 권한을 높이지 않습니다.",
      evidence: ["llm", "governance", "constitution"],
    }),
  ];
}
