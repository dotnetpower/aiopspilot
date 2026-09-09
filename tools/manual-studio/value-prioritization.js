/** Assemble the 25-slide value-prioritization workshop; it grants no runtime authority. */
import { evidenceLine, sources } from "./value-prioritization-slide-kit.js";
import { buildValuePrioritizationFoundations } from "./value-prioritization-foundations.js";
import { buildValuePrioritizationEligibility } from "./value-prioritization-eligibility.js";
import { buildValuePrioritizationValue } from "./value-prioritization-value.js";
import { buildValuePrioritizationPortfolio } from "./value-prioritization-portfolio.js";
import { buildValuePrioritizationAction } from "./value-prioritization-action.js";

/** Return the complete static deck in its authored decision sequence. */
export function buildValuePrioritizationDeck() {
  const cover = {
    brandLogo: "assets/microsoft-logo.png",
    eyebrow: "VISION & VALUE / L200",
    deckTitle: "FDAI / VALUE PORTFOLIO",
    title: "Use Case &<br>Value Prioritization",
    lead: "검증 가능한 첫 결정을 선택하는 포트폴리오 워크숍",
    layout: "briefing-value-cover deck-value-prioritization",
    priority: {
      id: "cover",
      chapter: 1,
      state: "PROPOSAL",
      sources: [sources.constitution, sources.metrics],
    },
    content: `
      <section class="vp-cover-field" aria-hidden="true">
        <i></i><i></i><i></i><i></i>
      </section>
      <div class="vp-cover-meta"><span>L200</span><span>35 MIN</span><span>25 SLIDES</span></div>
      ${evidenceLine(["constitution", "metrics"])}`,
  };

  return [
    cover,
    ...buildValuePrioritizationFoundations(),
    ...buildValuePrioritizationEligibility(),
    ...buildValuePrioritizationValue(),
    ...buildValuePrioritizationPortfolio(),
    ...buildValuePrioritizationAction(),
  ];
}
