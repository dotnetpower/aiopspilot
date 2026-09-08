# AI/Data Readiness & Maturity editorial plan

This plan rebuilds the readiness manual as an evidence-led workshop for an adoption sponsor,
service owner, data lead, AI evaluation lead, and security reviewer. The reader should leave with
one bounded pilot decision, a defensible capability profile, and an owned improvement backlog.
It changes presentation content, not FDAI runtime behavior or authorization.

## Decision and audience

- **Audience:** a cross-functional adoption team at Discovery & Alignment, level L200.
- **Decision:** what can be investigated now, what blocks a read-only pilot, and which evidence
  must be produced before a later operational review.
- **Problem:** a convincing model demonstration does not establish usable data, repeatable
  evaluation, accountable operation, or permission to change a resource.
- **Deliverables:** a decision charter, source contracts, a six-dimension maturity profile,
  evaluation design, owned gaps, and a dated review plan.
- **Scope:** one cloud-operations decision. This is not a universal enterprise AI certification,
  an automated scoring product, or a new authority ladder.

## Initial design and critique

The previous 25-slide deck explained execution safeguards but offered few usable data or AI
assessment methods. Three short phrases often occupied a large table or repeated card layout.
Implementation details displaced the title's central questions: what makes data fit for a decision,
how to evaluate AI, and how a team becomes consistently better at both.

The initial replacement idea was a scored checklist across six dimensions. Critique changed it:

- **No average score:** an attractive total can hide a missing access review or an unverified
  target. Use dimension-specific evidence and named blockers instead.
- **No authority ladder:** maturity describes repeatability, not increasing autonomy. Keep M1-M5
  separate from presentation level L200, decision tiers T0-T2, and execution modes.
- **No invented standard:** label the rubric, timetable, and workshop as proposals. Cite FDAI
  design requirements without implying that they define an industry maturity certification.
- **No mandatory mutation controls on reads:** explain the authorization and evidence contract for
  a read-only pilot separately from all seven safeguards required before a state change.
- **No measured-looking fiction:** carry one explicitly illustrative change-review scenario through
  the source contract, coverage calculation, maturity profile, decision memo, and gap register.
- **No baseline confusion:** distinguish the team's current-workflow diagnostic baseline from
  FDAI's governed reference-system/treatment performance claim. A sample floor is not statistical
  proof, and an offline answer test is not an operational effect measurement.
- **No feature-status inventory as the story:** retain a compact implementation-versus-environment
  boundary, but make the majority of the manual useful even before a deployment exists.

### Review disposition

The pre-implementation review sharpened four requirements: make role and exit evidence explicit in
the gap register; show the reason for each illustrative maturity judgment; introduce data
minimization with the decision charter rather than after collection; and close the worked example
with a bounded hold plus a concrete next review, not an invented successful future.

Not all review suggestions were admissible. Do not invent measured reference-agent results,
universal 30-day maturity thresholds, or new ontology relationship names. The semantic diagram uses
the documented `implemented_by` and `workload_runs_on` relationships. Model-use approval, document
access, evidence coverage, and mutation authority remain separate conditions. The example's 14
mapped resources never establish complete impact coverage for the original 20-resource scope.

Slide 25 therefore describes **assessment confidence**, not authorization. The final workshop
proposes a scope for the accountable owner to review; it grants no read, model-export, deployment,
or resource-change permission. Evidence windows and sample sufficiency are agreed per dimension
before assessment, and the rubric claims no quantitative maturity score.

## Revised story

The manual has 32 slides in five chapters. Every slide has one job, one dominant visual, one
actionable takeaway, and compact source citations with full paths retained in metadata.

