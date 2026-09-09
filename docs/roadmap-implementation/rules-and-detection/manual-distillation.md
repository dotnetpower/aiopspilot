# Manual Distillation implementation ledger

This delivery ledger preserves reviewable implementation scope, append-only transitions,
and resumable work while the roadmap owner remains focused on normative design.

## Implementation status

### Implementation scope

| Area | State | Evidence | Notes |
|------|-------|----------|-------|
| Access and bounded drop-directory ingestion | implemented | `services/core-control-plane/src/fdai/shared/providers/manual_source.py`; `services/core-control-plane/tests/providers/test_manual_source.py` | `ManualSource` and `DropDirectoryManualSource` preserve source identity, reject traversal and symlink escape, and keep oversize files as metadata-only review items rather than deletion signals. |
| Sensitivity and deterministic triage | implemented | `services/core-control-plane/src/fdai/rule_catalog/pipeline/distill/sensitivity.py`; `triage.py`; focused sensitivity and triage tests | Secret and PII findings are value-free. Multiple credentials on one line are scanned, while filtering, exact deduplication, authority ranking, and prioritization remain deterministic. |
| Classifier and distiller provider boundaries | implemented | `services/core-control-plane/src/fdai/shared/providers/manual_classifier.py`; `distiller.py`; `services/core-control-plane/src/fdai/composition/wire_distiller.py` | Abstaining defaults select no manual or candidate. Classifier output preserves each exact input identity, absent ontology-council records keep abstention, and partial bindings fail startup. |
| Freshness, deletion, coverage, and orchestration | implemented | `services/core-control-plane/src/fdai/rule_catalog/pipeline/distill/freshness.py`; `coverage.py`; `orchestrator.py`; corresponding focused tests | Transient fetch failures and sensitivity or source-limit holds stay out of the snapshot and retry. Empty-source and oversize guards prevent false retirement. Malformed code fences create explicit review gaps. |
| Ontology claim inventory and review packaging | implemented | `services/core-control-plane/src/fdai/rule_catalog/pipeline/distill/ontology_claims.py`; `ontology_review.py`; focused claim and review tests | Zero-candidate outcomes retain structural claims as `needs_review`. Claim mapping requires the current content digest, and council receipts cover inventoried claims exactly once. |
| Ontology proposal, identity, and verification gates | implemented | `services/core-control-plane/src/fdai/rule_catalog/pipeline/distill/ontology_build.py`; `ontology_models.py`; `ontology_verify.py`; focused build and verifier tests | Object and link aliases preserve exact, unique, or bounded ambiguous resolution. Lower-priority conflict resolution retains the overridden evidence references. |
| Ontology lifecycle and reconciliation | implemented | `services/core-control-plane/src/fdai/rule_catalog/pipeline/distill/ontology_lifecycle.py`; `test_ontology_lifecycle.py` | Projection requires a validated plan, and rollback can restore only the exact recorded prior graph revision. |
| T2 ontology extraction council | implemented | `services/core-control-plane/src/fdai/rule_catalog/pipeline/distill/ontology_council.py`; `test_ontology_council.py` | Three blind ballots require distinct model families, bindings, and fault domains. Consensus remains proposal-only and review-only. |
| CLI and source-manifest integration | implemented | `services/core-control-plane/src/fdai/rule_catalog/pipeline/distill_cli.py`; `services/core-control-plane/src/fdai/rule_catalog/schema/source_manifest.schema.json`; focused CLI and schema tests | `manual-distill` runs the inert plan and persists bounded freshness state without promoting or executing candidates. |
| Deployment-specific models, back-translation, and customer connectors | not-applicable | [Downstream seam recipe](../../roadmap/fork-and-sequencing/downstream-fork-seam-recipes.md#516-manual-distillation-manualsource--manualclassifier--distiller); abstaining upstream provider defaults | Concrete model-backed extraction, source-fidelity back-translation, and silo connectors remain downstream responsibilities. This upstream ledger claims no live model fidelity, customer-corpus quality, or production promotion evidence. |

### Implementation history

| Date | State | Change | Evidence | Remaining |
|------|-------|--------|----------|-----------|
| 2026-08-24 | in-progress | Migrated the legacy status into the delegated ledger without reconstructing earlier provenance. | `current change`; preserved owner status from `docs/roadmap/rules-and-detection/manual-distillation.md`. | Replace the legacy summary with bounded evidence-backed scope rows and observable exits. |
| 2026-09-10 | implemented | Replaced the migrated summary with bounded scope rows and completed 15 critique-to-hardening rounds across ingestion, source safety, provenance, coverage, ontology identity, lifecycle, council isolation, and audit lineage. One lifecycle concern was withdrawn after the design confirmed pre-projection approval rejection is valid. | Commits `33a32dc8b` through `323e73949`; `uv run pytest -q --no-cov services/core-control-plane/tests/rule_catalog/pipeline/distill services/core-control-plane/tests/providers/test_manual_source.py services/core-control-plane/tests/providers/test_manual_classifier.py services/core-control-plane/tests/providers/test_distiller.py services/core-control-plane/tests/composition/test_wire_distiller.py` (`323 passed`); routed Ruff and strict mypy checks passed; independent base and ontology re-reviews found no findings above Low; `current change` updates this ledger and passes the roadmap tracking gate. | No above-Low work remains. Informational Low residuals are coarse malformed-fence reporting, repeated retry cost for permanently unavailable sources, one unused identity-resolution operation field, and untyped lifecycle transition references. |

### Remaining work

- [x] Replaced the migrated legacy summary with bounded evidence-backed scope rows, 15 verified
  hardening rounds, and final reviews with no findings above Low.
- [x] Kept concrete model, back-translation, customer-connector, customer-corpus, and live-promotion
  evidence outside the upstream completion claim; downstream deployments own those implementations
  through the documented provider seams.
