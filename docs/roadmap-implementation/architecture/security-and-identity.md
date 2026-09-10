# Security and Identity implementation ledger

This delivery ledger preserves reviewable implementation scope, append-only transitions,
and resumable work while the roadmap owner remains focused on normative design.

## Implementation status

### Implementation scope

| Area | State | Evidence | Notes |
|------|-------|----------|-------|
| Workload identities and approval/execution separation | validated | `config/independent-service-live-evidence-manifest.json`; `infra/services/`; `shared/providers/workload_identity.py`; SD-08 and IS-09 evidence | Five-service deployment evidence proves distinct identities and makes the isolated Executor the sole eligible effect holder after cutover. |
| Executor safeguards and independent effect closure | in-progress | `packages/service-contracts/src/fdai_service_contracts/execution_safeguards.py`; `schemas/execution-safeguard-proof-bundle/1.0.0.json`; `test_execution_safeguards.py`; `core/executor/safeguards.py`; `config/constitution-traceability.json` requirement `FDAI-CONST-007`; issues `#81`, `#620`, `#627`, `#628`, and `#633` | The provider-neutral seven-proof wire bundle is implemented and grants no authority or effect-verification claim. Core and workflow producers, isolated-Executor validation, and separately authorized governed cross-path effect evidence remain open. |
| Global kill switch and break-glass controls | implemented | `core/rbac/kill_switch_command.py`; `core/control_loop/_execution.py`; `core/conversation/_write_break_glass_tool.py`; focused RBAC and control-loop tests | Revision-safe state, fail-closed refresh, authority ceiling, time-bound activation, audit, and paging paths exist. A retained operational drill remains open. |
| Automation-hold recovery approval hardening | in-progress | `core/workflow/recovery_admission.py`; `test_recovery_admission.py`; [Process Automation implementation status](../decisioning/process-automation.md#implementation-status); issues `#622` and `#630` | Exact human recovery approval admission is implemented without hold mutation or authority. Atomic evidence consumption and release-versus-new-hold fencing remain open under issue `#630`; FDAI-CONST-009 remains implemented. |
| Data protection and privacy evidence | in-progress | [Data Governance implementation status](data-governance.md#implementation-status); redaction and retention paths cited there; issue `#371` | Major boundaries now implement shared minimization and redaction, but deployment privacy approval and retained production evidence remain open. |
| Standing human authorization (A3-E) | in-progress | `config/constitution-traceability.json` requirement `FDAI-CONST-008`; [Escalation and Standing Authority](../../roadmap/decisioning/escalation-and-standing-authority.md); completed issue `#331`; issues `#621`, `#629`, `#631`, and `#632` | The schema, evaluator, immutable lifecycle, and read-time fence exist but remain unwired. Effect-spanning fencing, inert promotion review, bounded local shadow evidence, and separately authorized governed promotion remain open. |

### Implementation history

| Date | State | Change | Evidence | Remaining |
|------|-------|--------|----------|-----------|
| 2026-09-10 | implemented | Added future-request-time and process and approval-revision digest substitution regressions before closing the pure recovery-admission boundary. | `current change`; `test_recovery_admission.py`; 21 focused recovery-admission tests and 46 combined approval, recovery, and compensation checks passed. | No residual work remains for issue `#622`; complete atomic admission consumption and exact hold release under issue `#630`. |
| 2026-09-10 | implemented | Bound separately approved recovery to the existing workflow approval and decision-evidence admission contracts without releasing a hold or granting authority. | `current change`; `recovery_admission.py`; `test_recovery_admission.py`; 45 focused passing checks; Ruff and strict mypy. | Complete atomic admission consumption and exact hold release under issue `#630`. |
| 2026-09-10 | implemented | Added the provider-neutral seven-safeguard proof bundle as an immutable content-addressed wire contract with canonical proof order and false-only authority and effect flags. Service-owned mismatch, freshness, dispatch, and effect decisions remain outside the package. | `current change`; `execution_safeguards.py`; `schemas/execution-safeguard-proof-bundle/1.0.0.json`; `test_execution_safeguards.py`; 4 focused tests, Ruff, and strict mypy passed. | Emit and validate the bundle under issues `#627` and `#628`, then retain the separately authorized governed evidence under issue `#633`. |
| 2026-09-10 | in-progress | Reconciled the P0 execution-safety residual graph. Completed issue `#331` now supplies A3-E lifecycle evidence, while provider-neutral safeguard, workflow, isolated-Executor, effect-spanning lease, inert promotion, local shadow cohort, governed promotion, admitted recovery, and cross-path effect evidence have separate bounded owners. | `current change`; parent issue `#81`; completed issue `#331`; issues `#620`-`#622` and `#627`-`#633`. | Complete the child packages in dependency order, then retain separately authorized governed runtime and independent effect evidence before changing constitutional status. |
| 2026-08-29 | in-progress | Reconciled the security ledger with the shared executor safeguard contract, the completed model-bound minimization receipt, and explicit issue handoff for the remaining live drill, privacy, and A3-E evidence. | `core/executor/safeguards.py`; `tests/core/executor/test_safeguard_contract.py`; [Data Governance implementation status](data-governance.md#implementation-status); issues `#81`, `#331`, `#371`, and `#372` | Extend equivalent safeguard and independent-effect receipts to workflow and isolated-Executor paths, then retain governed live evidence. |
| 2026-08-14 | in-progress | Adopted the implementation ledger without reconstructing earlier provenance and aligned security claims with the service cutover, safeguard implementation, kill switch, privacy, and A3-E evidence boundaries. | `current change`; deployment manifests, source, focused tests, and constitutional register cited above. | Close the shared safeguard contract, operational drills, privacy gate, and standing-authorization implementation. |

### Remaining work

- [x] Define the provider-neutral seven-safeguard proof bundle under issue `#620`. Evidence: `execution_safeguards.py`, its versioned JSON Schema, and 4 focused passing contract tests.
- [ ] Emit the shared bundle from Core and workflow execution after lock and audit intent under issue `#627`.
- [ ] Revalidate the shared bundle in the isolated Executor without importing Core validators under issue `#628`.
- [ ] Retain separately authorized governed cross-path safeguard and independent effect evidence under issue `#633`.
- [x] Bind separately approved recovery through existing approval and decision-evidence contracts without mutating the hold under issue `#622`. Evidence: `recovery_admission.py`, `test_recovery_admission.py`, and 46 focused passing checks.
- [ ] Atomically consume the admitted recovery while releasing the exact hold revision and fencing a newer hold under issue `#630`; FDAI-CONST-009 remains implemented during this hardening.
- [ ] Retain governed kill-switch, break-glass, rollback, identity-recertification, and audit-anchor drill receipts on one pinned deployment revision. Tracked by issue `#372`.
- [ ] Complete the data-governance production gate before claiming privacy validation. Tracked by issue `#371`.
- [ ] Complete effect-spanning fencing, inert promotion review, bounded local shadow evidence, and separately authorized governed promotion under issues `#621`, `#629`, `#631`, and `#632`; completed issue `#331` remains the lifecycle persistence evidence.