| Slide | Reader question or decision | Visual | Evidence basis |
|-------|-----------------------------|--------|----------------|
| 1 | How do we move from using AI to operating it responsibly? | Quiet editorial cover with existing authorized artwork | Constitution |
| 2 | Why does a good demonstration fail to establish operational readiness? | Demonstration versus operating record | Constitution |
| 3 | How do readiness and maturity differ? | Two complementary lenses | Proposed assessment model |
| 4 | Which six capabilities need evidence? | Six-part diagnostic map | Proposed model; Constitution, data governance, LLM strategy |
| 5 | What exactly is the first decision? | Completed illustrative decision charter | Constitution, operating ontology |
| 6 | Which starting scope can be independently evaluated? | Three use-case eligibility comparisons | Constitution, goals and metrics |
| 7 | Which data serves which part of the decision? | Evidence supply map | Operating ontology |
| 8 | What does a usable source contract contain? | Completed illustrative data contract | Data governance, Constitution |
| 9 | How can a reviewer falsify data quality? | Six quality questions and failure tests | Proposed diagnostic checklist; data governance |
| 10 | What is missing from the denominator? | Illustrative 20-item coverage strip and calculation | Constitution, goals and metrics |
| 11 | When does collected evidence become too old? | Event, expiry, arrival, and decision timeline | Operating ontology, Constitution |
| 12 | How do assets acquire service and ownership context? | Directed service/workload/resource relationships | Operating ontology |
| 13 | When is a retrieved document usable evidence? | Source revision and claim-support comparison | Document ingestion, LLM strategy |
| 14 | What must be governed before sending data to AI? | Classification, use, retention, and deletion lifecycle | Data governance |
| 15 | Which reasoning mechanism does the problem need? | T0/T1/T2 decision design | LLM strategy, Constitution |
| 16 | What belongs in an evaluation set? | Six scenario classes with expected behavior | Proposed evaluation pack; Constitution, LLM strategy |
| 17 | What does a good answer do when facts are missing? | Unsupported answer versus bounded answer | Constitution, LLM strategy |
| 18 | Which layer does each quality metric actually measure? | Retrieval, answer, and task metric map | Proposed measurements; goals and metrics |
| 19 | How do we make the comparison fair? | Paired cohorts and a frozen evaluation basis | Goals and metrics |
| 20 | What makes a quality result operationally affordable? | Work-unit economics and bounded budgets | Goals and metrics, LLM strategy |
| 21 | What happens after data, prompts, or models change? | Version and review lifecycle | LLM strategy, data governance |
| 22 | What do the five maturity levels mean? | Evidence-backed maturity staircase | Proposed rubric |
| 23 | What evidence distinguishes data-side maturity? | Value, data, and semantic-context rubric | Proposed rubric; ontology, governance |
| 24 | What evidence distinguishes AI and operating maturity? | Evaluation, people/process, governance rubric | Proposed rubric; LLM strategy, Constitution |
| 25 | How credible is the assessment itself? | Assessment-confidence ladder and unknown handling | Proposed assessment protocol; Constitution |
| 26 | How does one realistic capability profile look? | Illustrative six-dimension profile without an average | Proposed rubric; illustrative scenario |
| 27 | What decision follows from that profile? | Filled decision memo with permitted and held scope | Constitution; illustrative scenario |
| 28 | What closes each gap, and who proves it? | Filled gap register | Proposed improvement plan |
| 29 | What is implemented versus still deployment-owned? | Implementation, environment, and authority separation | Data governance, goals and metrics, Constitution |
| 30 | What can the team produce in the first 30 days? | Four checkpoints with owners and observable exits | Proposed schedule, not a delivery promise |
| 31 | How do we conduct the assessment conversation? | 90-minute workshop agenda and outputs | Proposed workshop |
| 32 | What should the next meeting approve? | Decision brief and explicit next actions | Constitution; proposed adoption method |

### Assessment model

Use six dimensions: value and scope; data quality and lifecycle; semantic and service context;
AI evaluation and lifecycle; people and operating process; governance and safe change.

M1-M5 mean ad hoc, defined, repeatable, evidenced, and continuously improved. Each dimension is
assessed separately. Do not infer M1 from missing evidence: record **unassessed**. Mark a dimension
not applicable only with scope rationale and reviewer confirmation. A target level is selected
for this pilot, not prescribed for every organization. Neither a high level nor a complete profile
grants runtime approval or proves an operational outcome.

### Worked example

The fictional team wants a read-only briefing before a change to an API workload. It is not
requesting automatic approval, a definitive causal diagnosis, or resource modification. A frozen
illustrative scope contains 20 resources: 14 have current reviewed mappings, three are unmapped,
two are inaccessible, and one has stale evidence. No item disappears from the denominator.

The maturity profile is a separate qualitative workshop assessment, not a calculation from that
70% mapping-coverage example. Missing model-use approval holds model transmission. The team may
continue authorized data-quality investigation while the owner closes that specific gap.

