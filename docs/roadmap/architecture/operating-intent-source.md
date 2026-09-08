---
title: Deployment-Owned Operating-Intent Source
---
# Deployment-Owned Operating-Intent Source

`ServiceObjective`, `RecoveryObjective`, `CostObjective`, `ArchitectureConstraint`, `Ownership`, and
`ChangeWindow` are the six operating-intent ObjectTypes Forseti and the risk gate read as protected
objectives and constraints. They are supplied by a distinct deployment-owned source rather than the
generic `FDAI_OPERATING_MODEL_PATH` snapshot, which may legitimately carry only `Resource`
instances. This document owns that binding: its pinned identity, its fail-closed admission, the
bounded revalidation that keeps admission current, and the lock that serializes projection across
replicas.

> **Authority boundary:** the source supplies *intent shape*. Projecting it never grants
> maintenance, approval, or execution authority; it only makes typed objectives and constraints
> readable. Every state change still passes the typed ActionType, risk, approval, execution,
> verification, and recovery boundaries in
> [operating-ontology.md](operating-ontology.md).

## Pinned identity

The file MUST carry one `provenance` block (`source_url`, `resolved_ref`, `retrieved_at`), and the
operator pins `FDAI_OPERATING_INTENT_SOURCE_REVISION` and `FDAI_OPERATING_INTENT_SOURCE_SHA256`
once, out of band, after review - mirroring the frozen `configuration_drift` baseline precedent.
That digest covers the whole document, provenance included, so rewriting any provenance field, or
forward-dating a retrieval to defeat the freshness check, fails the pin exactly like editing an
objective.

The pin is only as honest as the parser under it. The intent-source parser therefore rejects any
member it does not recognize - at the document, `provenance`, object, and link level - so every
accepted member is covered by the digest. A tolerant parser would have discarded an added member
before hashing, leaving the pinned digest unchanged while the file on disk changed. The generic
`FDAI_OPERATING_MODEL_PATH` format stays tolerant, because it advertises no pin.

The binding is **on by default**: the Core image ships an approved generic source at
`/app/config/operating-intent/generic-source.json`, and the Terraform caller pins that path,
revision, digest, and per-type counts unless a deployment overrides them. Every pinned value lives on
its own `optional(...)` attribute rather than in an object-level `default` block, because Terraform
ignores an object-level default as soon as a caller supplies any attribute; tuning
`revalidate_seconds` alone therefore keeps the binding instead of silently disabling admission.
Replacing the shipped path without also replacing its revision and digest is rejected outright. The
shipped artifact's placeholder references and deliberately non-effective change window mean binding
it supplies intent shape and grants no authority.

## Fail-closed admission

Before projecting, the runtime fails closed - recording the reason and preserving the graph already
durably owned - on:

| Defect | Condition |
|--------|-----------|
| cross-release | `source_revision`, `provenance.resolved_ref`, or the whole-document digest disagrees with the binding. |
| missing | A required type has zero instances. |
| duplicate | A type exceeds its `FDAI_OPERATING_INTENT_SOURCE_EXPECTED_COUNTS_JSON` count (default one each). |
| incomplete | A type falls short of that same pinned count, so an approved objective cannot disappear silently. |
| stale | An instance is outside its effective interval, or the source exceeds an instance's declared `freshness_seconds`. |

Staleness has two independent axes that MUST NOT be conflated. The effective interval
(`effective_from`, `effective_to`) is *when the declared intent applies*. `freshness_seconds` is
*how recently the source was observed*, measured from `provenance.retrieved_at` and never from
`effective_from`, so a long-lived objective just read is fresh, a newly-effective objective
republished from an old retrieval is stale, and a `retrieved_at` in the future denies as an
untrusted observation time.

## Continuous admission

Admission is a proof about a moment, not a standing grant. A source that was complete and fresh at
startup can later leave its effective interval, exceed its declared freshness, change revision,
disappear from the deployment mount, or become unreachable.

A bounded revalidation worker therefore re-runs the identical fail-closed checks every
`FDAI_OPERATING_INTENT_SOURCE_REVALIDATE_SECONDS` (default 300; Terraform field
`operating_intent_source.revalidate_seconds`, bounded to 1..28800). Each pass records a durable
admission carrying the pinned revision, the whole-document digest, the validation time, and the
validity window that admission may back authority for. The window is a multiple of the interval, so
one slow pass does not withdraw authority while a stopped or persistently failing worker expires the
admission with no further action from anyone. A validation time later than the decision instant is
malformed and grants no authority.

A failing pass quarantines rather than deletes: the projected objects remain readable as evidence
and history, and only intent authority is withdrawn. A later valid refresh re-admits without a
restart, and re-admitting an unchanged, already-projected document refreshes the record without
rewriting the graph.

A pass that fails *after* validation fails closed the same way. Ontology-catalog validation, a
malformed durable manifest, and a store write failure all mean the pinned document did not become
the owned graph, so the attempt durably records a quarantine before it returns rather than aborting
startup or leaving the previous admission alive until it expires.

