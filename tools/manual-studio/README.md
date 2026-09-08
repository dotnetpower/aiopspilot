# Manual Studio

Manual Studio presents FDAI reference decks on a fixed 1536x864 canvas. The viewer scales the whole
slide for the available screen; the presentation is a static explanation, not an operational
control or a source of execution authority.

## Ontology deck files

| File | Responsibility |
|------|----------------|
| [ontology-foundation.js](ontology-foundation.js) | Preserves the approved title page and assembles the forty-slide deck. |
| [ontology-slide-kit.js](ontology-slide-kit.js) | Shared slide structure, short citations, tables, and connected diagrams. |
| [ontology-story-foundations.js](ontology-story-foundations.js) | Slides 2-14: motivation, history, and the operating definition. |
| [ontology-story-contracts.js](ontology-story-contracts.js) | Slides 15-28: identity, time, evidence, and semantic boundaries. |
| [ontology-story-operations.js](ontology-story-operations.js) | Slides 29-40: bounded queries, agents, effects, scenarios, and adoption. |
| [ontology-editorial.css](ontology-editorial.css) | Restrained ivory layouts and typography for the 39 body slides only. |
| [ontology-foundation.css](ontology-foundation.css) | Existing base styles, retained for the approved cover's rendering compatibility. |
| [ontology-opening.css](ontology-opening.css) | Slide 1 only: title, short subtitle, and decorative artwork. |
| [manual-content.js](manual-content.js) | Registers the ontology deck alongside other manuals. |
| [catalog.json](catalog.json) | Catalog identity, level, duration, and slide count. |
| [validation-evidence.json](validation-evidence.json) | Recorded validation history; a scoped review does not revalidate earlier deck revisions. |

## Refine one slide at a time

Keep the opening stylesheet scoped to `.manual-slide.slide-ontology-cover` and loaded after the
shared styles in both viewer entry points. The opening's content-density contract is in
[test/prototype.test.mjs](test/prototype.test.mjs). Explanations, agendas, and instructional diagrams
belong in the body slides. The cover's unlabeled architectural SVG is decorative, hidden from
assistive technology, and independent of external images or fonts.

Body slides use one central visual and one takeaway instead of stacking several boxed summaries.
History retains its chronology and qualifications; examples stay labeled. Meaning, observed state,
policy, approval, execution, and independent effects remain distinct. ObjectSet examples name the
actual `truncated` and `truncation_reason` fields rather than invented receipt flags.

Interpretation branches show alternative meanings, not resource relationships. Query graphs label
their scope and direction; the agent diagram connects independent roles to an event bus rather than
to each other. Comparison closure stays separate from an unscorable hold. These distinctions are
covered by [test/ontology-diagrams.test.mjs](test/ontology-diagrams.test.mjs).

Preserve presentation-size text rather than shrinking it to resolve crowding. Check the actual
browser viewport, text bounds, contrast, connector endpoints, and neighboring content regions.
A hidden shared browser can report a zero-size viewport; that is not responsive-validation evidence.
Use a local Chromium context for repeatable dimensions and inspect a full-size screenshot as well.

## Validation

Run `npm --prefix tools/manual-studio run check` from the repository root. The opening contracts in
[test/prototype.test.mjs](test/prototype.test.mjs) protect its content boundaries and stylesheet scope.
When adding a runtime-loaded asset, update the
[static artifact allowlist](../../scripts/deployment/azure/build_manual_studio_artifact.py) and its
[integration test](../../tests/integration/scripts/test_build_manual_studio_artifact.py).

Store screenshots and PDFs outside the repository. Record only performed checks, their slide scope,
and the tested content revision; retain older evidence as history rather than silently relabeling it.

## Related guidance

| To learn about | Read |
|----------------|------|
| Presentation and evidence standards | [Manual Studio guide](../../.github/skills/manual-studio/SKILL.md) |
| Meaning and authority boundaries | [FDAI Constitution](../../docs/roadmap/architecture/fdai-constitution.md) |
| The operating meaning model | [Operating ontology](../../docs/roadmap/architecture/operating-ontology.md) |
