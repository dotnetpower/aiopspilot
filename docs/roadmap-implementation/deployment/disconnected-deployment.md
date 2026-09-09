# Disconnected Deployment implementation ledger

This delivery ledger preserves reviewable implementation scope, append-only transitions,
and resumable work while the roadmap owner remains focused on normative design.

## Implementation status

### Implementation scope

| Area | State | Evidence | Notes |
|------|-------|----------|-------|
| Private Azure networking and VNet deploy host | implemented | `infra/`, `infra/bootstrap/`, `.github/workflows/deploy-dev.yml`, and focused infrastructure workflow tests | Private endpoints, DNS, the durable deploy host, protected plans, and exact apply are implemented independently of the offline CLI path. |
| Internal mirror and pinned-input controls | implemented | `infra/modules/preflight-toggles/` and `scripts/quality/ci/check-ci-contracts.py` | The repository exposes mirror inputs and rejects mutable or registry-bound base-image references. |
| Offline kit staging and drill harness | in-progress | `scripts/deployment/release/stage-offline-kit.sh`, `build-offline-kit.py`, `airgap-drill.sh`, and focused productization tests | The signed toolchain drill has historical validation. The explicit complete mode now requires runtime v2 and runs installed-wheel preparation without a route or DNS, but eligible current-release evidence is still open. |
| Disconnected inspection, bundle verification, and planning commands | implemented | `packages/deployment-cli`; focused artifact, profile, plan, and productization tests | The independent wheel registers `fdaictl`, verifies signed local inputs, prepares a private snapshot, and blocks public-artifact workflow dispatch for offline profiles. |
| Complete runtime release assembly | implemented | `fdai_deployment_cli.runtime_build`; `build-runtime-release.py`; focused runtime assembly tests | A digest-bound private descriptor produces runtime v2 with five FDAI services, ClamAV, Console, and deployment support. Assembly makes no production-eligibility or Azure-readiness claim. |
| Pinned offline trust root and release integration | not-started | `docs/runbooks/offline-trust-ceremony.md` | No pinned root ships in a CLI wheel and kit staging is not a passing release workflow. |
| Full-air-gap cloud operation | not-applicable | The full-air-gap boundary in this document | The deterministic core can run from static inputs, but live Azure evidence and cloud mutation are intentionally outside this profile. |

### Implementation history

| Date | State | Change | Evidence | Remaining |
|------|-------|--------|----------|-----------|
| 2026-08-14 | in-progress | Adopted the implementation ledger; earlier provenance was not reconstructed. Corrected the prior end-to-end support claim after the deployment CLI package was removed. | current change; infrastructure, release-script, package-metadata, and focused workflow evidence listed in the scope table | Restore the dedicated offline verifier and CLI, establish the trust root, and pass the air-gap drill. |
| 2026-09-09 | implemented | Reconciled the ledger with the restored independent CLI and added digest-bound runtime v2 assembly plus an explicit complete air-gap drill mode. | `current change`; runtime builder, release wrapper, complete-mode drill, focused runtime and productization checks | Run complete mode with eligible exact-revision artifacts, then retain governed signing, protected apply, state handoff, and readiness evidence. |
| 2026-09-09 | implemented | Corrected the complete staging order after real release preparation exposed that a prebuilt runtime inventory cannot know the exact deployment bundle produced by a later signing attempt. Descriptor mode now builds the signed bundle first and assembles runtime v2 against those exact bytes before outer kit signing; prebuilt mode remains supported. The same review restored the service-owned bundle-builder import path and rejects signing-key symlinks before Python revalidation. | `current change`; `stage-offline-kit.sh`, `airgap-drill.sh`, focused productization, bundle-builder import, and documentation checks | Produce eligible exact-revision image, Console, and support inputs and retain a passing complete drill. |

### Remaining work

- [x] Offline-kit and deployment-bundle verification are packaged behind the independent CLI boundary with tamper, symlink, file-set, digest, size, and compatibility tests.
- [ ] Establish and package the offline trust root through the governed ceremony, then prove inspection distinguishes verified, review, and rejected kits without a network call.
- [ ] Stage eligible runtime v2 inputs from a clean exact revision and pass `airgap-drill.sh --runtime-release <directory> --require-runtime` inside a namespace with no route or DNS.
- [ ] Prove the manual exact-plan approval and apply path from a private deploy host, including rollback, teardown, and post-provision verification receipts.