## Visual direction

- **Canvas:** retain the viewer's uniformly scaled 1536x864 presentation canvas and 16:9 print.
- **Palette:** warm ivory, dark ink, restrained teal for evidence, amber for gaps, and indigo for
  review. Pair every state color with text or a pattern.
- **Type:** 43px slide titles, 24-26px leads and primary body, 19-21px secondary labels, and
  13-16px technical citations. Shorten or split content rather than reducing the primary floor.
- **Composition:** favor unboxed editorial groups, useful tables, annotated records, diagrams,
  comparisons, a coverage strip, a maturity profile, and a gap register. Do not repeat three
  consecutive card or flow slides.
- **Geometry:** use one CSS Grid coordinate system for connected nodes; measure connector endpoints.
- **Assets:** retain the existing catalog artwork and reuse it for the editorial cover. Author diagrams locally without external assets,
  web fonts, remote model requests, or customer data.

## Implementation and validation plan

1. Replace the generic topic-list builder for this manual with a dedicated deck entry point,
   slide helpers, and chapter modules. Keep other deck objects unchanged.
2. Add scoped presentation styles to both viewer entry points. Update the static artifact
   allowlist and its focused test so every transitive import and stylesheet ships.
3. Update the catalog count and description, add behavioral content contracts, and keep earlier
   validation evidence as history of the old deck rather than relabeling it as current.
4. Run JavaScript syntax and focused Manual Studio tests, the packaging integration test,
   punctuation, and readable-Hangul checks.
5. Render all 32 slides at 1440x900, inspect full-size captures and contact sheets, and measure
   text bounds, region overlap, contrast, body-font floor, and connector geometry.
6. Recheck all slides at 993x641 and 390x844, then through real slide-stage fullscreen and print.
   Count every PDF page and verify every 16:9 MediaBox. Store artifacts outside the repository.
7. Record only completed checks, exact source/deck digests, and the scope of visual review.
   Leave runtime, live model, and production-readiness validation explicitly out of scope.

### Completed presentation review

On 2026-09-08, the 32-slide rebuild passed 160 slide/mode checks: desktop, tablet, mobile, actual
slide-stage fullscreen, and print. Full-size images and four contact sheets were inspected. The
first pass identified a cover line-box issue and a workshop agenda overlapping its takeaway;
line spacing and row padding resolved both without reducing primary text. Coverage segments were
also bound to their exact displayed proportions rather than flex-weight approximations.

All 32 PDF pages have 1152x648-point MediaBoxes and extractable text. The final checks found no
clipped text, region overlap, failed request, or page error; primary text remains at least 24px.
The exact deck and stylesheet digests are recorded in the scoped review in
[validation-evidence.json](validation-evidence.json). The other nine additional deck objects retain
their pre-edit digest. These checks establish presentation behavior, not operational readiness.

## Premium visual refinement

The next review keeps the 32-slide story and its original adoption decision, but separates two
jobs the first revision mixed: a cover introduces the subject; body slides explain it. The user
found the artwork, agenda, and explanatory cover too elaborate, while the body still relied too
heavily on text columns and tables.

### Initial direction, critique, and revision

- **Initial direction:** add richer artwork, color, and icons across the deck.
- **Critique:** decorative artwork would repeat the cover problem. Icons alone would leave the
  body as the same text in prettier boxes, and a radar score would misrepresent qualitative
  maturity as a measured continuous quantity.
- **Revised direction:** use a typography-only cover and meaning-led diagrams in the body.
  Preserve concrete explanations, source citations, uncertainty, and all authority boundaries.
  Use a categorical dot profile, not filled bars or a radar area, for M1-M5.

### Scope and visual jobs

