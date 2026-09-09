# WAF and CAF evidence-governed assessment implementation ledger

This delivery ledger tracks the shared shadow assessment boundary for WAF workload controls and CAF
estate guidance without duplicating the normative design.

## Implementation status

### Implementation scope

| Area | State | Evidence | Notes |
|------|-------|----------|-------|
| Shared catalog and evidence contracts | implemented | `framework_assessment.py`; generated WAF and CAF catalogs; focused schema tests | The content-addressed catalogs account for all 59 WAF controls, 186 WAF requirements, and all 15 CAF areas. |
| WAF 59-control assessment | implemented | `core/framework_assessment/`; Azure supporting-evidence adapter; focused runtime and adapter tests | Exact workload scope, inventory generation, evidence failure boundaries, approved N/A, tradeoffs, immutable replay, and no-authority output are enforced. |
| CAF 15-area assessment | implemented | `azure-caf.source.yaml`; `framework_assessment_cli.py`; focused catalog, runtime, provider, and live-runner tests | Strict deployment profiles cover all areas. Strategy, Plan, and Adopt require procedure plus execution evidence, while hierarchy evidence stays scope- and generation-bound. |
| Operator API and Console | implemented | `framework_assessment_projection.py`; `/caf-controls`; WAF detail extension; focused Operator and Console checks | The API and Console preserve separate reference, mapping, applicability, evaluation, and satisfaction states and reject authority-bearing or out-of-order events. |
| Review-only source changes | implemented | `framework_review.py`; `test_framework_review.py` | Proposed source generations remain pending until the exact review-package digest is approved; failed proposals retain the prior valid generation. |
| Governed live-Azure receipts | not-started | Issues #402 and #403 | Run only from one pushed required-CI-green revision after focused local checks pass. |

### Implementation history

| Date | State | Change | Evidence | Remaining |
|------|-------|--------|----------|-----------|
| 2026-09-10 | in-progress | Adopted one shared WAF/CAF assessment owner after critiquing duplicated WARA copies, browser-side evaluation, and framework compliance scoring. Earlier implementation provenance was not reconstructed. | `current change`; framework assessment design; issues #402 and #403. | Implement the catalog, runtime, provider, projection, Console, replay, and live validation slices. |
| 2026-09-10 | implemented | Added complete WAF and CAF catalogs, deterministic evidence admission, provider adapters, immutable replay, audit and event services, review-only updates, Operator projections, localized Console views, and the private-runner live validation workflow. | `current change`; 230 focused Python tests passed; 16 focused Console tests, TypeScript checks, production build, strict mypy, Ruff, deterministic regeneration, localization, roadmap, and design-route gates passed. | Push one exact required-CI-green revision, retain and review the two live shadow receipts, then run issue #404 plan-only validation. |
| 2026-09-10 | implemented | Rejected unknown decisive evidence targets instead of silently omitting them, restored the Operator composition fanout ceiling, and made sharded coverage defer its threshold to the combined 90% gate. | `current change`; framework core passed 43 tests at 93.01% branch coverage; focused CI-contract and Operator composition checks passed 85 tests. | Retain the governed live WAF and CAF receipts after required CI is green. |
| 2026-09-10 | implemented | Registered the new framework projection tests to the Operator service test owner after CI correctly rejected an unowned service test path. | `current change`; the service-suite manifest and runner contract tests passed. | Retain the governed live WAF and CAF receipts after required CI is green. |
| 2026-09-10 | implemented | Rebound the packaged System Knowledge catalog to a reachable post-rebase source revision so release evidence remains reproducible after integration. | `current change`; packaged catalog parity and ancestry check. | Retain the governed live WAF and CAF receipts after required CI is green. |
| 2026-09-10 | implemented | Removed the optional scheduled WARA Job as a live-validation scope prerequisite. Protected validation now selects exactly one topology-bound PostgreSQL workload and fails closed on zero, multiple, or invalid candidates. | Failed protected run `34402162140`; sanitized deployment query confirmed zero Container Apps Jobs; focused exporter and workflow tests. | Retain and review the governed live WAF and CAF receipts after required CI is green. |

### Remaining work

- [x] Proved exact 59-control WAF and 15-area CAF catalog accounting with focused schema tests.
- [x] Proved missing, stale, conflicting, truncated, synthetic, wrong-scope, and unsupported evidence
  remains unknown in focused runtime tests.
- [x] Proved Strategy, Plan, and Adopt cannot pass without both procedure and execution evidence.
- [x] Proved external WAF reports and scores cannot establish satisfaction by themselves.
- [x] Proved immutable replay, tradeoff non-interference, event publication, and authority isolation.
- [x] Proved Operator API, Console, localization, and projection quarantine behavior.
- [ ] Retain and independently review one governed live-Azure shadow receipt for WAF and one for CAF.