## Consumer fences

Authority consumers resolve that admission at the decision instant instead of trusting a projected
object, through three fences.

**Binding.** A consumer carries the exact revision and whole-document digest its own configuration
pins, so a record written under any other binding is rejected rather than accepted because it parses.
A consumer configured with no source is explicitly unconfigured: it does not consult the record at
all, which is the only supported way to keep the pre-existing generic `FDAI_OPERATING_MODEL_PATH`
behavior. For a configured consumer a *missing* record denies, because deletion, corruption, and the
interval before the first write are indistinguishable from one another and none of them proves
anything.

**Generation.** `FDAI_OPERATING_INTENT_SOURCE_GENERATION` (Terraform field
`operating_intent_source.generation`, raised whenever the pinned binding changes) orders two
otherwise equally valid bindings. During a rolling deployment the departing replica's revalidation
worker never overwrites a higher generation's record, and a consumer rejects a record from any
generation but its own - so an old replica can neither authorize nor quarantine the rollout that
replaced it, and a new rollout's proof never authorizes a replica that reads a graph it never
validated. The deployment-wide lock serializes writers but says nothing about which release should
win; the generation does. An unusable or future-dated newer-generation record keeps the older
replica fenced because malformed state cannot prove that rollback is safe.

**Ownership.** The record enumerates the object identities the admission vouches for. The generic
`FDAI_OPERATING_MODEL_PATH` snapshot and the continuous operating-model worker can both project a
`ChangeWindow`, and neither is covered by this pin, so an *allowing* window opens only when the
admitted record owns its id. A *blocking* window still blocks whoever supplied it: refusing to act is
never the unsafe direction. A quarantined, expired, unavailable, or malformed admission names no
ownership at all and therefore denies the whole maintenance surface.

## Replica serialization

Manifest inspection, interrupted-apply recovery, projection, and the admission write all run inside
the deployment-wide resource lock on the fixed `operating-intent-source:apply` identity - a constant,
because the lock serializes one deployment-wide manifest, and disjoint from the continuous
operating-model worker's key because the two sources own disjoint manifests. Startup takes that lock
too.

Without it, a replica starting beside another reads its peer's in-flight `applying` manifest as an
interrupted apply and deletes the subgraph the peer is still writing. A lock that cannot be acquired
records `unavailable` and projects nothing, so an unreachable lock backend fails closed instead of
racing.

## Implementation status

### Implementation scope

| Area | State | Evidence | Notes |
|------|-------|----------|-------|
| Pinned identity and provenance | implemented | [operating_intent_binding.py](../../../services/core-control-plane/src/fdai/runtime/operating_intent_binding.py), [operating_model.py](../../../services/core-control-plane/src/fdai/shared/providers/operating_model.py), [json_file.py](../../../services/core-control-plane/src/fdai/delivery/operating_model/json_file.py) | Whole-document digest covers provenance; the parser rejects unknown members at every level so nothing accepted escapes the digest; the binding is operator-pinned out of band. |
| Fail-closed admission | implemented | [core/operational_context/operating_intent_source.py](../../../services/core-control-plane/src/fdai/core/operational_context/operating_intent_source.py) | Cross-release, missing, duplicate, incomplete, and stale all deny and preserve the owned graph. |
| Continuous revalidation | implemented | [operating_intent_revalidation.py](../../../services/core-control-plane/src/fdai/runtime/operating_intent_revalidation.py), [operating_intent_source.py](../../../services/core-control-plane/src/fdai/runtime/operating_intent_source.py) | Bounded worker supervised beside the other runtime background workers. |
| Authority gating | implemented | [core/operational_context/operating_intent_admission.py](../../../services/core-control-plane/src/fdai/core/operational_context/operating_intent_admission.py), [core/risk_gate/ontology_preconditions.py](../../../services/core-control-plane/src/fdai/core/risk_gate/ontology_preconditions.py) | `ChangeWindow` evidence resolves the durable admission at the decision instant, fenced by configured binding, rollout generation, and manifest ownership; a missing record denies for a configured consumer. |
| Replica serialization | implemented | [operating_intent_source.py](../../../services/core-control-plane/src/fdai/runtime/operating_intent_source.py), [bootstrap_core.py](../../../services/core-control-plane/src/fdai/runtime/bootstrap_core.py) | Startup and every revalidation hold the deployment-wide lock; acquisition failure is explicit. |
| Deployment binding | implemented | [core-control-plane module](../../../infra/services/core-control-plane/modules/core-control-plane/variables.tf), [Core caller](../../../infra/services/core-control-plane/variables.tf) | Path, revision, digest, per-type counts, rollout generation, and revalidation interval are all Terraform-threaded; the caller's per-attribute defaults keep the shipped generic binding on under a partial override. |

### Implementation history

