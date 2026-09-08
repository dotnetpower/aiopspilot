/** Chapters 1-2: frame one decision, then establish minimum usable evidence. */
import { entry, path, record, slide } from "./readiness-slide-kit.js";
import { convergence, dimensionMap, edge, icon } from "./readiness-diagrams.js";

/** Frame the first decision and its data requirements in thirteen teaching slides. */
export function buildReadinessFoundations() {
  return [
    slide({
      id: "demo-gap", chapter: 1, visual: "contrast", state: "GUIDE",
      title: "좋은 데모가 곧 운영 준비를 뜻하지는 않습니다",
      lead: "답변을 만드는 능력과 그 답변을 업무에 맡길 수 있는 조건은 다릅니다.",
      body: `<article class="rm-demo">${icon("ai")}<small>DEMONSTRATION</small><h3>질문에 답할 수 있다</h3><blockquote>이 변경의 영향을<br>요약해 주세요.</blockquote><div class="rm-graph rm-demo-output"><span data-rm-node="input">입력</span>${edge("input", "generation")}<span data-rm-node="generation">생성</span>${edge("generation", "answer")}<span data-rm-node="answer">답변</span></div><p>답변이 생긴 것과<br>업무를 맡길 수 있는 것은 다릅니다.</p></article>
        <section class="rm-operating-record"><small>OPERATION</small><h3>누락과 예외도 다룰 수 있는가?</h3>
          <div class="rm-proof-checks">${[
            ["target", "대상", "이름이 아니라 정확한 대상과 리비전 확인"],
            ["data", "근거", "누락·지연·접근 불가를 숨기지 않음"],
            ["people", "책임", "보류 기준과 이어받을 담당자를 지정"],
            ["check", "결과", "실제 효과를 별도의 관측으로 확인"],
          ].map(([symbol, label, detail]) => `<article>${icon(symbol)}<div><h3>${label}</h3><p>${detail}</p></div></article>`).join("")}</div></section>`,
      takeaway: "도입의 출발점은 모델 선택이 아니라, 맡길 판단과 확인할 근거입니다.",
      evidence: ["constitution"],
    }),
    slide({
      id: "two-lenses", chapter: 1, visual: "lenses", state: "PROPOSAL",
      title: "준비도는 이번 판단을, 성숙도는 반복할 능력을 봅니다",
      lead: "한 번의 파일럿이 가능한지와 조직이 그 품질을 유지할 수 있는지를 함께 살펴봅니다.",
      body: `<section class="rm-lens-panel"><small>READINESS / 이번 판단</small><h3>현재 범위의 한 장면</h3><div class="rm-snapshot-visual">${icon("target")}<strong>지금</strong><span>대상 / 근거 / 검토자</span></div><p>이번 범위의 근거와 실패 대응을 확인해<br>진행 또는 보류 의견을 남깁니다.</p></section>
        <section class="rm-lens-panel"><small>MATURITY / 반복할 능력</small><h3>변화 뒤에도 유지되는 품질</h3><div class="rm-graph rm-repeat-visual">${["진단", "검증", "인계"].map((label, index) => `<span data-rm-node="review-${index}">${icon(["search", "check", "people"][index])}<b>${label}</b></span>${index < 2 ? edge(`review-${index}`, `review-${index + 1}`) : ""}`).join("")}</div><p>사람과 데이터가 바뀌어도 절차를 반복하고,<br>결과를 보고 개선할 수 있는지 봅니다.</p></section>
        <div class="rm-lens-summary"><span>범위가 바뀌면 준비도를 다시 확인</span><span>담당자가 바뀌어도 근거를 인수인계</span></div>`,
      takeaway: "준비도와 성숙도는 검토를 돕는 정보입니다. 접근이나 실행 권한은 별도로 확인합니다.",
      evidence: ["constitution", "governance"],
    }),
    slide({
      id: "six-dimensions", chapter: 1, visual: "dimensions", state: "PROPOSAL",
      title: "여섯 가지 역량을 하나의 운영 판단에 연결합니다",
      lead: "기술, 데이터, 사람을 따로 채점하지 않고 같은 업무를 수행하는 데 필요한 근거로 연결합니다.",
      body: dimensionMap([
        ["01 / VALUE", "가치와 범위", "개선할 판단과 하지 않을 일을 정의", "target"],
        ["02 / DATA", "데이터 품질과 관리", "출처 계약과 결손 검사로 품질 확인", "data"],
        ["03 / CONTEXT", "의미와 서비스 맥락", "대상·관계·목표·담당자를 연결", "context"],
        ["04 / AI", "AI 평가와 변경 관리", "정답과 올바른 보류를 함께 평가", "ai"],
        ["05 / PEOPLE", "사람과 운영 절차", "예외 대응과 인수인계의 책임 지정", "people"],
        ["06 / GOVERNANCE", "통제와 안전한 변경", "사용 조건과 접근·실행 권한을 구분", "shield"],
      ]),
      takeaway: "종합점수 대신, 선택한 업무를 막는 구체적인 격차를 찾습니다.",
      evidence: ["constitution", "governance", "llm"],
    }),
    slide({
      id: "decision-charter", chapter: 1, visual: "charter", state: "EXAMPLE",
      title: "먼저, 맡길 업무를 한 문장으로 정의합니다",
      lead: "예시: 운영자가 API 변경을 검토할 때, 영향 근거와 미확인 범위를 한 번에 확인하도록 돕습니다.",
      body: `<div class="rm-charter-heading"><small>DECISION CHARTER / 작성 예시</small><h3>${icon("target")}변경 전 영향 검토 브리핑</h3><span class="rm-pill">읽기 전용 파일럿 제안</span></div>
        ${record([["사용자와 시점", "서비스 운영자 / 변경 검토 회의 전"], ["대상 범위", "선택한 API 워크로드와 관련 리소스 20개"], ["필요한 입력", "변경 차이, 현재 관계, 목표, 담당자"], ["최소 수집", "판단에 필요한 필드와 원문 참조만 사용"], ["확인할 결과", "근거를 찾는 시간과 누락 발견 여부"], ["하지 않을 일", "변경 승인, 리소스 수정, 원인 확정"]], "rm-record-grid")}`,
      takeaway: "대상과 목적을 먼저 정해야 필요 없는 데이터를 모으지 않을 수 있습니다.",
      evidence: ["constitution", "ontology", "governance"],
    }),
    slide({
      id: "pilot-selection", chapter: 1, visual: "selection", state: "PROPOSAL",
      title: "첫 업무는 작고, 반복 가능하며, 검토할 수 있어야 합니다",
      lead: "세 운영 영역 모두 시작점이 될 수 있습니다. 기대 가치만으로 데이터와 권한의 빈틈을 넘지 않습니다.",
      body: `<div class="rm-option-board">${[
        ["change", "변경 안전", "영향 브리핑", "변경 차이, 서비스 관계, 보호 목표", "자동 승인과 배포 실행"],
        ["shield", "복원력", "장애 근거 정리", "같은 사건의 관측, 시각, 기존 대응", "상관관계만으로 원인 확정"],
        ["cost", "비용", "검토 후보 설명", "비용 기간, 사용량, 신뢰성 제약", "예상 절감을 실현 절감으로 보고"],
      ].map(([symbol, label, title, need, excluded]) => `<article>${icon(symbol)}<small>${label}</small><h3>${title}</h3><div><span>먼저 확보</span><p>${need}</p></div><div class="rm-not-in-scope"><span>첫 검증에서 제외</span><p>${excluded}</p></div></article>`).join("")}</div>
        <div class="rm-question-strip"><b>공통 질문</b><span>현재 절차가 있나요?</span><span>효과를 따로 평가하나요?</span><span>사람이 이어받을 수 있나요?</span></div>`,
      takeaway: "읽기 파일럿도 접근 권한이 필요합니다. 상태 변경은 별도의 안전 심사 대상입니다.",
      evidence: ["constitution", "metrics"],
    }),
    slide({
      id: "evidence-supply", chapter: 2, visual: "supply", state: "GUIDE",
      title: "데이터마다 답할 수 있는 질문이 다릅니다",
      lead: "관측, 변경, 문서, 목표를 연결하되 각각이 무엇을 증명하는지 구분합니다.",
      body: convergence([
        ["관측", "지금 무엇이 보이나요?", "상태·지표·추적 정보와 관측 범위", "data"],
        ["변경", "무엇이 달라지나요?", "현재 상태와 고정된 계획 리비전의 차이", "change"],
        ["지식", "어떻게 검토해 왔나요?", "유효한 런북·절차와 근거가 있는 사례", "document"],
        ["목표", "무엇을 지켜야 하나요?", "서비스 목표·제약과 현재 담당자", "target"],
      ], ["BOUNDED EVIDENCE", "한 판단을 위한 근거 묶음", "대상·관계·시간·출처를 함께 확인\n문서 ≠ 현재 관측 ≠ 사용 권한\n빈틈은 추측 대신 미확인으로 기록", "context"]),
      takeaway: "많이 수집하는 것보다, 각 주장을 뒷받침하는 최소 근거를 연결하는 것이 중요합니다.",
      evidence: ["ontology", "governance"],
    }),
    slide({
      id: "data-contract", chapter: 2, visual: "data-contract", state: "EXAMPLE",
      title: "출처 하나에도 목적, 시간, 책임이 있는 계약을 둡니다",
      lead: "예시: 변경 영향 브리핑이 읽을 자산 관계 자료의 사용 조건을 작성합니다.",
      body: `<header class="rm-document-heading"><div><small>SOURCE CONTRACT / 작성 예시</small><h3>${icon("document")}API 워크로드의 현재 관계 자료</h3></div><span class="rm-pill">실제 운영 설정 아님</span></header>
        ${record([["목적과 필드", "영향 검토 / 대상 참조, 관계, 출처 시각"], ["원본과 리비전", "승인된 자산 목록 / 평가 시점의 고정본"], ["소유자와 범위", "플랫폼 담당자 / 선택한 리소스 20개"], ["시간 기준", "기준 시점과 출처별 최신성 정책"], ["품질 실패", "미매핑, 접근 불가, 지연을 별도 기록"], ["접근과 보존", "허용된 검토자 / 승인된 보존·삭제 정책"]], "rm-record-grid")}`,
      takeaway: "출처 연결 성공만으로 준비 완료가 아닙니다. 계약을 위반한 입력의 처리도 정의합니다.",
      evidence: ["governance", "constitution"],
    }),
    slide({
      id: "quality-tests", chapter: 2, visual: "quality", state: "PROPOSAL",
      title: "품질은 좋은 점수보다 결함을 찾는 검사로 설명합니다",
      lead: "판단에 중요한 필드부터 검사하고, 실패한 항목을 분모와 검토 기록에 남깁니다.",
      body: `<div class="rm-quality-lab">${[
        ["completeness", "완전성", "예정된 대상과 관측 범위를 대조", "누락을 정상으로 보지 않음", '<b></b><b></b><b></b><b></b><b></b><b class="is-missing"></b>'],
        ["accuracy", "정확성", "정확한 식별자를 원본과 대조", "다른 대상이면 판단 보류", '<span>대상 A</span><i>≠</i><span>대상 B</span>'],
        ["freshness", "최신성", "출처 시각과 유효 구간을 비교", "만료 근거는 현재 판단에서 제외", `${icon("clock")}<span>관측 / 만료 / 도착</span>`],
        ["consistency", "일관성", "단위·상태·관계의 충돌을 확인", "평균으로 충돌을 지우지 않음", '<span>주장 A</span><i>≠</i><span>주장 B</span>'],
        ["uniqueness", "유일성", "같은 사건의 재수집을 구분", "중복을 새 표본으로 세지 않음", '<span>사건 A</span><i>=</i><span>사건 A</span>'],
        ["lineage", "추적성", "출처·리비전·변환 경로를 재현", "경로가 끊기면 미확인으로 기록", `${icon("link")}<span>원본 / 변환 / 인용</span>`],
      ].map(([kind, title, check, failure, motif]) => `<article><div class="rm-quality-motif rm-motif-${kind}" aria-hidden="true">${motif}</div><h3>${title}</h3><p>${check}</p><span class="rm-failure-rule">${failure}</span></article>`).join("")}</div>`,
      takeaway: "품질 기준은 업무별로 합의합니다. 임의의 공통 통과율을 만들지 않습니다.",
      evidence: ["constitution", "governance", "metrics"],
    }),
    slide({
      id: "coverage", chapter: 2, visual: "coverage", state: "EXAMPLE",
      title: "보이지 않는 여섯 개도 평가 대상에 남아 있어야 합니다",
      lead: "예시: 선택한 리소스 20개 중 현재 검토된 관계를 확인한 것은 14개입니다.",
      body: `<div class="rm-coverage-head"><div><small>검토된 현재 관계의 확인 비율 / 예시</small><strong>14 <span>/ 20</span></strong></div><div class="rm-resource-waffle" role="img" aria-label="20개 리소스 각각의 상태를 유지합니다. 확인 14, 미매핑 3, 접근 불가 2, 지연 1.">${Array.from({ length: 20 }, (_, index) => `<span data-rm-unit="${index < 14 ? "verified" : index < 17 ? "gap" : index < 19 ? "restricted" : "stale"}" aria-hidden="true">${index < 14 ? "✓" : index < 17 ? "?" : index < 19 ? "×" : "!"}</span>`).join("")}</div><p>기준 시점: 10:00 UTC<br>고정 범위: 리소스 20개 / 제외 0개<br>확인 조건: 대상·관계·최신성 근거 충족</p></div>
        <div class="rm-coverage-strip" data-rm-total="20" role="img" aria-label="예시: 확인 14개, 미매핑 3개, 접근 불가 2개, 오래된 근거 1개. 전체 20개.">
          <span class="is-verified" data-rm-count="14" style="width:70%">확인 14</span><span class="is-gap" data-rm-count="3" style="width:15%">미매핑 3</span><span class="is-restricted" data-rm-count="2" style="width:10%">접근 불가 2</span><span class="is-stale" data-rm-count="1" style="width:5%">지연 1</span></div>
        <div class="rm-coverage-equation"><strong>70%</strong><p>14 / 20 = 70%<br>확인한 14개만 분모로 삼아 100%라고 보고하지 않습니다.</p><b>여섯 개의 미확인이<br>전체 영향 판단을 제한합니다.</b></div>`,
      takeaway: "이 비율은 예시의 관계 확인 범위일 뿐, 성숙도 점수나 파일럿 승인 기준이 아닙니다.",
      evidence: ["constitution", "metrics"],
    }),
    slide({
      id: "time", chapter: 2, visual: "time", state: "EXAMPLE",
      title: "방금 수집한 정보도 이미 오래된 사실일 수 있습니다",
      lead: "예시 정책은 관측 이후 5분까지만 현재 판단에 재사용하도록 허용합니다.",
      body: `<div class="rm-time-chart"><div class="rm-time-window" data-rm-duration="10"><div class="rm-valid-window" data-rm-duration="5" style="width:50%"><strong>판단에 사용 가능한 5분</strong></div><div class="rm-expired-window" style="width:50%"><strong>만료 이후 / 현재 근거로 재사용 불가</strong></div></div>
        <div class="rm-time-axis" data-rm-total-minutes="10">${[
          [0, "09:50 UTC", "사건과 관측"], [5, "09:55 UTC", "최신성 만료"], [8, "09:58 UTC", "FDAI에 도착"], [10, "10:00 UTC", "판단 기준 시점"],
        ].map(([minute, time, label]) => `<div class="rm-time-marker" data-rm-minute="${minute}" style="left:${minute * 10}%"><i aria-hidden="true"></i><div><strong>${time}</strong><span>${label}</span></div></div>`).join("")}</div>
        <div class="rm-time-explanation">${entry("시간축은 실제 간격에 비례 / 예시", "수집 시각은 새로워도 사실은 만료", "8분 뒤 도착한 관측이 5분 유효 기간을 늘리지 않습니다.")}${entry("판단 기준 시점의 대응", "재관측하거나 현재 판단을 보류", "사건·기록 시각과 유효 구간을 남겨 같은 판단을 재현합니다.")}</div></div>`,
      takeaway: "늦은 근거는 별도 리비전으로 남깁니다. 과거 판단의 근거를 덮어쓰지 않습니다.",
      evidence: ["constitution", "ontology"],
    }),
    slide({
      id: "semantic-spine", chapter: 2, visual: "semantic", state: "EXAMPLE",
      title: "리소스에 서비스의 의미와 책임을 연결합니다",
      lead: "예시의 API 변경을 이해하려면 정확한 리소스가 어떤 워크로드와 서비스에 연결되는지 알아야 합니다.",
      body: path([
        ["BusinessService", "주문 서비스", "보호할 목표와 서비스 책임자의 기준", "people"],
        ["Workload", "API 워크로드", "변경 검토와 운영 인수인계의 단위", "context"],
        ["Resource", "선택한 실행 리소스", "관측된 대상과 출처 리비전", "data"],
      ], ["구현 관계<small>implemented_by</small>", "실행 위치<small>workload_runs_on</small>"])
        + `<div class="rm-semantic-notes">${entry("맥락을 보완하는 연결", "목표와 담당자", "서비스의 승인된 목표와 현재 소유권도 별도 근거로 확인합니다.")}${entry("해석의 한계", "관계는 원인이나 권한이 아닙니다", "연결이 없으면 미매핑으로 남깁니다. 이름이 비슷하다고 채우지 않습니다.")}</div>`,
      takeaway: "온톨로지는 대상과 관계의 의미를 맞춥니다. 현재 상태와 접근 권한은 별도로 검증합니다.",
      evidence: ["ontology", "constitution"],
    }),
    slide({
      id: "knowledge", chapter: 2, visual: "knowledge", state: "EXAMPLE",
      title: "검색된 문서가 곧 답변의 근거가 되지는 않습니다",
      lead: "검색 증강 생성(RAG)은 검색한 자료를 답변 생성에 연결합니다. 접근 권한과 인용 근거도 확인해야 합니다.",
      body: path([
        ["01 / 접근 범위", "허용 문서만", "읽기 권한과 원본 사용 조건을 먼저 확인", "shield"],
        ["02 / 검색", "관련 구절 찾기", "허용 집합 안에서 검색과 순위 계산", "search"],
        ["03 / 검증", "주장과 대조", "대상·리비전·구절이 주장을 지지하는지 확인", "compare"],
        ["04 / 답변", "근거와 한계", "지지되는 주장만 인용하고 미확인을 공개", "document"],
      ]) + `<div class="rm-retrieval-review"><span class="rm-review-old">${icon("hold")}이전 리비전: 현재 영향 근거에서 제외</span><span>${icon("check")}현재 자료: 관련 주장에 한정해 인용</span></div>`,
      takeaway: "문서가 없거나 충돌하면 그 한계를 설명합니다. 검색 점수로 빈 근거를 대체하지 않습니다.",
      evidence: ["ingestion", "llm"],
    }),
    slide({
      id: "data-lifecycle", chapter: 2, visual: "lifecycle", state: "CONTRACT",
      title: "데이터를 넣는 순간부터 지우는 순간까지 준비합니다",
      lead: "원문과 요약뿐 아니라 임베딩(검색용 수치 표현)에도 원본의 접근, 보존, 삭제 조건이 이어져야 합니다.",
      body: `<div class="rm-lifecycle-track">${[
        ["data", "분류와 수집", "목적에 필요한 최소 필드", "소유자 / 분류 / 수집 목적"],
        ["shield", "모델 전송", "지역·보존·학습 사용 조건", "비식별화 / 승인된 처리자"],
        ["search", "검색과 공유", "사용자와 원본의 접근 범위", "문서와 파생 자료의 권한 대조"],
        ["cycle", "보존과 삭제", "삭제·법적 보존의 처리 경로", "원본 / 조각 / 임베딩의 완료 확인"],
      ].map(([symbol, title, check, proof], index) => `<article>${icon(symbol)}<small>0${index + 1}</small><h3>${title}</h3><p>${check}</p><span>${proof}</span></article>`).join("")}</div>
        <div class="rm-inheritance-band"><strong>원본의 사용 조건을 함께 유지</strong><span>원문</span><i aria-hidden="true">/</i><span>요약·인용 조각</span><i aria-hidden="true">/</i><span>임베딩</span></div>
        <p class="rm-full-note">분류나 모델 사용 승인이 미확인이면 전송을 보류합니다. 충분히 비식별화할 수 없는 입력도 보내지 않습니다.</p>`,
      takeaway: "저장 기간이나 모델 약관은 보편값이 아닙니다. 각 배포의 책임자가 승인해야 합니다.",
      evidence: ["governance", "ingestion"],
    }),
  ];
}
