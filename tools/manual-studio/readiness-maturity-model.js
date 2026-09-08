/** Chapter 4: proposed qualitative rubric, not an automated score or authority registry. */
import { slide, table } from "./readiness-slide-kit.js";
import { icon, maturityPosition } from "./readiness-diagrams.js";

export const maturityLevels = [
  ["M1", "개별 대응", "사람의 경험에 의존", "관측한 업무 사례"],
  ["M2", "정의됨", "담당자와 기준을 합의", "문서와 확인 기록"],
  ["M3", "반복 가능", "같은 절차를 반복", "반복 수행 기록"],
  ["M4", "근거로 검증", "합의한 품질을 입증", "측정과 별도 검토"],
  ["M5", "지속 개선", "변화를 감지해 재검증", "회귀·개선·복귀 이력"],
];

export const illustrativeProfile = [
  { dimension: "가치와 범위", level: "M2", evidence: "업무 정의와 검토자가 문서에 있음", next: "동일 업무의 현재 기준선 측정" },
  { dimension: "데이터 품질과 관리", level: "M3", evidence: "반복 점검에서 20개 모두의 상태를 기록", next: "미매핑·접근 불가·지연 보완" },
  { dimension: "의미와 서비스 맥락", level: "M2", evidence: "매핑 기준은 있으나 여섯 개가 미확인", next: "전체 범위의 관계와 출처 확인" },
  { dimension: "AI 평가와 변경 관리", level: "M2", evidence: "평가 기준을 합의했고 비교 결과는 없음", next: "고정 사례로 보류·인용까지 평가" },
  { dimension: "사람과 운영 절차", level: "M3", evidence: "검토와 인계 절차의 반복 기록이 있음", next: "예외 대응과 검토 부담 측정" },
  { dimension: "통제와 안전한 변경", level: null, evidence: "모델 사용 승인 근거를 제시하지 못함", next: "권한과 데이터 사용 조건의 별도 검토" },
];

