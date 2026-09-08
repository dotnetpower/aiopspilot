import { slide, entry, flow, table, sources as s } from "./ontology-slide-kit.js";

/** Slides 15-28: identity, time, evidence, and the semantic boundary. */
export function contractSlides() {
  return [
    slide({
      state: "ILLUSTRATIVE", chapter: "14 / PRIMITIVES", layout: "primitive-map",
      title: "타입과 실제 대상은 구분해서 읽습니다",
      lead: "클래스, 인스턴스, 속성, 관계를 구분하면 질문의 각 부분을 검증할 수 있습니다.",
      body: `<div class="oe-split"><aside class="oe-specimen"><small>설명용 관측 예시</small><strong>Resource<br>vm-01</strong><code>power_state = running</code><p>NIC-01 attached_to VM-01</p></aside>
        ${table(["요소", "검증하는 의미"], [
          ["타입 / ResourceType", "어떤 속성과 의미가 허용되는가"],
          ["인스턴스 / Resource", "어떤 실제 대상을 가리키는가"],
          ["속성 / power_state", "값의 종류·단위·범위가 맞는가"],
          ["관계 / attached_to", "방향과 끝점 타입이 맞는가"],
        ])}</div>`,
      takeaway: "타입 선언은 현재 상태가 아닙니다. 정체성·속성·관계마다 시간과 출처가 있는 관측을 연결합니다.",
      evidence: [s.ontology, s.structural],
    }),
    slide({
      state: "BOUNDARY", chapter: "15 / RELATIONSHIP DIRECTION", layout: "relation-compass",
      title: "관계의 방향과 원인은 같은 뜻이 아닙니다",
      lead: "저장 방향, 탐색 방향, 유효 시간, 인과성은 한 간선에서도 서로 다른 의미입니다.",
      body: `<div class="oe-split oe-narrow-left"><div class="oe-vertical-relation" role="img" aria-label="저장 방향: Workload에서 Database로 depends_on"><div class="oe-relation-node"><strong>Workload</strong></div><div class="oe-vertical-edge"><span>depends_on</span><i aria-hidden="true"></i></div><div class="oe-relation-node"><strong>Database</strong></div></div>
        ${table(["구분", "해석"], [
          ["저장", "의존하는 대상에서 필요한 대상 방향으로 기록"],
          ["탐색", "outgoing / incoming을 선택해 읽기"],
          ["시간", "관계가 유효했던 구간을 근거와 함께 보존"],
          ["인과", "연결만으로 원인이라고 확정하지 않기"],
        ])}</div>`,
      takeaway: "역방향으로 조회해도 저장된 간선은 바뀌지 않습니다. 상관관계와 인과관계는 별도 근거로 구분합니다.",
      evidence: [s.structural, s.metamodel],
    }),
    slide({
      state: "CURRENT", chapter: "16 / STABLE IDENTITY", layout: "identity-anchor",
      title: "이름이 바뀌어도 대상의 정체성은 남습니다",
      lead: "표시 이름과 객체 식별자, 해석에 사용한 온톨로지 버전을 따로 보존합니다.",
      body: `<div class="oe-identity"><div class="oe-name-change"><div><small>표시 이름 예시 / 어제</small><strong>payments-vm-01</strong></div><span aria-hidden="true">→</span><div><small>표시 이름 예시 / 오늘</small><strong>checkout-worker-a</strong></div></div>
        <div class="oe-identity-anchor"><small>두 이름이 가리키는 동일 대상</small><strong>ObjectRef</strong><span>정확한 provider identity + type_ref</span></div>
        <div class="oe-two">${entry("공급자 정체성이 달라지면", "같은 이름이어도 병합하지 않음", "새 대상인지, 검토된 매핑이 있는지 확인합니다.")}${entry("의미 버전이 달라지면", "정확한 릴리스로 다시 검증", "불일치하면 해석을 멈추고 호환성을 검토합니다.")}</div></div>`,
      takeaway: "재생에는 대상의 ObjectRef와 사용한 OntologyRelease digest가 함께 필요합니다.",
      evidence: [s.ontology, s.platform],
    }),
    slide({
      state: "BOUNDARY", chapter: "17 / STATE AUTHORITY", layout: "authority-lanes",
      title: "관측, 해석, 목표, 실행은 서로 다른 사실입니다",
      lead: "같은 대상에 대한 상태라도 권위 있는 출처와 용도가 다르면 서로 대체할 수 없습니다.",
      body: table(["상태 영역", "설명하는 것", "근거의 소유"], [
        ["OBSERVED / 관측", "공급자가 보고한 현재 전원 상태", "외부의 권위 있는 관측 출처"],
        ["DERIVED / 해석", "degraded 판단이나 용량 예측", "버전이 있는 함수와 입력 근거"],
        ["DESIRED / 목표", "SLO·예산·정책상 목표 상태", "승인된 운영 의도와 설정"],
        ["EXECUTION / 실행", "계획·명령 발송·실행 결과", "Process와 실행 감사 기록"],
      ]),
      takeaway: "명령을 수락했다는 기록은 회복 관측이 아닙니다. 실행 결과를 관측 사실로 바꾸려면 독립 재관측이 필요합니다.",
      evidence: [s.ontology, s.metamodel, s.constitution],
    }),
    slide({
      state: "CURRENT", chapter: "18 / TIME & PROVENANCE", layout: "time-ribbon",
      title: "도착한 정보가 지금도 유효한 정보는 아닙니다",
      lead: "발생·유효·기록·신선도는 정해진 순서의 네 점이 아니라, 근거를 읽는 네 가지 질문입니다.",
        body: `<div class="oe-time-reading">${table(["시간의 의미", "확인할 질문"], [
        ["event_time", "언제 발생했는가?"], ["effective_time", "어느 구간에 유효한가?"],
        ["recorded_time", "언제 수락·기록했는가?"], ["fresh_until", "언제까지 재사용할 수 있는가?"],
        ])}<figure class="oe-freshness-chart"><figcaption>신선도 만료 뒤에 도착한 관측 / 예시</figcaption>
          <svg class="oe-inline-diagram" viewBox="0 0 760 260" role="img" aria-label="10시 발생한 사건의 근거가 10시 5분에 만료되고 10시 6분에 기록됩니다. 도착 시점에는 재사용할 수 없습니다.">
            <path class="oe-fresh-window" d="M44 124H544"/><path class="oe-expired-window" d="M544 124H728"/>
            <text class="oe-diagram-detail" x="294" y="98" text-anchor="middle">재사용 가능 구간</text>
            <circle class="oe-diagram-dot" cx="44" cy="124" r="5"/>
            <text class="oe-diagram-label" x="44" y="185">10:00</text><text class="oe-diagram-detail" x="44" y="218">사건 발생</text>
            <path class="oe-expiry-marker" d="M544 77V149"/>
            <text class="oe-diagram-label" x="544" y="30" text-anchor="middle">10:05</text><text class="oe-diagram-detail" x="544" y="62" text-anchor="middle">신선도 만료</text>
            <path class="oe-arrival-marker" d="M644 124V180"/><rect class="oe-diagram-dot" x="639" y="119" width="10" height="10"/>
            <text class="oe-diagram-label" x="644" y="209" text-anchor="middle">10:06</text><text class="oe-diagram-detail" x="644" y="242" text-anchor="middle">관측 기록</text>
          </svg><p>도착 시점에는 만료된 근거입니다.<br>현재 상태는 새 관측으로 확인합니다.</p>
        </figure></div>`,
      takeaway: "시간과 함께 출처·리비전·완전성·충돌을 보존합니다. 늦은 근거는 새 리비전이며 과거 판단을 덮어쓰지 않습니다.",
      evidence: [s.ontology, s.governance, s.constitution],
    }),
    slide({
      state: "BOUNDARY", chapter: "19 / WORKING WITH UNKNOWN", layout: "unknown-spectrum",
      title: "모른다는 결과도 다음 행동을 안내해야 합니다",
      lead: "무엇이 부족한지 구분하면 추측 대신 범위가 정해진 복구와 확인으로 이어갈 수 있습니다.",
      body: `<div class="oe-definition-grid">${entry("UNKNOWN SERVICE", "서비스 연결이 미확인입니다", "서비스·워크로드의 승인된 매핑을 요청합니다.")}${entry("UNCLASSIFIED", "타입 분류가 미검토 상태입니다", "원시 타입과 근거를 함께 분류 검토로 보냅니다.")}${entry("UNAVAILABLE", "권위 있는 출처를 읽을 수 없습니다", "기한 내 재수집 또는 사람 검토로 이어갑니다.")}${entry("INCOMPLETE", "요청 범위를 일부만 보았습니다", "질의를 좁히거나 완전한 관측 근거를 모읍니다.")}</div>`,
      takeaway: "복구되면 새 근거로 다시 판단합니다. 복구되지 않으면 보류·변경 없음·감사를 남기며 권한을 높이지 않습니다.",
      evidence: [s.ontology, s.platform],
    }),
    slide({
      state: "CURRENT", chapter: "20 / VERSIONED MEANING", layout: "release-rings",
      title: "의미를 바꾸려면 새 릴리스가 필요합니다",
      lead: "과거 판단은 당시의 의미로 재생하고, 새 선언은 정확한 버전과 digest로 구분합니다.",
      body: `<div class="oe-release-pair"><div><small>과거 판단을 재생</small><strong>Release A</strong><span>A의 선언과 digest 유지</span></div><div><small>새로운 판단에 적용</small><strong>Release B</strong><span>새 선언과 호환성 판정</span></div></div>
        ${table(["호환성", "사용 조건"], [["COMPATIBLE", "기존 소비자가 읽을 수 있는 변경"], ["MIGRATION REQUIRED", "명시적인 변환과 근거 확인 후 사용"], ["INCOMPATIBLE", "자동 수락하지 않고 A와 B의 경로 분리"]])}`,
      takeaway: "새 릴리스가 과거 기록의 의미를 바꾸지는 않습니다. 최신값으로 과거의 판단을 재작성하지 않습니다.",
      evidence: [s.platform, s.structural],
    }),
    slide({
      state: "ILLUSTRATIVE", chapter: "21 / AN UNGROUNDED REQUEST", layout: "failure-cascade",
      title: "그럴듯한 재시작 제안은 어디서 잘못될까요?",
      lead: "예시 요청: 결제 서비스가 느려. 재시작해줘. 네 가지 확인 없이 바로 행동할 수는 없습니다.",
      body: `<div class="oe-four">${entry("01 / 잘못된 대상", "정체성 확인", "이름 대신 정확한 타입과 ObjectRef를 확인합니다.")}${entry("02 / 오래된 문서", "현재 근거 확인", "유효 시간·출처·릴리스가 지금 판단에 맞는지 봅니다.")}${entry("03 / 승인 없는 요청", "행동 자격 확인", "정책·위험·필요한 사람 승인을 따로 확인합니다.")}${entry("04 / 수락뿐인 성공", "실제 효과 확인", "Heimdall(독립 관측 담당) 에이전트의 근거로 확인합니다.")}</div>`,
      takeaway: "어느 확인에서든 근거가 부족하면 변경 없이 멈추고, 필요한 대상 확인·관측·승인을 안내합니다.",
      evidence: [s.llm, s.constitution, s.ontology],
    }),
    slide({
      state: "BOUNDARY", chapter: "22 / THE LIMIT OF RETRIEVAL", layout: "rag-sieve",
      title: "관련 문서를 찾았다고 현재 사실이 되지는 않습니다",
      lead: "RAG는 자료 후보를 찾습니다. 대상·유효 시간·접근 범위·완전성은 여전히 검증해야 합니다.",
      body: `<div class="oe-retrieval-caption"><small>예시 질문</small><strong>이 Workload의 복구 절차는?</strong></div>
        <div class="oe-document-strip"><article><small>관련 문서 / A</small><strong>Runbook</strong><p>이름은 같지만<br>다른 ObjectRef</p><span>이 대상의 근거에서 제외</span></article><article><small>관련 문서 / B</small><strong>Incident</strong><p>정확한 대상이지만<br>이전 릴리스</p><span>현재 적용성을 다시 확인</span></article><article><small>관련 문서 / C</small><strong>Policy</strong><p>현재 문서지만<br>범위 일부만 설명</p><span>부분 근거로 표시하고 보완</span></article></div>`,
      takeaway: "관련성과 권위는 다릅니다. 충분한 현재 근거가 없으면 판단을 보류하고 부족한 항목을 설명합니다.",
      evidence: [s.llm, s.governance, s.platform],
    }),
    slide({
      state: "BOUNDARY", chapter: "23 / SIMILARITY IS NOT IDENTITY", layout: "similarity-map",
      title: "벡터에서 가깝다는 것은 같다는 뜻이 아닙니다",
      lead: "임베딩은 후보의 순서를 정하는 데 유용합니다. 대상의 동일성이나 원인을 증명하지는 않습니다.",
      body: `<div class="oe-split"><div class="oe-similarity" role="img" aria-label="설명용 유사도 개념도. timeout과 latency는 가까운 표현이지만 동일 대상이나 원인의 증명이 아닙니다."><small>유사도 개념도 / 측정 데이터 아님</small><svg viewBox="0 0 560 300" aria-hidden="true"><ellipse cx="224" cy="132" rx="170" ry="94"/><circle cx="130" cy="106" r="6"/><text x="147" y="114">timeout</text><circle cx="235" cy="164" r="6"/><text x="252" y="172">latency</text><circle cx="412" cy="247" r="6"/><text x="302" y="285">throttle</text></svg></div>
        <div class="oe-stack">${entry("후보 검색", "비슷한 표현을 찾습니다", "관련성이 높아도 아직 대상과 원인은 미확정입니다.")}${entry("의미 확인", "정확한 대상과 관계를 맞춥니다", "ObjectRef·LinkType 방향·릴리스를 검증합니다.")}${entry("판단 경계", "현재 근거와 자격을 확인합니다", "신선도·완전성·정책·필요한 승인을 따로 확인합니다.")}</div></div>`,
      takeaway: "유사도는 검토 순서를 돕습니다. 인과 판정과 실행 권한을 대신하지 않습니다.",
      evidence: [s.llm, s.behavior, s.constitution],
    }),
    slide({
      state: "PRINCIPLE", chapter: "24 / GROUNDED INTERPRETATION", layout: "grounding-bridge",
      title: "후보는 넓게 만들고, 의미는 좁게 검증합니다",
      lead: "자연어 해석은 계획 입력이 될 수 있지만, 곧바로 실행 명령이 되지는 않습니다.",
      body: `${flow([["생성", "해석 후보", "단어·임베딩·모델로<br>가능한 뜻을 찾기"], ["의미 검증", "검증된 계획", "정확한 릴리스와<br>해결된 용어에 고정"], ["판단 경로", "정책·위험·승인", "일반 판단 경로에서<br>행동 자격을 검토"]])}
        <div class="oe-outcomes"><span><b>적격</b> 다음 게이트 검토</span><span><b>근거 부족</b> 보류·재수집</span><span><b>T2 불일치</b> 사람 검토</span><span><b>정책 위반</b> 변경 없이 차단</span></div>`,
      takeaway: "적격은 실행 확정이 아닙니다. 필요한 승인과 일곱 안전장치, 독립 효과 확인은 그대로 적용됩니다.",
      evidence: [s.platform, s.constitution, s.agentLoop],
    }),
    slide({
      state: "CURRENT", chapter: "25 / PROOF-CARRYING PLAN", layout: "proof-chain",
      title: "검증된 의미 계획도 실행 권한은 없습니다",
      lead: "모든 용어와 인자를 고정할 근거가 있어야 후보를 검증된 계획으로 바꿀 수 있습니다.",
      body: `<div class="oe-proof"><div class="oe-proof-names"><div><small>후보</small><code>SemanticInterpretationCandidate</code></div><div><small>모든 용어 해결 후</small><code>VerifiedSemanticPlan</code></div></div>
        ${table(["허용되는 의미 근거", "확인하는 것"], [["EXACT_CATALOG", "활성 릴리스의 정확한 선언"], ["PROMOTED_SURFACE", "검토 후 승격된 의미 표현"], ["OPERATOR_CONFIRMATION", "인증된 운영자의 대상·범위 확인"]])}</div>`,
      takeaway: "하나라도 미해결이면 계획을 만들지 않습니다. VerifiedSemanticPlan.execution_authority는 항상 false입니다.",
      evidence: [s.platform, s.agentLoop],
    }),
    slide({
      state: "FOUNDATION", chapter: "26 / THE OPERATING SPINE", layout: "operating-spine",
      title: "기술 이벤트를 서비스의 운영 결과와 연결합니다",
      lead: "대상만이 아니라 목표, 선택지, 실행 시도, 실제 효과까지 같은 의미로 읽어야 합니다.",
      body: `<ol class="oe-spine"><li><b>01</b><div><strong>무엇을 운영하는가</strong><code>BusinessService · Workload · Resource</code></div><p>서비스와 실제 자원의 범위를 고정</p></li><li><b>02</b><div><strong>무엇을 지키려는가</strong><code>Objective · Change</code></div><p>SLO·복구·비용 목표와 변경을 연결</p></li><li><b>03</b><div><strong>어떤 선택이 가능한가</strong><code>DecisionCase · ActionOption</code></div><p>무조치 기준선과 대안을 함께 비교</p></li><li><b>04</b><div><strong>실제로 무엇이 달라졌는가</strong><code>ActionRun · ObservedOutcome</code></div><p>실행 시도와 독립 관측을 구분</p></li></ol>`,
      takeaway: "중간 객체나 관계가 미해결이면 그 지점에서 멈춥니다. 다음 단계의 사실이나 권한을 추측하지 않습니다.",
      evidence: [s.ontology, s.platform],
    }),
    slide({
      state: "FOUNDATION", chapter: "27 / DECLARATION AND OBSERVATION", layout: "dual-wheel",
      title: "질문의 종류와 선언의 종류를 구분합니다",
      lead: "운영자의 다섯 질문이 모두 릴리스 선언이 되는 것은 아닙니다. 상태와 맥락은 근거에 묶인 산출물입니다.",
      body: `${table(["운영 질문", "답을 담는 형태", "고정할 기준"], [
        ["Object · Relationship · Action", "ObjectType · LinkType · ActionType", "선언 버전과 릴리스"],
        ["State · Context", "상태 사실 · 맥락 스냅샷", "시간·출처·완전성"],
        ["공유 역량과 연산", "InterfaceType · FunctionType", "query / derive / validate / plan"],
      ])}<div class="oe-inline-note"><strong>선언은 의미를, 관측은 현재 상태를 설명합니다.</strong><p>StateType과 ContextType을 새 선언 종류로 만들지 않습니다.</p></div>`,
      takeaway: "릴리스 선언과 런타임 산출물을 분리해야 과거 판단의 의미와 당시 근거를 함께 재생할 수 있습니다.",
      evidence: [s.metamodel, s.platform],
    }),
  ];
}
