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
objective. Configuration and durable admission records accept only `sha256:` followed by 64
lowercase hexadecimal characters.

The pin is only as honest as the parser under it. The intent-source parser therefore rejects any
member it does not recognize - at the document, `provenance`, object, and link level - so every
accepted member is covered by the digest. A tolerant parser would have discarded an added member
before hashing, leaving the pinned digest unchanged while the file on disk changed. The generic
`FDAI_OPERATING_MODEL_PATH` format stays tolerant, because it advertises no pin.
The dedicated source accepts only the six operating-intent ObjectTypes; any other type rejects the
whole document instead of expanding this source's graph ownership.
The adapter reads no more than `max_bytes + 1` bytes from one open file handle, so a replacement or
growth between a metadata check and content read cannot bypass the configured size bound.
JSON object keys must also be unique; a duplicate key cannot be collapsed before canonical hashing.

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
rewriting the graph. Durable denial records use fixed reason codes; untrusted exception text, paths,
and object identities are not persisted or logged.

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
too. Revalidation reuses a projected manifest only when its exact object-id and link-key inventories
still match the pinned document; a same-digest manifest with altered ownership quarantines instead.

Without it, a replica starting beside another reads its peer's in-flight `applying` manifest as an
interrupted apply and deletes the subgraph the peer is still writing. A lock that cannot be acquired
records `unavailable` and projects nothing, so an unreachable lock backend fails closed instead of
racing.
## Related docs

| To learn about | Read |
|----------------|------|
| Delivery status and remaining work | [Implementation ledger](../../roadmap-implementation/architecture/operating-intent-source.md) |
| The operating ontology this source populates | [operating-ontology.md](operating-ontology.md) |
| Local and deployed parity for the same env bindings | [dev-and-deploy-parity.md](../deployment/dev-and-deploy-parity.md) |
| Where the modules live | [code-map.md](code-map.md) |