| Area | Revised visual | Content improvement |
|------|----------------|---------------------|
| Cover | Title, one-line subtitle, restrained metadata | Remove artwork, agenda, and body-level claims. |
| Readiness versus maturity | A current checkpoint and repeated review cycles | Separate one scoped decision from the ability to repeat it. |
| Six dimensions | One decision connected to six assessment perspectives | Keep people and governance equal to data and AI. |
| Data supply | Typed sources converging on an evidence bundle | Name the source's job and what it cannot prove. |
| Data quality | Six visible failure mechanisms rather than six table rows | Pair each check with an observable failure response. |
| Coverage | Twenty individually accounted-for units and an exact proportional strip | Keep all unknowns in the denominator and label the example. |
| Freshness | Proportional time axis with a valid interval and late arrival | Show why recent collection does not renew old facts. |
| Semantics and retrieval | Labeled graph and permission-first evidence path | Preserve exact relationship names and the distinction between documents and observations. |
| AI reasoning and evaluation | Tier-specific lanes, expected-outcome tests, and paired cohorts | Distinguish reasoning, deterministic verification, and authorization. |
| Measurement and economics | Numerator/denominator lenses and a cost composition | No invented performance results or decorative trends. |
| AI changes | Explicit version-review cycle with a re-evaluation path | Show what changes, who reviews it, and when to return to the prior version. |
| Maturity | Evidence milestones and a discrete six-row capability plot | No overall score; unassessed remains unassessed. |
| Decision and gaps | Held versus investigable scope and owned closure lanes | Keep assessment recommendations separate from permission. |
| First month | A proposed workstream calendar with review checkpoints | A date does not close a gate or grant promotion. |
| Workshop | A 90-minute proportionate agenda ring and deliverables | The diagram represents the proposed agenda, not operational metrics. |

Keep the warm paper, dark ink, and restrained evidence/hold/review palette. Use purposeful
monoline symbols, quiet full outlines, and content-local emphasis, not ornamental color rails or
large shadows. Keep 24px primary body text and the fixed 1536x864 canvas. Do not alter other books,
viewer navigation, runtime state, provider bindings, or existing implementation claims.

### Verification contract

The cover receives an executable content-density contract: no artwork, agenda, cards, teaching
diagram, or promotional caption. Graphs use one CSS Grid coordinate system and named endpoint
references. Time and agenda proportions derive from explicit illustrative values, with geometry
checks. Categorical maturity markers encode a named level only; empty evidence produces no marker.

Render and inspect all 32 slides at desktop size first, then tablet, mobile, real slide-stage
fullscreen, and print. Check text and component bounds, connector endpoints, exact proportions,
contrast, PDF page count, and every 16:9 MediaBox. Retain the previous review unchanged as history
and append only evidence from the new render. Capture screenshots and PDF outside the repository.

### Completed refinement review

The refined deck passed 160 slide/mode checks on one content digest at 1440x900, 993x641,
390x844, real fullscreen, and print. All 32 desktop images were inspected at full size, followed
by revised fullscreen captures and four contact sheets. The cover now has two title lines, one
subtitle line, and no artwork or agenda. Primary body text remains at least 24px.

Twenty-five grid connectors per pass touch their named node boundaries within 1 CSS pixel. The
coverage strip, time positions, categorical markers, and 90-minute agenda arcs match their declared
values. Explicit paper backing on the time labels prevents the thin axis line from being treated
as their text background. The minimum measured text contrast is 5.42:1, with no clipped text,
region overlap, page error, or failed request. All 32 PDF MediaBoxes are 1152x648 points.

The review is appended as `readiness-premium-visual-2026-09-08` in
[validation-evidence.json](validation-evidence.json). Previous evidence and the other nine
additional decks' content digests remain unchanged. This is presentation evidence only.

## Source map

| Contract | Source |
|----------|--------|
| Meaning, authority, reads versus changes, independent effects | [FDAI Constitution](../../docs/roadmap/architecture/fdai-constitution.md) |
| Classification, model terms, retention, deletion, deployment privacy | [Data governance](../../docs/roadmap/architecture/data-governance.md) |
| Identity, relation direction, time, unknown scope | [Operating ontology](../../docs/roadmap/architecture/operating-ontology.md) |
| Retrieval authorization and source inheritance | [Document ingestion](../../docs/roadmap/interfaces/document-ingestion.md) |
| Deterministic-first reasoning, model independence, lifecycle | [LLM strategy](../../docs/roadmap/architecture/llm-strategy.md) |
| Cohorts, units, uncertainty, zero-tolerance guards | [Goals and metrics](../../docs/roadmap/architecture/goals-and-metrics.md) |
| Presentation and evidence standards | [Manual Studio guide](../../.github/skills/manual-studio/SKILL.md) |
