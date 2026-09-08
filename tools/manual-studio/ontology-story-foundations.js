import { slide, entry, table, sources as s, references as r } from "./ontology-slide-kit.js";

/** Slides 2-14: why shared meaning matters and how the idea developed. */
export function foundationSlides() {
  return [
    slide({
      state: "PROBLEM", chapter: "01 / WHY NOW", layout: "tension",
      title: "유창한 답변과 실행 가능한 판단은 다릅니다",
      lead: "LLM은 가능한 답을 만듭니다. 현재 대상과 상태, 실행 권한은 따로 확인해야 합니다.",
      body: `<div class="oe-split">
        <blockquote class="oe-statement"><small>운영자의 질문</small><strong>이 서비스를<br>재시작해도 될까?</strong><p>답변의 설득력만으로는<br>지금 실행할 수 있는지 알 수 없습니다.</p></blockquote>
        <div class="oe-stack">${entry("LLM이 제안하는 것", "가능한 절차와 이유", "문맥에서 관련 패턴을 찾아 설명과 후보를 만듭니다.")}${entry("운영이 확인하는 것", "지금, 이 대상에서 가능한가", "정확한 대상·최신 관측·정책·복구·필요한 승인을 확인합니다.")}</div>
      </div>`,
      takeaway: "모델의 자신감은 실행 권한이 아닙니다. 확인할 수 없는 항목은 모르는 것으로 남깁니다.",
      evidence: [s.llm, s.constitution],
    }),
    slide({
      state: "ILLUSTRATIVE", chapter: "02 / ONE WORD, MANY MEANINGS", layout: "fracture",
      title: "같은 service, 서로 다른 세 가지 대상",
      lead: "예시 질문: 결제 service의 장애 원인을 알려줘. 먼저 어떤 대상을 뜻하는지 맞춰야 합니다.",
        body: `<div class="oe-meaning-map" role="group" aria-label="service라는 한 표현에서 세 가지 해석이 갈라집니다. 연결은 선택 가능성을 뜻하며 객체 사이의 관계가 아닙니다.">
          <div class="oe-meaning-source" data-meaning-node="term"><small>표현은 하나</small><strong>service</strong><p>확인 전에는<br>대상을 선택하지 않습니다.</p></div>
          <div class="oe-meaning-links" aria-hidden="true"><i class="oe-meaning-trunk"></i><i class="oe-meaning-branch" data-branch-to="business"></i><i class="oe-meaning-branch" data-branch-to="runtime"></i><i class="oe-meaning-branch" data-branch-to="provider"></i></div>
          <div class="oe-meaning-targets"><article data-meaning-node="business"><small>01 / 비즈니스</small><strong>BusinessService</strong><p>서비스 책임과 SLO가<br>연결된 비즈니스 단위</p></article><article data-meaning-node="runtime"><small>02 / 런타임</small><strong>Kubernetes Service</strong><p>Pod로 트래픽을 보내는<br>네트워크 객체</p></article><article data-meaning-node="provider"><small>03 / 공급자 용어</small><strong>Cloud service</strong><p>클라우드 제품군이나<br>관리 기능의 일반적인 명칭</p></article></div>
        </div>`,
      takeaway: "이름이 같다고 같은 타입은 아닙니다. 미해결 용어를 보존하고 확인 가능한 후보를 제시합니다.",
      evidence: [s.ontology, s.metamodel],
    }),
    slide({
      state: "PROBLEM", chapter: "03 / FAILURE MODES", layout: "failure-matrix",
      title: "의미의 빈틈은 여섯 가지 오류로 이어집니다",
      lead: "온톨로지 없이 LLM만 사용하면 대상·관계·시간·근거·권한의 오류가 한 판단 안에서 결합할 수 있습니다.",
      body: `<div class="oe-six">${entry("01", "의미 모호성", "service가 어떤 종류의 대상인지 정하지 못합니다.")}${entry("02", "정체성 혼합", "비슷한 이름의 다른 리소스를 같은 것으로 묶습니다.")}${entry("03", "관계 추정", "가까이 있다는 이유로 의존 관계를 가정합니다.")}${entry("04", "시간 소실", "과거 문서의 상태를 현재 사실로 사용합니다.")}${entry("05", "근거 과장", "부분 조회를 전체 범위를 확인한 결과로 취급합니다.")}${entry("06", "권한 오인", "작업 요청을 실행 승인으로 받아들입니다.")}</div>`,
      takeaway: "검색 결과가 많아져도 이 빈틈은 저절로 닫히지 않습니다. 서로 다른 검증 경계가 필요합니다.",
      evidence: [s.constitution, s.ontology, s.governance],
    }),
    slide({
      state: "BOUNDARY", chapter: "04 / DISTINCT RESPONSIBILITIES", layout: "role-bands",
      title: "생성, 검색, 의미, 권한은 다른 역할입니다",
      lead: "LLM, RAG, 온톨로지, 정책은 경쟁 기술이 아니라 서로 다른 질문에 답하는 계층입니다.",
      body: table(["계층", "답하는 질문", "맡지 않는 역할"], [
        ["LLM", "가능한 해석과 설명은 무엇인가?", "현재 사실이나 실행 승인 보증"],
        ["RAG", "어떤 자료가 이 질문과 관련 있는가?", "문서가 지금도 유효하다는 보증"],
        ["온톨로지", "대상과 관계는 무엇을 뜻하는가?", "관측·판단·승인·실행"],
        ["정책과 근거 검증", "지금 이 판단이 적격한가?", "모델의 추측을 사실로 바꾸기"],
      ]),
      takeaway: "한 계층의 성공이 다음 계층의 성공을 뜻하지 않습니다. 생성·검색·의미·권한을 따로 검증합니다.",
      evidence: [s.llm, s.ontology, s.constitution],
    }),
    slide({
      state: "FOUNDATION", chapter: "05 / FROM DATA TO DECISION", layout: "meaning-ladder",
      title: "데이터를 저장하는 것만으로는 충분하지 않습니다",
      lead: "값, 구조, 의미, 현재 근거, 결정은 각각 다른 책임을 가집니다.",
      body: `<div class="oe-split oe-wide-left"><ol class="oe-ladder">
        <li><b>01</b><strong>Data</strong><span>무엇이 관측되었는가</span></li><li><b>02</b><strong>Schema</strong><span>어떤 필드와 자료형인가</span></li><li class="oe-emphasis"><b>03</b><strong>Ontology</strong><span>그 값과 관계는 무엇을 뜻하는가</span></li><li><b>04</b><strong>Knowledge graph</strong><span>어떤 근거로 연결되었는가</span></li><li><b>05</b><strong>Decision</strong><span>정책과 권한 안에서 무엇을 할 것인가</span></li>
        </ol><aside class="oe-margin"><strong>구조가 맞아도<br>뜻은 다를 수 있습니다.</strong><p>같은 문자열 필드가 표시 이름인지, 안정된 식별자인지 스키마만으로 알 수는 없습니다.</p></aside></div>`,
      takeaway: "온톨로지는 데이터 없이 사실을 만들지 않고, 정책은 온톨로지의 의미를 실행 권한으로 바꾸지 않습니다.",
      evidence: [s.ontology, s.platform],
    }),
    slide({
      state: "HISTORY", chapter: "06 / ARISTOTLE", layout: "aristotle",
      title: "시작은 오래된 질문입니다. 무엇이 존재하는가?",
      lead: "아리스토텔레스는 기원전 4세기에 존재와 범주를 탐구했습니다. ontology라는 용어를 쓰지는 않았습니다.",
      body: `<div class="oe-split"><blockquote class="oe-quote"><small>아리스토텔레스 / 형이상학</small><strong>존재자로서의<br>존재</strong><p>무엇이 존재하며, 어떤 종류로 말할 수 있고,<br>어떤 관계를 맺는가를 묻습니다.</p></blockquote>
        <div class="oe-category-study"><small>전통적으로 번역되는 열 범주</small><div class="oe-category-grid">${["실체", "수량", "성질", "관계", "장소", "시간", "자세", "소유·상태", "작용", "영향받음"].map(word => `<span>${word}</span>`).join("")}</div><p>분류와 관계를 명시하려는 질문은<br>현대의 모델 설계에서도 중요합니다.</p></div></div>`,
      takeaway: "질문의 유사성이지 직접적인 기술 계보는 아닙니다. 고대의 범주론을 현대 컴퓨터 모델과 동일시하지 않습니다.",
      evidence: [s.ontology, r.aristotle, r.logic],
    }),
    slide({
      state: "HISTORY", chapter: "07 / A NAME EMERGES", layout: "history-timeline",
      title: "존재에 대한 질문에 ontologia라는 이름이 붙습니다",
      lead: "고대의 탐구는 근대에 존재 일반을 다루는 학문명으로 체계화됩니다.",
      body: `<ol class="oe-timeline"><li><time>기원전 4세기</time><strong>아리스토텔레스</strong><p>존재·실체·범주를<br>체계적으로 질문</p></li><li><time>중세</time><strong>스콜라 철학</strong><p>본질과 존재,<br>보편자와 개별자 탐구</p></li><li><time>1606</time><strong>Jacob Lorhard</strong><p>ontologia 표제의<br>초기 용례</p></li><li><time>1730</time><strong>Christian Wolff</strong><p>존재 일반을 다루는<br>일반 존재론 체계화</p></li></ol>`,
      takeaway: "주요 순서를 보여주는 개요이며 시간 축척은 아닙니다. 용어의 최초성은 서지 기준에 따라 신중히 다룹니다.",
      evidence: [s.ontology, r.logic],
    }),
    slide({
      state: "HISTORY", chapter: "08 / MAKING ASSUMPTIONS VISIBLE", layout: "logic-bridge",
      title: "형식 언어는 문장 속의 전제를 드러냅니다",
      lead: "자연어를 형식화하면 대상의 범위와 관계 방향, 반례를 따로 검토할 수 있습니다.",
      body: `<div class="oe-logic-pair"><div class="oe-natural"><small>자연어 예시</small><strong>모든 서비스에는<br>책임자가 있다.</strong></div><div class="oe-formal"><small>설명용 논리식</small><code>∀x (Service(x) → ∃y owns(y,x))</code><p>Service의 범위와 owns의 방향을<br>명시적으로 해석해야 합니다.</p></div></div>
        <div class="oe-three oe-questions">${entry("범위", "어떤 Service인가?", "BusinessService와 런타임 객체를 구분")}${entry("관계", "누가 누구를 소유하는가?", "Owner → Service 방향을 선언과 대조")}${entry("반례", "책임자가 없다면?", "사실을 강제하지 않고 미비점을 보고")}</div>`,
      takeaway: "형식은 명확성을 높이지만 사실을 만들지 않습니다. 실제 대상과 책임 관계는 권위 있는 근거가 필요합니다.",
      evidence: [s.metamodel, r.logic],
    }),
    slide({
      state: "HISTORY", chapter: "09 / KNOWLEDGE REPRESENTATION", layout: "kr-evolution",
      title: "AI는 지식을 표현하는 방법을 넓혀 왔습니다",
      lead: "논리, 프레임, 의미망, 설명 논리, 지식 그래프는 개념과 관계를 재사용하려는 여러 접근입니다.",
      body: `<ol class="oe-timeline oe-five"><li><time>1950s-60s</time><strong>기호 AI</strong><p>논리식과 탐색으로<br>문제를 표현</p></li><li><time>1970s</time><strong>프레임·의미망</strong><p>객체·슬롯·관계를<br>구조화</p></li><li><time>1980s</time><strong>전문가 시스템</strong><p>도메인 규칙과<br>지식 기반 활용</p></li><li><time>1990s</time><strong>설명 논리</strong><p>분류·일관성 추론을<br>형식화</p></li><li><time>2000s+</time><strong>지식 그래프</strong><p>웹과 기업 데이터를<br>공통 의미로 연결</p></li></ol>`,
      takeaway: "주요 흐름을 단순화한 연대 개요입니다. 각 접근은 공존하며, 당시 모두 ontology라고 불린 것도 아닙니다.",
      evidence: [s.ontology, r.logic],
    }),
    slide({
      state: "HISTORY", chapter: "10 / GRUBER, 1993", layout: "gruber",
      title: "공유할 개념을 명시적으로 설계합니다",
      lead: "Gruber는 온톨로지를 지식 공유를 위한 설계 산출물로 설명했습니다.",
      body: `<div class="oe-split oe-wide-left"><blockquote class="oe-quote oe-definition-quote"><small>THOMAS R. GRUBER / 1993</small><strong>explicit specification<br>of a conceptualization</strong><p>어떤 개념과 관계를 어떤 목적으로 공유하는지<br>기계가 처리할 수 있도록 명시합니다.</p></blockquote><div class="oe-stack">${entry("01 / 명료성", "뜻이 흔들리지 않게", "같은 용어를 다른 문맥에서도 일관되게 해석")}${entry("02 / 일관성", "서로 모순되지 않게", "선언과 추론을 함께 검토")}${entry("03 / 확장성", "기존 의미를 지키며", "새 개념을 추가할 수 있도록 설계")}</div></div>`,
      takeaway: "온톨로지는 세계 전체의 복제본이 아닙니다. 특정 목적을 위해 함께 사용할 의미를 합의한 모델입니다.",
      evidence: [s.ontology, r.gruber],
    }),
    slide({
      state: "HISTORY", chapter: "11 / SEMANTIC WEB", layout: "semantic-web",
      title: "RDF는 연결을, OWL은 형식 의미를 표현합니다",
      lead: "웹의 공유 식별자와 논리적 제약은 기계가 데이터를 함께 읽는 기반이 되었습니다.",
      body: `<div class="oe-relation-example" role="img" aria-label="RDF triple 예시: Workload A가 Database B에 의존합니다"><div class="oe-relation-node"><small>주어</small><strong>Workload A</strong></div><div class="oe-labeled-edge"><span>depends_on</span><i class="oe-edge" aria-hidden="true"></i></div><div class="oe-relation-node"><small>목적어</small><strong>Database B</strong></div></div>
        <div class="oe-two">${entry("RDF", "주어·술어·목적어", "triple을 통해 식별자와 관계를 그래프로 연결합니다.")}${entry("OWL", "클래스·속성·공리", "논리적 의미와 추론에 필요한 제약을 명시합니다.")}</div>`,
      takeaway: "FDAI는 자체 타입 계약을 사용합니다. 그래프의 의미가 현재 외부 사실이나 승인·실행 권한을 대신하지 않습니다.",
      evidence: [s.structural, r.rdf, r.owl],
    }),
    slide({
      state: "HISTORY", chapter: "12 / THE LLM ERA", layout: "return-loop",
      title: "언어의 유연함에 의미의 엄밀함을 더합니다",
      lead: "LLM 시대의 온톨로지는 생성 능력을 대체하기보다, 후보를 검증할 공통 기준을 제공합니다.",
      body: `<div class="oe-duet"><article><small>기호 기반 지식</small><strong>일관된 의미</strong><p>명시적인 타입과 관계<br>재현 가능한 제약 검증</p><span>합의와 작성에 비용이 듭니다.</span></article><b aria-hidden="true">+</b><article><small>LLM</small><strong>폭넓은 표현</strong><p>다양한 자연어 이해<br>설명과 해석 후보 생성</p><span>현재 사실과 권한을 보장하지 않습니다.</span></article></div>`,
      takeaway: "반복 판단은 규칙으로 먼저 해결합니다. 남은 모호성도 의미·근거·정책·필요한 승인을 거쳐야 합니다.",
      evidence: [s.llm, s.constitution, s.platform],
    }),
    slide({
      state: "FOUNDATION", chapter: "13 / OPERATING ONTOLOGY", layout: "definition-cube",
      title: "운영 온톨로지는 버전이 있는 의미 계약입니다",
      lead: "클라우드 운영 질문에 필요한 객체, 관계, 제약과 그 의미의 버전을 함께 정의합니다.",
      body: `<div class="oe-definition-grid">${entry("WHAT", "Object", "무엇이 존재하는가?<br>서비스·워크로드·리소스의 종류")}${entry("HOW", "Relationship", "어떻게 연결되는가?<br>의존·배치·소유의 방향")}${entry("MEANING", "Constraint", "어떤 구조가 유효한가?<br>타입·단위·끝점의 제약")}${entry("VERSION", "Release", "어떤 의미로 해석했는가?<br>정확한 선언 버전과 digest")}</div>`,
      takeaway: "릴리스는 의미를 고정하고, 관측은 현재 근거를 제공합니다. 행동 자격은 별도의 정책과 승인 경계에서 결정합니다.",
      evidence: [s.ontology, s.metamodel],
    }),
  ];
}