/** Explain the proposed rubric and its explicitly fictional evidence-based assessment. */
export function buildReadinessMaturityModel() {
  return [
    slide({
      id: "maturity-ladder", chapter: 4, visual: "maturity", state: "PROPOSAL",
      title: "성숙도는 자동화의 양이 아니라 반복 가능한 역량입니다",
      lead: "M1-M5는 이 워크숍의 제안 모델입니다. 공인 등급이나 FDAI의 실행 권한 단계가 아닙니다.",
      body: `<ol class="rm-maturity-steps">${maturityLevels.map(([code, title, meaning, evidence], index) => `<li style="--step:${index}"><div class="rm-maturity-stage"><small>${code}</small>${icon(["people", "document", "cycle", "check", "context"][index])}</div><h3>${title}</h3><p>${meaning}</p><span>${evidence}</span></li>`).join("")}</ol>
        <div class="rm-maturity-boundary"><strong>먼저 합의할 기준</strong><p>업무 범위, 측정 구간, 필요한 표본, 허용 오류, 근거의 유효 기간, 검토 책임자</p></div>`,
      takeaway: "근거가 없으면 낮은 등급이 아니라 미평가입니다. M등급은 T0-T2나 실행 모드와 다릅니다.",
      evidence: ["constitution", "metrics"],
    }),
    slide({
      id: "data-rubric", chapter: 4, visual: "rubric", state: "PROPOSAL",
      title: "데이터 쪽 성숙도는 문서에서 반복 검증으로 자랍니다",
      lead: "중간 세 단계의 판단 예시입니다. 필요한 기간과 표본은 선택한 업무의 위험과 변동성에 맞춰 합의합니다.",
      body: table(["역량", "M2 / 정의됨", "M3 / 반복 가능", "M4 / 근거로 검증"], [
        ["가치와 범위", "목표·책임자·제외 범위가 있음", "같은 업무의 기준선을 반복 수집", "같은 단위로 가치와 부작용을 검토"],
        ["데이터 품질과 관리", "출처 계약·품질 기준·소유자 지정", "동일 범위의 결손과 지연을 반복 기록", "합의한 품질과 삭제·접근 절차 입증"],
        ["의미와 서비스 맥락", "대상·관계·목표의 의미 합의", "매핑 변경과 미분류를 일관되게 관리", "질문별 관계·시간·출처를 별도로 검증"],
      ], "rm-rubric-table") + `<p class="rm-full-note">M5에서는 새로운 데이터와 관계 변경을 감지하고, 재평가·개선·복귀 기록을 유지합니다.</p>`,
      takeaway: "같은 문서 한 장을 모든 역량의 근거로 재사용하지 말고, 평가 항목과 직접 연결합니다.",
      evidence: ["governance", "ontology", "metrics"],
    }),
    slide({
      id: "operating-rubric", chapter: 4, visual: "rubric", state: "PROPOSAL",
      title: "AI와 운영의 성숙도는 평가와 책임이 함께 자랍니다",
      lead: "모델 사용 경험보다 오류를 발견하고, 사람이 이어받고, 변경을 검토하는 능력을 봅니다.",
      body: table(["역량", "M2 / 정의됨", "M3 / 반복 가능", "M4 / 근거로 검증"], [
        ["AI 평가와 변경 관리", "기대 답변·보류·실패 기준을 정의", "고정 사례와 버전으로 회귀 평가", "독립 검토로 품질·비용·지연 입증"],
        ["사람과 운영 절차", "업무·예외·대체 담당자 지정", "검토·인계·사고 대응을 반복", "부하와 인계 누락을 측정해 개선"],
        ["통제와 안전한 변경", "데이터 사용과 권한 경계를 정의", "접근·승인·감사·복구를 점검", "해당 환경의 통제와 효과 관측 입증"],
      ], "rm-rubric-table") + `<div class="rm-role-example"><strong>역할 배정 예시</strong><p>모델 버전 기록 누락은 AI 평가 담당자가 보완하고, 운영 책임자가 같은 사례의 재현 결과를 검토합니다.</p></div>`,
      takeaway: "문서화, 반복 수행, 검증은 다른 상태입니다. 성숙도 등급이 승인을 대신하지 않습니다.",
      evidence: ["llm", "governance", "constitution"],
    }),
    slide({
      id: "assessment-confidence", chapter: 4, visual: "confidence", state: "PROPOSAL",
      title: "현재 수준과 그 판정의 신뢰도를 함께 기록합니다",
      lead: "자기평가와 관측 근거를 구분합니다. 이 구분은 진단의 신뢰도이지 실행 적격성 판정이 아닙니다.",
      body: `<div class="rm-confidence-list">${[
        ["people", "설명만 있음", "인터뷰와 자기평가", "검증 전 가설로 두고 실제 사례를 요청합니다."],
        ["document", "자료 확인", "소유자·리비전이 있는 기록", "문서가 현재 범위에 맞는지 대조합니다."],
        ["cycle", "반복 확인", "실행 기록과 재현 결과", "담당자가 달라도 같은 절차가 유지되는지 봅니다."],
        ["check", "별도 검토", "측정 결과와 독립 확인", "기간·표본·실패·제외 사유를 함께 검토합니다."],
      ].map(([symbol, label, title, detail]) => `<article class="rm-entry"><small>${icon(symbol)}${label}</small><h3>${title}</h3><p>${detail}</p></article>`).join("")}</div>
        <aside class="rm-unknown"><h3>미평가를 남기는 방법</h3><p><strong>자료 없음</strong><br>근거 요청과 책임자 기록</p><p><strong>자료 충돌</strong><br>서로 다른 주장과 재검토 이유 보존</p><p><strong>해당 없음</strong><br>범위 사유와 검토자 확인 필요</p></aside>`,
      takeaway: "점수를 먼저 정하고 근거를 끼워 맞추지 않습니다. 오래된 판정은 새 근거로 재검토합니다.",
      evidence: ["constitution", "metrics"],
    }),
    slide({
      id: "profile", chapter: 4, visual: "profile", state: "EXAMPLE",
      title: "평균 점수 대신, 업무를 막는 격차를 읽습니다",
      lead: "예시 팀의 워크숍 판정입니다. 앞의 70% 관계 확인 비율을 성숙도 점수로 환산한 결과가 아닙니다.",
      body: `<div class="rm-profile-caption"><span>● 현재 판정 / 빈 점은 다른 범주</span><span>M1-M5는 서열 범주이며 간격은 수치 차이가 아닙니다.</span></div>` + table(["역량", '<span class="rm-category-scale">' + [1, 2, 3, 4, 5].map(value => `<b>M${value}</b>`).join("") + '</span>', "제시된 근거 / 예시"], illustrativeProfile.map(item => [
        item.dimension,
        maturityPosition(item.level),
        item.evidence,
      ]), "rm-profile-table"),
      takeaway: "반복 점검을 잘해도 관계 품질은 부족할 수 있습니다. 미평가 통제를 평균으로 지우지 않습니다.",
      evidence: ["constitution", "governance"],
    }),
    slide({
      id: "decision-memo", chapter: 4, visual: "memo", state: "EXAMPLE",
      title: "진단의 끝에는 범위와 이유가 있는 검토 의견을 남깁니다",
      lead: "예시 결론: 전체 영향 브리핑의 파일럿은 보류하고, 허용된 데이터 품질 진단을 먼저 제안합니다.",
      body: `<aside class="rm-memo-verdict">${icon("hold")}<small>ASSESSMENT MEMO / 예시</small><h3>파일럿 보류 의견</h3><p>20개 중 여섯 개의 관계가 미확인이고 모델 사용 승인 근거가 없습니다.</p><span>최종 검토: 서비스 책임자<br>데이터 사용: 데이터·보안 책임자</span></aside>
        <div class="rm-decision-branches"><article class="rm-investigate">${icon("search")}<div><small>지금 제안할 범위</small><h3>허용된 근거 조사</h3><p>기존 읽기 권한 안에서 미매핑 3개,<br>접근 불가 2개, 지연 1개를 진단합니다.</p></div></article><article class="rm-defer">${icon("hold")}<div><small>보류할 범위</small><h3>전체 영향과 행동 결정</h3><p>모델 전송, 전체 영향 확정, 변경 승인과 실행</p></div></article><div class="rm-revisit">${icon("cycle")}<p>보완 근거가 모인 뒤 같은 20개 범위를 재평가</p></div></div>`,
      takeaway: "이 문서는 검토 의견입니다. 14개 확인이나 높은 M등급이 새 권한을 부여하지 않습니다.",
      evidence: ["constitution", "governance"],
    }),
  ];
}
