/** Shared presentation primitives for the FDAI target-architecture review. */
export const sources = {
  architectureGuide: "docs/user-guide/architecture.md",
  constitution: "docs/roadmap/architecture/fdai-constitution.md",
  arb: "docs/roadmap/architecture/architecture-review-board.md",
  appShape: ".github/instructions/app-shape.instructions.md",
  services: "docs/roadmap/architecture/service-decomposition-execution-plan.md",
  pantheon: "docs/roadmap/agents/agent-pantheon.md",
  projectStructure: "docs/roadmap/architecture/project-structure.md",
  ontology: "docs/roadmap/architecture/operating-ontology.md",
  deterministic: "docs/user-guide/concepts/deterministic-first.md",
  execution: "docs/roadmap/decisioning/execution-model.md",
  security: "docs/roadmap/architecture/security-and-identity.md",
  axes: "docs/roadmap/architecture/decisions/0002-independent-runtime-axes.md",
  portability: "docs/roadmap/architecture/csp-neutrality.md",
  deployment: "docs/roadmap/deployment/deployment.md",
  readiness: "docs/roadmap/operations/operational-readiness.md",
  reviewState: "config/architecture-review.yaml",
};

const sourceLabels = {
  architectureGuide: "FDAI Architecture",
  constitution: "FDAI Constitution",
  arb: "Architecture Review Board",
  appShape: "App Shape",
  services: "Service Decomposition",
  pantheon: "Agent Pantheon",
  projectStructure: "Project Structure",
  ontology: "Operating Ontology",
  deterministic: "Deterministic First",
  execution: "Execution Model",
  security: "Security & Identity",
  axes: "ADR-0002",
  portability: "CSP-Neutrality",
  deployment: "Deployment",
  readiness: "Operational Readiness",
  reviewState: "Architecture Review State",
};

export const chapters = [
  "전체 구조",
  "런타임 토폴로지",
  "판단 아키텍처",
  "실행 경계",
  "Azure 배포",
];

const stateLabels = {
  CONDITIONAL: "조건부 설계 승인 요청",
  CONTRACT: "FDAI 설계 기준",
  CURRENT: "현재 구현",
  DECISION: "검토 결정",
  GAP: "프로덕션 전 열린 근거",
  STATUS: "구현과 운영 근거 구분",
  TARGET: "목표 상태",
  VALIDATED: "보존된 검증 근거",
};

/** Render readable source labels while retaining exact repository paths. */
export function evidenceLine(keys) {
  const paths = keys.map((key) => sources[key]);
  const labels = keys.map((key) => sourceLabels[key]);
  return `<small class="ta-source" title="${paths.join(" | ")}">근거: ${labels.join(" / ")}</small>`;
}

/** Build one architecture-review slide with one visual and one review takeaway. */
export function slide({ index, id, chapter, state, title, lead, body, takeaway, evidence, diagramKind = "architecture" }) {
  const number = String(index).padStart(2, "0");
  return {
    eyebrow: `${number} / ${chapters[chapter - 1]}`,
    title,
    lead,
    layout: `briefing-target-${id} deck-target-architecture`,
    architecture: { id, chapter, state, diagramKind, sources: evidence.map((key) => sources[key]) },
    content: `
      <div class="ta-meta">
        <span class="ta-state" data-state="${state}">${stateLabels[state]}</span>
        <span class="ta-progress" aria-label="5개 장 중 ${chapter}번째 장">${chapters.map((name, position) => `<i class="${position + 1 === chapter ? "is-current" : ""}"><b>0${position + 1}</b>${name}</i>`).join("")}</span>
      </div>
      <section class="ta-visual" data-ta-visual="${id}" aria-label="${title}">${body}</section>
      <p class="ta-takeaway"><span>검토 원칙</span>${takeaway}</p>
      ${evidenceLine(evidence)}`,
  };
}

/** Render one concise architecture fact without creating a runtime control. */
export function fact(label, title, detail) {
  return `<article class="ta-fact"><small>${label}</small><strong data-ta-primary>${title}</strong><span>${detail}</span></article>`;
}
