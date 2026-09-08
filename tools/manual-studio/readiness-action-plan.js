/** Chapter 5: turn an assessment into owned evidence work, never automatic authority. */
import { entry, record, slide } from "./readiness-slide-kit.js";
import { agendaRing, icon } from "./readiness-diagrams.js";

export const workshopAgenda = [
  { minutes: 15, activity: "업무와 범위 합의", output: "사용자, 목표, 제외할 일을 한 문장으로 확정" },
  { minutes: 20, activity: "보유 근거 확인", output: "출처·리비전·시간·접근 조건을 대조" },
  { minutes: 25, activity: "역량별 판정", output: "현재 수준과 신뢰도, 미평가 항목을 구분" },
  { minutes: 20, activity: "격차와 책임 배정", output: "종료 조건, 담당자, 의존성과 검토일 합의" },
  { minutes: 10, activity: "다음 결정 기록", output: "지금 가능한 진단과 보류할 범위를 구분" },
];

/** Build owned next steps; the displayed assessment cannot approve any operation. */
export function buildReadinessActionPlan() {
  return [
    slide({
      id: "gap-register", chapter: 5, visual: "gaps", state: "EXAMPLE",
      title: "격차마다 책임자와 관측 가능한 종료 조건을 정합니다",
      lead: "예시의 여섯 개 미확인과 모델 사용 조건을 같은 개선 목록에서 추적합니다. 시점은 합의할 제안입니다.",
      body: `<div class="rm-closure-lanes"><header><span>해결할 격차</span><span>담당과 제안 시점</span><span>완료를 확인할 근거</span></header>${[
        ["context", "미매핑 3개", "서비스·플랫폼", "2주차", "검토된 대상·관계와 원본 리비전"],
        ["shield", "접근 불가 2개", "데이터·접근 관리", "2주차", "허용 여부 검토와 서버 측 실효 접근 확인"],
        ["clock", "오래된 근거 1개", "수집·플랫폼", "2주차", "새 관측과 최신성 검사 결과"],
        ["document", "모델 사용 근거 없음", "데이터·보안", "3주차", "목적·분류·지역·보존·전송 조건의 승인"],
      ].map(([symbol, gap, owner, week, exit]) => `<article><div>${icon(symbol)}<h3>${gap}</h3></div><div><strong>${owner}</strong><span>${week} / 제안</span></div><p>${exit}</p></article>`).join("")}</div><p class="rm-full-note">같은 20개 범위를 다시 평가할 때까지 미완료를 유지합니다. 제출된 문서만으로 완료 처리하지 않습니다.</p>`,
      takeaway: "자료 제출이 아니라 검증 결과로 격차를 닫습니다. 미완료 항목에는 다음 책임과 날짜를 남깁니다.",
      evidence: ["constitution", "governance", "ontology"],
    }),
    slide({
      id: "three-boundaries", chapter: 5, visual: "boundaries", state: "STATUS",
      title: "제품 구현, 환경 준비, 행동 승인은 서로 다릅니다",
      lead: "설계 문서와 테스트가 있어도 해당 배포의 데이터 사용, 실운영 품질, 실행 권한이 입증된 것은 아닙니다.",
      body: `<div class="rm-boundary-columns"><section>${icon("document")}${entry("공통 구현", "코드와 계약이 있음", "근거 검증과 입력 최소화 계약은 구현되어 있습니다. 실운영 성과 전체를 입증하지는 않습니다.")}</section><section>${icon("data")}${entry("환경별 준비", "운영 근거가 필요함", "개인정보 승인과 보존 정책은 배포별로 필요합니다. 완전한 실운영 비교 집단의 근거도 남아 있습니다.")}</section><section>${icon("shield")}${entry("행동 승인", "별도 통제를 거침", "읽기는 접근·범위·근거·감사를 확인합니다. 상태 변경은 정책상 권한과 안전장치를 별도로 확인합니다.")}</section></div>
        <div class="rm-safeguard-section"><strong>상태 변경 전에 필요한 일곱 안전장치</strong><ol class="rm-safeguards"><li>중지 조건</li><li>검증된 복구</li><li>영향 범위 제한</li><li>성공한 가상 실행</li><li>논리 대상 잠금</li><li>안정된 중복 억제 키</li><li>실행 전 의도·종료 감사</li></ol></div>`,
      takeaway: "실행 접수는 성공이 아닙니다. 기대 효과는 실행기와 독립된 관측자가 확인해야 합니다.",
      evidence: ["constitution", "governance", "metrics"],
    }),
    slide({
      id: "thirty-days", chapter: 5, visual: "roadmap", state: "PROPOSAL",
      title: "첫 30일에는 다음 결정을 위한 근거를 만듭니다",
      lead: "완료를 보장하는 일정이 아니라 검토 지점의 예시입니다. 통과하지 못한 조건은 다음 단계로 넘기지 않습니다.",
      body: `<div class="rm-workstream-calendar"><header><span>책임이 있는 작업 흐름</span>${[1, 2, 3, 4].map(week => `<strong>${week}주</strong>`).join("")}</header>${[
        ["범위와 기준선", "서비스 책임자", "목표·제외 범위\n평가 책임 합의"],
        ["데이터와 맥락", "데이터·플랫폼", "전체 범위의\n결손·접근 진단"],
        ["AI와 운영 평가", "AI 평가·운영", "고정 사례\n품질·보류 비교"],
        ["별도 검토", "서비스·보안", "미완료 격차\n다음 결정 기록"],
      ].map(([title, owner, output], index) => `<div class="rm-calendar-row"><div><h3>${title}</h3><small>${owner}</small></div>${[0, 1, 2, 3].map(week => `<div class="rm-calendar-cell${index === week ? " is-planned" : ""}" data-rm-week="${week + 1}"${index === week ? ` data-rm-checkpoint="${index + 1}"` : ""}>${index === week ? `<p>${output}</p>` : '<i aria-hidden="true"></i>'}</div>`).join("")}</div>`).join("")}</div><p class="rm-calendar-caption">색 면은 제안된 작업 주차이며 완료율이 아닙니다. 다음 단계는 선행 근거 확인 뒤 검토합니다.</p>`,
      takeaway: "날짜가 지났다는 이유로 승격하지 않습니다. 근거가 부족하면 범위를 줄이거나 보류합니다.",
      evidence: ["constitution", "metrics", "governance"],
    }),
    slide({
      id: "workshop", chapter: 5, visual: "workshop", state: "PROPOSAL",
      title: "90분 워크숍은 등급보다 합의할 산출물에 집중합니다",
      lead: "서비스, 데이터, AI 평가, 보안 책임자가 같은 근거를 봅니다. 자료가 없으면 미평가로 남깁니다.",
      body: `<aside class="rm-workshop-clock">${agendaRing(workshopAgenda)}<h3>회의 전 준비</h3><p>실제 질문과 절차, 출처 목록,<br>품질 기록, 사용 조건과 담당자</p></aside>
        <ol class="rm-agenda">${workshopAgenda.map((item, index) => `<li data-rm-agenda="${index + 1}"><span>${item.minutes}분</span><div><h3>${item.activity}</h3><p>${item.output}</p></div></li>`).join("")}</ol>`,
      takeaway: "회의 결과는 업무 정의, 근거 목록, 역량별 판정, 격차 책임자, 다음 검토일로 남깁니다.",
      evidence: ["constitution", "governance"],
    }),
    slide({
      id: "next-decision", chapter: 5, visual: "next", state: "PROPOSAL",
      title: "오늘 정할 것은 모델이 아니라 첫 검증의 범위입니다",
      lead: "목표는 높은 점수를 받는 일이 아닙니다. 어떤 근거를 누가 만들고 다음에 무엇을 판단할지 합의하는 일입니다.",
      body: `<section class="rm-final-brief"><small>${icon("target")}NEXT DECISION / 검토 요청</small><h3>읽기 파일럿의 범위와<br>보완 계획을 검토하세요.</h3>
        ${record([["한 가지 업무", "변경 영향 검토처럼 반복 가능한 판단"], ["책임과 근거", "서비스·데이터·평가·보안 담당자"], ["다음 검토", "기준선, 차단 격차, 종료 조건과 날짜"]])}</section>
        <section class="rm-next-outcomes"><div>${icon("check")}${entry("검토 진행", "근거가 갖춰진 범위부터", "기존 권한과 승인된 데이터 사용 조건 안에서 관찰 모드 계획을 검토합니다.")}</div><div>${icon("cycle")}${entry("보완 후 재검토", "차단 격차에 먼저 투자", "자료와 책임을 보완하고 같은 평가 범위로 돌아옵니다.")}</div><div>${icon("target")}${entry("범위 재정의", "맞지 않는 업무는 바꿉니다", "가치가 낮거나 검증할 수 없다면 다른 시작점을 선택합니다.")}</div></section>`,
      takeaway: "준비도는 다음 행동을 선명하게 하고, 성숙도는 그 판단을 반복할 능력을 키웁니다.",
      evidence: ["constitution", "metrics"],
    }),
  ];
}
