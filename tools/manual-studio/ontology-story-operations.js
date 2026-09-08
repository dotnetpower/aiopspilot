import { slide, entry, flow, table, sources as s } from "./ontology-slide-kit.js";

function agentPort(role, name, description) {
  return `<article class="oe-agent-port" data-agent="${name}"><small>${role}</small><strong>${name}</strong><p>${description}</p><i class="oe-bus-connector" aria-hidden="true"></i></article>`;
}

/** Slides 29-40: bounded questions, agent responsibility, effects, and adoption. */
export function operationSlides() {
  return [
    slide({
      state: "ILLUSTRATIVE", chapter: "28 / A BOUNDED QUESTION", layout: "objectset-worked",
      title: "ObjectSet은 질문의 범위와 한도를 명시합니다",
      lead: "예시: 이 Workload가 의존하는 데이터 서비스는? 대상·관계·깊이·한도를 필드로 고정합니다.",
      body: `<div class="oe-bounded-query"><figure class="oe-query-diagram"><figcaption><span>depends_on / outgoing · 깊이 1</span><span>점선 안: 반환 대상</span></figcaption>
        <svg class="oe-inline-diagram" viewBox="0 0 780 314" role="img" aria-label="예시 조회: Workload를 루트로 depends_on 관계를 한 단계 탐색하면 Database와 Cache 두 대상이 반환됩니다. 점선은 반환 대상의 범위입니다.">
          <defs><marker id="oe-query-direction" viewBox="0 0 8 8" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0L8 4L0 8Z"/></marker></defs>
          <rect class="oe-query-scope" x="456" y="1" width="316" height="312" rx="12"/>
          <path class="oe-query-edge" data-diagram-edge="database" data-from="root" data-to="database" d="M250 133H372V64H494"/>
          <path class="oe-query-edge" data-diagram-edge="cache" data-from="root" data-to="cache" d="M250 181H372V250H494"/>
          <g class="oe-query-node"><rect data-diagram-node="root" x="18" y="109" width="232" height="96" rx="6"/><text class="oe-diagram-label" x="134" y="150" text-anchor="middle">Workload</text><text class="oe-diagram-detail" x="134" y="182" text-anchor="middle">루트 / ObjectRef</text></g>
          <g class="oe-query-node"><rect data-diagram-node="database" x="494" y="18" width="244" height="92" rx="6"/><text class="oe-diagram-label" x="616" y="59" text-anchor="middle">Database</text><text class="oe-diagram-detail" x="616" y="89" text-anchor="middle">반환 대상</text></g>
          <g class="oe-query-node"><rect data-diagram-node="cache" x="494" y="204" width="244" height="92" rx="6"/><text class="oe-diagram-label" x="616" y="245" text-anchor="middle">Cache</text><text class="oe-diagram-detail" x="616" y="275" text-anchor="middle">반환 대상</text></g>
        </svg></figure><aside class="oe-bounded-receipt"><small>설명용 질의 영수증</small><strong>2<span>개 대상</span></strong><dl><div><dt>반환 한도</dt><dd>최대 100개</dd></div><div><dt>시점·해석</dt><dd>현재 cutoff · 정확한 릴리스</dd></div><div><dt>조회 완전성</dt><dd>잘림 없음</dd></div></dl><p>읽기 근거이며<br>실행 권한은 없습니다.</p></aside></div>`,
      takeaway: "ObjectSet 결과는 범위가 있는 읽기 근거입니다. 반환된 객체가 있다는 사실만으로 원인이나 실행 자격이 정해지지 않습니다.",
      evidence: [s.platform, s.structural],
    }),
    slide({
      state: "ILLUSTRATIVE", chapter: "29 / COMPLETENESS", layout: "completeness-tree",
      title: "결과가 없다는 말보다 완전성부터 확인합니다",
      lead: "빈 결과는 요청 범위를 완전히 확인했을 때만 부재 근거가 됩니다. 잘린 결과라면 이유를 먼저 읽습니다.",
      body: `${table(["조회 결과의 상태", "뜻하는 것", "다음 행동"], [
        ["잘림 없음", "요청 범위의 조회 완료", "0개라면 그 범위의 부재 검토"],
        ["RESULT_LIMIT", "반환 수 한도에 도달", "허용된 한도 조정 또는 질의 분할"],
        ["CANDIDATE_LIMIT", "필터 전 후보 일부만 확인", "조건을 좁혀 다시 조회"],
        ["TRAVERSAL_LIMIT", "관계 탐색 일부만 확인", "루트·깊이·범위를 좁혀 재조회"],
      ])}<div class="oe-receipt-line"><code>ObjectSetMaterialization</code><span>truncated + truncation_reason</span><small>실제 계약의 잘림 표시</small></div>`,
      takeaway: "조회가 잘리지 않았어도 관측 출처 자체가 불완전하면 부재를 단정할 수 없습니다. 범위와 원천 근거를 함께 확인합니다.",
      evidence: [s.platform, s.constitution],
    }),
    slide({
      state: "CURRENT", chapter: "30 / ACCOUNTABLE AGENTS", layout: "agent-swimlane",
      title: "같은 의미를 읽되, 각자의 책임으로 협업합니다",
      lead: "주요 역할의 협업 개념도입니다. 에이전트는 직접 호출하지 않고 검증된 이벤트를 게시·구독합니다.",
      body: `<div class="oe-agent-system oe-pubsub-map" role="group" aria-label="주요 에이전트가 이벤트 버스에 독립적으로 연결됩니다. 에이전트 사이의 직접 호출이나 실행 순서를 나타내지 않습니다."><div class="oe-pubsub-top">${agentPort("수집", "Huginn", "변경·상관관계 발행")}${agentPort("맥락", "Muninn", "스냅샷·전문가 근거")}${agentPort("판단", "Forseti", "필수 근거를 모아 판단")}</div>
        <div class="oe-pubsub-bus" data-diagram-bus><strong>이벤트 버스</strong><span>스키마 검증된 게시·구독 / pub/sub</span></div>
        <div class="oe-pubsub-bottom">${agentPort("사람 승인", "Var", "필요한 승인 검증")}${agentPort("실행", "Thor", "적격 작업만 실행")}${agentPort("독립 관측", "Heimdall", "실제 효과 확인")}${agentPort("감사", "Saga", "근거·행동 계보 기록")}</div></div>`,
      takeaway: "배치는 실행 순서가 아닙니다. 직접 호출·공유 가변 상태·자기 승인 없이, 승인·실행·관측의 책임을 분리합니다.",
      evidence: [s.agentLoop, s.constitution],
    }),
    slide({
      state: "BOUNDARY", chapter: "31 / MEANING IS NOT PERMISSION", layout: "authority-wall",
      title: "정확한 의미가 실행 권한을 만들지는 않습니다",
      lead: "의미 검증 이후에도 정책·위험·필요한 사람 승인과 실행 안전장치가 별도로 적용됩니다.",
      body: `<div class="oe-split oe-narrow-left"><blockquote class="oe-statement"><small>넘을 수 없는 경계</small><strong>의미<br><em>≠</em><br>권한</strong></blockquote>
        <div class="oe-stack">${entry("정책과 위험", "이 행동이 지금 적격한가?", "허용 행동·영향 범위·복구 가능성을 검토합니다.")}${entry("사람 승인", "필요한 승인이 유효한가?", "역할·정족수·만료를 검증하며 실행 주체와 분리합니다.")}${entry("실행", "일곱 안전장치를 충족하는가?", "중지 조건·검증된 복구·영향 범위·성공한 dry-run·대상 잠금·멱등 키·2단계 감사")}</div></div>`,
      takeaway: "Thor 에이전트만 적격 작업을 실행합니다. 명령 수락은 성공이 아니며 Heimdall 에이전트의 독립 효과 관측이 필요합니다.",
      evidence: [s.constitution, s.platform, s.action],
    }),
    slide({
      state: "CURRENT", chapter: "32 / ACTION AND EFFECT", layout: "effect-lifecycle",
      title: "선택, 실행 시도, 실제 효과를 따로 기록합니다",
      lead: "결정을 내린 것과 명령을 보낸 것, 원하는 효과를 확인한 것은 서로 다른 사실입니다.",
      body: `${flow([["판단 / Forseti", "선택한 대안", "DecisionCase가<br>ActionOption을 검토"], ["실행 / Thor", "실행 시도", "적격 MutationPlan에 따라<br>ActionRun을 기록"], ["관측 / Heimdall", "실제 효과", "ExpectedEffect와<br>ObservedOutcome을 비교"]])}
        <div class="oe-effect-records"><span><code>ActionOption</code> expects <code>ExpectedEffect</code></span><span><code>ActionRun</code> resulted_in <code>ObservedOutcome</code></span></div>`,
      takeaway: "실행 실패·효과 불일치·관측 불가를 성공으로 합치지 않습니다. 복구 제안도 다시 정책과 승인 경로를 거칩니다.",
      evidence: [s.ontology, s.platform, s.action],
    }),
    slide({
      state: "CURRENT", chapter: "33 / INDEPENDENT VERIFICATION", layout: "reconciliation-loop",
      title: "효과 확인에는 성공 외의 상태도 필요합니다",
      lead: "실행기와 독립된 권위 있는 관측자가 기대 효과를 비교합니다. 근거가 부족한 상태는 종료와 구분합니다.",
      body: `<div class="oe-reconciliation-split"><div class="oe-closed-outcomes"><small>비교를 마감하는 세 상태</small><ol><li data-result-state="MATCHED" data-closure="terminal"><div><code>MATCHED</code><strong>기대 범위 확인</strong></div><p>효과 확인과<br>종료 근거 기록</p></li><li data-result-state="MISMATCHED" data-closure="terminal"><div><code>MISMATCHED</code><strong>기대와 실제 불일치</strong></div><p>복구 검토 제안<br>자체 실행 권한 없음</p></li><li data-result-state="TIMED_OUT" data-closure="terminal"><div><code>TIMED_OUT</code><strong>관측 창 종료</strong></div><p>성공 주장 없이<br>복구 검토</p></li></ol></div>
        <aside class="oe-open-outcome" data-result-state="UNSCORABLE" data-closure="pending"><small>관측 근거 부족 / 비종료</small><strong>판단 보류</strong><code>UNSCORABLE</code><p>현재 시도만 기록하고,<br>새 인증 관측을 기다립니다.</p><span>새 관측으로 재평가 가능</span></aside></div>`,
      takeaway: "API·브로커 수락은 효과 증거가 아닙니다. 복구 요청은 제안일 뿐, 다음 실행을 자동 승인하지 않습니다.",
      evidence: [s.platform, s.constitution],
    }),
    slide({
      state: "ILLUSTRATIVE", chapter: "34 / CHANGE SAFETY", layout: "scenario-change",
      title: "변경의 영향은 서비스의 관계를 따라 읽습니다",
      lead: "예시: 결제 워크로드의 데이터베이스 등급 변경. 무엇이 영향을 받으며 어떤 목표를 지켜야 할까요?",
      body: `<div class="oe-change-graph" role="img" aria-label="서비스는 워크로드로 구현되고, 워크로드는 데이터베이스에 의존합니다"><div class="oe-relation-node"><small>비즈니스 범위</small><strong>BusinessService</strong></div><div class="oe-labeled-edge"><span>implemented_by</span><i class="oe-edge" aria-hidden="true"></i></div><div class="oe-relation-node"><small>운영 단위</small><strong>Workload</strong></div><div class="oe-labeled-edge"><span>depends_on</span><i class="oe-edge" aria-hidden="true"></i></div><div class="oe-relation-node"><small>변경 대상 예시</small><strong>Database</strong></div></div>
        <div class="oe-three">${entry("목표", "무엇을 보호할까?", "SLO·복구 목표·허용 변경 창")}${entry("근거", "지금도 유효한가?", "현재 토폴로지·변경 리비전·백업 증적")}${entry("안전", "실패하면 되돌릴 수 있나?", "복구 계획·성공한 dry-run·필요한 승인")}</div>`,
      takeaway: "정확한 변경과 근거를 DecisionCase에 고정합니다. 오래된 근거나 실패한 dry-run이 있으면 실행하지 않습니다.",
      evidence: [s.agentLoop, s.ontology, s.action],
    }),
    slide({
      state: "ILLUSTRATIVE", chapter: "35 / INCIDENT ANALYSIS", layout: "scenario-incident",
      title: "같은 시간의 이상이 같은 원인은 아닙니다",
      lead: "예시: 배포 뒤 API 지연과 DB throttle이 나타났습니다. 시간 순서는 후보를 좁힐 뿐 원인을 확정하지 않습니다.",
      body: `<ol class="oe-incident-timeline"><li><time>10:01</time><strong>배포</strong></li><li><time>10:04</time><strong>API 지연</strong></li><li><time>10:05</time><strong>DB throttle</strong></li><li><time>10:09</time><strong>추가 관측</strong></li></ol>
        ${table(["원인 후보", "가설을 구분할 관측"], [
          ["H1 / 배포 회귀", "같은 부하에서 이전·현재 리비전의 지연 차이"],
          ["H2 / DB 용량 제한", "포화·할당량 지표와 throttle의 유효 시간"],
          ["H3 / 저장소 지연", "Storage 관측과 요청 trace의 동일 구간"],
        ])}`,
      takeaway: "Heimdall 에이전트의 근거로 Forseti 에이전트가 가설을 비교합니다. 구분 근거가 부족하거나 충돌하면 원인은 unknown입니다.",
      evidence: [s.ontology, s.platform, s.constitution],
    }),
    slide({
      state: "ILLUSTRATIVE", chapter: "36 / COST GOVERNANCE", layout: "scenario-cost",
      title: "절감과 SLO 보호를 같은 결정에서 비교합니다",
      lead: "예시: 저사용 VM을 한 단계 줄이는 선택. 비용 외에 용량 여유와 복구 가능성도 살펴야 합니다.",
      body: `<div class="oe-cost-options"><article><small>OPTION A</small><strong>현재 크기 유지</strong><p>현재 비용과 용량 여유를<br>무조치 기준선으로 보존</p></article><article><small>OPTION B</small><strong>한 단계 축소</strong><p>절감을 기대할 수 있지만<br>용량 여유는 줄어들 수 있음</p></article></div>
        <div class="oe-three oe-cost-criteria">${entry("비용 목표", "절감이 실제로 생기는가", "CostObjective와 관측 비용 비교")}${entry("서비스 목표", "SLO를 계속 지키는가", "같은 부하·관측 구간에서 확인")}${entry("복구 목표", "문제가 생기면 복구 가능한가", "검증된 복구와 제한된 영향 범위")}</div>`,
      takeaway: "Njord·Freyr 에이전트의 비용·용량 근거로 검토합니다. 먼저 관찰 모드에서 제안하며 목표 충돌이나 근거 부족이면 보류합니다.",
      evidence: [s.ontology, s.constitution, s.action],
    }),
    slide({
      state: "BOUNDARY", chapter: "37 / LEARNING WITHOUT SELF-PROMOTION", layout: "learning-flywheel",
      title: "학습은 제안을 만들고, 검토가 채택을 결정합니다",
      lead: "문서와 운영 결과를 읽었다고 활성 온톨로지나 실행 권한이 바로 바뀌지는 않습니다.",
      body: `<div class="oe-learning-paths"><div><small>문서에서 의미 추출</small>${flow([["입력", "문서", "객체·관계·속성 후보"], ["제안", "의미 변경안", "OntologyChangeProposal"], ["별도 검토", "OntologyRelease", "출처·충돌·호환성 확인"]])}</div><div><small>봉인된 운영 사례에서 학습</small>${flow([["입력", "운영 사례군", "성공·실패·보류·복구"], ["제안", "비활성 규칙", "RuleCandidate"], ["별도 검토", "Rule catalog", "재생·관찰 모드 근거 확인"]])}</div></div>`,
      takeaway: "Norns 에이전트의 학습 제안과 Mimir 에이전트의 규칙 검토도 실행 승격과 다릅니다. 학습 결과는 실행 권한을 자동으로 높이지 않습니다.",
      evidence: [s.distillation, s.learning, s.constitution],
    }),
    slide({
      state: "GAP", chapter: "38 / IMPLEMENTATION AND EVIDENCE", layout: "status-roadmap",
      title: "구현과 운영 입증은 서로 다른 단계입니다",
      lead: "현재 설계 기록을 읽을 때도 코드 존재, 검증 범위, 운영 증적을 따로 확인해야 합니다.",
      body: table(["근거 수준", "현재 범위와 남은 확인", "뜻하지 않는 것"], [
        ["구현된 기반", "정확한 릴리스·타입 계약·bounded query", "모든 대상과 경로의 운영 입증"],
        ["진행 중인 검증", "공급자 바인딩·이력·효과 조정의 종단 근거", "일부 테스트 통과가 전체 완료"],
        ["별도 설계·전달 범위", "행동 지식 resolver·저장소·현재 운영 영수증", "설계 문서만으로 기능 사용 가능"],
      ]) + `<div class="oe-inline-note"><strong>배포 판단에는 정확한 리비전의 운영 근거가 필요합니다.</strong><p>성공뿐 아니라 보류·실패·복구 시나리오까지 확인합니다.</p></div>`,
      takeaway: "부분 구현이나 제한된 검증을 전체 플랫폼의 프로덕션 완료로 표현하지 않습니다. 최신 상태는 각 소유 문서와 증적으로 확인합니다.",
      evidence: [s.platform, s.structural, s.behavior],
    }),
    slide({
      state: "DECISION", chapter: "39 / START WITH ONE QUESTION", layout: "adoption-checklist",
      title: "한 가지 질문을 끝까지 검증하는 것부터",
      lead: "범위를 작게 정하고, 같은 의미와 근거로 답을 재생할 수 있는지 확인한 뒤 확장하세요.",
      body: `<div class="oe-split"><blockquote class="oe-statement"><small>첫 질문의 예시</small><strong>이 변경이<br>어떤 서비스 목표에<br>영향을 주는가?</strong></blockquote><ol class="oe-adoption-steps"><li><b>01</b><div><strong>범위를 합의합니다</strong><p>서비스 책임자와 정확한 대상·관계·출처를 정합니다.</p></div></li><li><b>02</b><div><strong>근거를 고정합니다</strong><p>리비전·cutoff·완전성과 허용할 unknown을 남깁니다.</p></div></li><li><b>03</b><div><strong>재생으로 확인합니다</strong><p>예상 답과 실제 근거를 비교하고 거짓 권한 주장이 없는지 봅니다.</p></div></li></ol></div>`,
      takeaway: "근거가 충분하면 다음 질문을 관찰 모드로 넓힙니다. 부족하면 보완하고, 안전 경계 위반이 있으면 확장을 멈춥니다.",
      evidence: [s.ontology, s.platform, s.constitution],
    }),
  ];
}
