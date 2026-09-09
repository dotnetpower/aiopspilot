# System Knowledge Service implementation ledger

This delivery ledger tracks the independently packaged system-knowledge bot while the roadmap
owner remains focused on its normative design and safety boundary.

## Implementation status

### Implementation scope

| Area | State | Evidence | Notes |
|------|-------|----------|-------|
| Independent service design and ownership | implemented | `docs/roadmap/interfaces/system-knowledge-service.md`; project, service-layout, channel, and graduation owners | The revised design separates the knowledge bot from Core, Operator Service, and the operational A3 edge while retaining Muninn and Bragi accountability. |
| Versioned system-knowledge contracts | implemented | `fdai_service_contracts/system_knowledge.py`; `test_system_knowledge.py` (`3 passed`) | Request, response, catalog, record, citation, status, source revision, and digest contracts reject authority and malformed evidence. |
| Release-bound catalog and retrieval | implemented | `catalog.py`; `seeds.py`; packaged `data/catalog.json`; `test_catalog_search.py` | Fourteen reviewed records compile from repository sources. Exact aliases and bilingual lexical retrieval return citations, while unrelated input returns a complete empty result. |
| Teams mention bot runtime | implemented | `teams_{auth,ingress,publisher}.py`; `runtime.py`; `ledger.py`; `blob_ledger.py`; focused service tests (`21 passed`) | Bot service identity, tenant, team, channel, recipient, mention entity, and sender mapping gate search. SQLite handles local claims and Managed Identity Blob CAS handles deployed claims and restart reconciliation. |
| Independent distribution and image | implemented | `pyproject.toml`; `docker/Dockerfile`; wheel and local image builds; packaging checks | The runtime layer runs as UID 65532 and contains the 14-record catalog without repository source. |
| Production persistence and deployment | implemented | `blob_ledger.py`; `infra/services/system-knowledge-service/`; `system-knowledge-deploy.yml`; Terraform validation and deployment-helper checks | The root creates a private Blob claim container, dedicated UAMI, three minimum roles, one-replica Container App, F0 Azure Bot, and Teams channel. The protected workflow seals plan/apply and builds the Teams package. Live provider, cost, disable, and timed rollback evidence remain open. |

### Implementation history

| Date | State | Change | Evidence | Remaining |
|------|-------|--------|----------|-----------|
| 2026-09-10 | implemented | Corrected catalog generation so `source_revision` resolves from protected `origin/main`, while each record continues to pin current reviewed source blobs independently. | `current change`; compiler, CLI, exact catalog provenance test, derived-source ancestry gate, and regenerated 14-record artifact. | No catalog-lineage work remains; production graduation evidence stays open and issue #262 paths remain unchanged. |
| 2026-09-10 | implemented | Regenerated the tracked catalog from a reachable source snapshot and corrected its focused check to prove that ancestor revision, every cited blob, and current compiled record content without requiring the artifact to contain the hash of its own commit. | `current change`; packaged catalog plus focused catalog provenance and complete System Knowledge Service tests | No catalog-provenance work remains for this bounded correction. |
| 2026-09-10 | implemented | Restored clean-checkout import and source-scan coverage, regenerated the 14-record release catalog from current reviewed sources, and aligned repository CI inventories with the sixth service candidate. | `current change`; service tests, catalog equivalence, venue coverage, runtime-image inventory, OPA setup inventory, and aggregate-coverage contract checks. | Keep the existing production canary, persistence, disable, and rollback evidence open; no deployment work changed. |
| 2026-09-09 | in-progress | Replaced the proposed Core and Operator integration with a dedicated system-knowledge microservice and Teams bot boundary. | `current change`; canonical bilingual design and this ledger. | Implement contracts, catalog, search, Teams transport, package, image, and focused checks; keep production enablement blocked until runtime evidence exists. |
| 2026-09-09 | implemented | Added the separate service contracts, 14-record release catalog, deterministic bilingual search, mention-only Teams boundary, restart-safe claim ledger, package, and non-root image. | `current change`; 18 service and contract tests, strict mypy, Ruff, wheel build, image build, and runtime-layer source-isolation check passed. | Retain downstream Teams, persistent-volume, cost, disable, and timed rollback evidence before changing production scope to `validated`. |
| 2026-09-10 | implemented | Replaced the deployment volume assumption with Managed Identity Blob CAS, added the independent Terraform root, deterministic Teams package, protected plan/apply workflow, and explicit enable/disable rollback boundary. | `current change`; 21 service tests, deployment-helper and workflow tests, strict mypy, Ruff, Terraform validation, and Teams package determinism checks. | Push an exact green revision, apply its guarded plan, install the Teams package, run mention and restart canaries, record cost, and prove disable within 15 minutes. |

### Remaining work

- [x] Add the service-contract models and pass their focused validation tests.
- [x] Compile the reviewed reference records from tracked files and pass whole-catalog source
  precision and bilingual retrieval tests.
- [x] Pass Teams authentication, mention-only admission, same-conversation reply, request bounds,
  and duplicate-delivery tests.
- [x] Build the service wheel and non-root container image with repository source absent from the
  runtime layer.
- [ ] Record a downstream Teams canary and Blob-backed restart-deduplication receipt for the exact
  image.
- [ ] Record cost evidence and a protected disable and rollback rehearsal within 15 minutes before changing the
  production state to `validated`.