| Date | State | Change | Evidence | Remaining |
|------|-------|--------|----------|-----------|
| 2026-09-09 | implemented | Kept older replicas fenced when a newer-generation admission has an invalid validity window or future proof time. | `current change`; focused rolling-replica regression tests. | Retain one governed deployed runtime receipt before advancing this area to `validated`. |
| 2026-09-09 | implemented | Rejected future-dated durable admissions so clock skew cannot produce a negative age that extends authority. | `current change`; focused admission regression test. | Retain one governed deployed runtime receipt before advancing this area to `validated`. |
| 2026-09-05 | implemented | Closed the review findings that let admission be trusted more widely than it was proven. The intent-source parser now rejects unknown document, `provenance`, object, and link members, so the advertised whole-document pin covers every accepted member instead of a lossy projection. Admission records carry the rollout generation and the object identities they vouch for; a consumer is fenced to its own configured revision, digest, and generation, a missing record denies for a configured consumer, and an allowing `ChangeWindow` opens only when the admitted manifest owns it, so a generic or continuous snapshot cannot be blessed by this pin. A departing replica can no longer overwrite - or quarantine - a newer rollout's admission. Projection, manifest, and ontology-catalog failures now persist a denying admission inside the deployment-wide lock before returning rather than aborting startup or expiring silently. The Terraform caller moved its pinned values onto per-attribute defaults so a partial override cannot silently disable the default-on generic binding, and replacing the shipped path without its revision and digest is rejected. | [Issue #366](https://github.com/dotnetpower/fdai/issues/366); `current change`; `uv run pytest -q --no-cov services/core-control-plane/tests/core/operational_context services/core-control-plane/tests/core/risk_gate services/core-control-plane/tests/runtime services/core-control-plane/tests/delivery/operating_model tests/integration/infra/test_operating_intent_source_binding.py tests/integration/services/test_operating_intent_source_artifact.py` passed 819 cases; the wider `services/core-control-plane/tests/core`, `tests/runtime`, and `tests/shared` sweep passed 6657 cases with one unrelated `architecture_review/test_readiness.py` failure reproduced on the unmodified tree; the Terraform caller/module pass-through is exercised by a real `terraform plan` over both real variable blocks, which is what proved the plain `enabled = false` disable had to keep working; Ruff; strict mypy (six unrelated pre-existing `operator-service` findings, identical on the unmodified tree); `terraform fmt` and `terraform validate`. | Unchanged: observe one governed deployment through a real quarantine and recovery before raising any area to `validated`. |
| 2026-09-03 | implemented | Split the deployment-owned operating-intent source into this focused owner document, then made admission continuous and replica-safe. A bounded revalidation worker re-runs the identical fail-closed checks and records a self-expiring admission; `ChangeWindow` maintenance authority now resolves that admission at the decision instant rather than trusting a projected object, and a stale, missing, cross-release, or lock-unavailable source quarantines authority while preserving the projected graph. Startup manifest inspection, interrupted-apply recovery, and projection moved inside the deployment-wide resource lock on a disjoint key, so concurrently starting replicas cannot read each other's `applying` state as an interruption. | [Issue #366](https://github.com/dotnetpower/fdai/issues/366); `current change`; `uv run pytest -q --no-cov services/core-control-plane/tests/runtime/test_operating_intent_revalidation.py services/core-control-plane/tests/runtime/test_operating_intent_source.py services/core-control-plane/tests/core/operational_context/ services/core-control-plane/tests/core/risk_gate/`; `uv run pytest -q --no-cov tests/integration/infra/test_operating_intent_source_binding.py`; the concurrent-replica case was confirmed falsifiable by observing three subgraph replacements without the shared lock; Ruff; strict mypy; `terraform fmt`. | Retain one governed deployment that observes a real quarantine and recovery cycle before raising any area to `validated`. |
| 2026-09-03 | implemented | Bound the deployment-owned six-type operating-intent source to an operator-pinned exact revision, self-declared provenance, and a whole-document digest, and shipped a customer-agnostic generic source in the Core image that the Terraform caller pins by default. | [Issue #366](https://github.com/dotnetpower/fdai/issues/366); commits `d095465dc` and `d221cd09d`; focused core, runtime, delivery, and infrastructure checks. | Make admission continuous rather than startup-only, and serialize startup projection across replicas. |

### Remaining work

- [ ] Observe one governed deployment through a real quarantine and a real recovery, then record whether any area may rise from `implemented` to `validated`.
- [ ] Decide whether a future source format should carry per-object source attribution, which would let a quarantine deny only the windows that source vouched for instead of the whole maintenance surface. The admission record now enumerates owned identities, so a quarantine already denies nothing it never owned; what remains is deciding whether a *partial* quarantine of one source's own windows is meaningful.
- [ ] Decide whether `operating_intent_source.generation` should be derived from the pinned digest by the deployment pipeline instead of being an operator-maintained counter.

## Related docs

| To learn about | Read |
|----------------|------|
| The operating ontology this source populates | [operating-ontology.md](operating-ontology.md) |
| Local and deployed parity for the same env bindings | [dev-and-deploy-parity.md](../deployment/dev-and-deploy-parity.md) |
| Where the modules live | [code-map.md](code-map.md) |
