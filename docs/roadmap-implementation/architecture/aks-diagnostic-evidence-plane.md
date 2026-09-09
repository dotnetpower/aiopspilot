# AKS Diagnostic Evidence Plane Implementation

This ledger records the delivery state for the bounded AKS diagnostic evidence plane defined in
the [owner design](../../roadmap/architecture/aks-diagnostic-evidence-plane.md).

## Implementation status

### Implementation scope

| Area | State | Evidence | Notes |
|------|-------|----------|-------|
| Exact topology and basic runtime state | validated | Issue #278 and local base commit | One exact cluster generation proved 103 Kubernetes Resources, 208 verified relationships, and one exact Node-to-VMSS VM bridge. |
| Fleet-safe source bindings | not-started | Issue #578 | Legacy single-cluster configuration remains active. |
| Diagnostic object facts and relationships | in-progress | Existing Kubernetes inventory, lifecycle, log, diagnosis, recovery, and rollout modules | Node pressure, Pod scheduling details, endpoint target health, storage, policy, and autoscale facts remain incomplete. |
| Metric, log, and Event evidence | in-progress | Existing provider-neutral metrics, content-free Pod log summary, and durable Event history | Exact operational provider bindings and combined receipts remain incomplete. |
| Deterministic diagnosis | in-progress | Existing Pod termination, recovery, replacement, and rollout reducers | Scheduling, endpoint, storage, policy, Node, and control-plane families remain open. |
| Operator and Console projection | not-started | Issue #578 | Exact diagnostic receipts are not yet exposed as a dedicated bounded projection. |
| Live validation and hardening | not-started | Issue #578 | At least ten rounds and live positive plus unavailable evidence are required. |

### Implementation history

| Date | State | Change | Evidence | Remaining |
|------|-------|--------|----------|-----------|
| 2026-09-10 | in-progress | Added server-allowlisted Kubernetes identity and diagnostic facts to the instance projection and Console Inspector. | `current change`; focused Operator decoder, Console decoder, i18n, typecheck, and build checks. | Bind Forseti receipt history and retain authenticated live geometry evidence. |
| 2026-09-10 | in-progress | Added Forseti-owned deterministic T0 diagnostic receipts for workload, Node, endpoint, storage, quota, autoscale, metric, and control-plane signals. | `current change`; focused family, hold, conflict, and no-authority tests. | Bind receipts through the secured Operator projection and add remaining live evidence. |
| 2026-09-10 | in-progress | Required source revision and independent provider-window coverage for content-free Pod log evidence. | `current change`; focused log collection, diagnosis, runtime binding, and completeness tests. | Bind a deployed coverage-producing log adapter and live receipt. |
| 2026-09-10 | in-progress | Added exact-target Kubernetes metric evidence with independent provider-window coverage. | `current change`; focused metric scope, empty-window, coverage, and mismatch tests. | Bind deployed metric coverage and deterministic resource-pressure diagnosis. |
| 2026-09-10 | in-progress | Added content-safe EndpointSlice health and exact target Pod UID relationships. | `current change`; focused EndpointSlice fact, source-schema, and relationship tests. | Add bounded metric evidence and deterministic endpoint diagnosis. |
| 2026-09-10 | in-progress | Added exact storage, policy, autoscale, quota, and limit ResourceTypes with bounded facts and reviewed relationships. | `current change`; focused catalog, collection, and relationship tests. | Add EndpointSlice target health and metric evidence. |
| 2026-09-10 | in-progress | Added content-safe Node, Pod, init-container, ephemeral-container, scheduling, probe, resource, and workload diagnostic facts. | `current change`; focused diagnostic fact and API inventory tests. | Add storage, policy, autoscale, endpoint, and metric evidence. |
| 2026-09-10 | in-progress | Separated stable UID identity from versioned Kubernetes observation metadata and added a fail-closed exact resolver. | `current change`; focused API inventory and resolver tests. | Bind the resolver to persistence and operator projection after diagnostic facts land. |
| 2026-09-10 | in-progress | Added the fleet binding and per-cluster source-state implementation. | `current change`; focused configuration, composition, enrichment, and metadata tests. | Complete the remaining diagnostic evidence families and live validation. |
| 2026-09-10 | in-progress | Adopted the implementation ledger and bounded design after Issue #278 topology completion. Earlier diagnostic provenance was not reconstructed. | Current source paths listed in the scope table and Issue #578. | Implement every open scope row, complete ten hardening rounds, and retain live evidence. |

### Remaining work

- [ ] Pass focused tests for fleet-safe bindings and exact resource resolution.
- [ ] Pass focused tests for diagnostic objects, endpoint health, metrics, logs, and Event coverage.
- [ ] Pass focused deterministic diagnosis and no-authority projection tests.
- [ ] Record at least ten hardening rounds with no unresolved finding above Low.
- [ ] Retain one live exact-cluster positive receipt and one explicit unavailable or absence receipt.
- [ ] Record final validation, local commits, cleanup, and Issue #578 completion evidence.
