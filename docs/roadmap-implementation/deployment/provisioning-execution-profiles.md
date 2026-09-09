# Provisioning Execution Profiles implementation ledger

This delivery ledger preserves reviewable implementation scope, append-only transitions,
and resumable work while the roadmap owner remains focused on normative design.

## Implementation status

### Implementation scope

| Area | State | Evidence | Notes |
|------|-------|----------|-------|
| Read-only inspection and profile initialization commands | implemented | `packages/deployment-cli`; focused profile, target, inspection, and productization tests | The dedicated wheel registers `fdaictl`, persists private target-bound profiles, and keeps execution-host readiness at review until external evidence exists. |
| Managed VM, private backend, and protected runner | implemented | `infra/bootstrap/`, `.github/workflows/deploy-dev.yml`, and focused bootstrap and workflow tests | The durable VNet host, workload identity, private state, protected plan, and exact-apply mechanics exist without the local CLI facade. |
| Offline-kit construction and verification | validated | `fdai_deployment_cli.offline_kit`; locked release scripts; historical shipped-wheel network-isolated drill | Signature-first verification, exact files, SBOM coverage, ABI/libc binding, private snapshots, and installed-wheel use passed for the recorded revision. Complete current runtime-release evidence remains separate. |
| Temporary public-access cleanup | not-started | The access preference contract in this document | No composed command proves bounded creation, automatic cleanup, incomplete-on-cleanup-failure behavior, and audit closure. |
| Pinned TUF root and rotation | not-started | `docs/runbooks/offline-trust-ceremony.md` | The first root ceremony, package resource, client bootstrap, and rotation evidence remain open. |
| Post-provision verification | in-progress | Protected workflow checks and `docs/roadmap/operations/operating-and-verification.md` | Runner-side convergence, migrations, health, and canary checks exist; the complete CLI-driven lifecycle and disconnected receipt do not. |

### Implementation history

| Date | State | Change | Evidence | Remaining |
|------|-------|--------|----------|-----------|
| 2026-08-14 | in-progress | Adopted the implementation ledger; earlier provenance was not reconstructed. Corrected inspection, profile persistence, and offline verification from implemented to their evidence-backed current states. | current change; package metadata, bootstrap source, release scripts, and focused workflow checks listed in the scope table | Create the CLI package, restore offline verification, complete trust bootstrap, and validate the full lifecycle. |
| 2026-09-09 | implemented | Reconciled obsolete missing-package claims with the independent CLI, private profile, and restored offline verifier currently in source. | `current change`; package source plus focused profile, artifact, productization, and runtime release checks | Complete temporary-access cleanup, trust-root bootstrap, protected application execution, and governed lifecycle evidence. |
| 2026-09-09 | implemented | Bound descriptor-driven runtime v2 assembly to the exact signed deployment bundle generated inside kit staging while preserving already-matching prebuilt runtime input. | `current change`; release staging, complete air-gap argument contracts, and focused productization checks | Retain an eligible descriptor-driven complete drill and the governed lifecycle receipt. |

### Remaining work

- [x] `provision inspect` and `provision init` are in the dedicated CLI package with no-mutation, private-mode, overwrite, symlink, target-binding, and stable-JSON tests.
- [x] Offline-kit verification uses an injected release root and passes signature-before-parse, exact-file-set, no-follow digest, compatibility, and bounds tests.
- [ ] Implement temporary public-access creation and cleanup so cleanup failure leaves an incomplete audited operation, then pass CIDR, duration, authentication, rollback, and idempotency tests.
- [ ] Complete the TUF root ceremony and package bootstrap, then retain a governed inspect-to-plan-to-apply-to-cleanup-to-verification receipt.
