# CP03 W02 G1 — Independent Architecture / Security / QA Review

**Review ID:** `CP03-W02-G1-REVIEW-20260914`  
**Candidate:** `3885ba717cba450fd7283eb45a9e43b09b26b1a0` (PR #28 convergence candidate)  
**Main reviewed:** `f7f30badc9f1852c6f42117c528f9f32dad74bd7`  
**Upstream OpenJarvis pin:** `72033b8ec288aa067ce4530ff9d96bf231e9c4e5`

## Review boundary

This branch is an independent review overlay. It does not change the candidate implementation.
It adds tests, a read-only E2E workflow, findings, and recovery evidence only.

Reviewed surfaces:
- `ARCHITECTURE.md`
- `SECURITY_MODEL.md`
- CP03/W02 task graph and evidence transitions
- Rust adapter supervisor / capability registry / lifecycle
- OpenJarvis Python sidecar
- PR #28, PR #29, and historical PR #15
- decision/risk ledgers
- GitHub workflow supply-chain pinning
- repository branch/ruleset governance

## Executive result

**Recommendation: CONDITIONAL BLOCK.**

The candidate is materially stronger than `main`: it combines W02-03 bounded I/O,
W02-05 strict correlation/atomic registry, W02-04 bounded lifecycle/cleanup, and the
sidecar correlation fix needed by the strict supervisor. However, merge authority
must wait for exact-head independent E2E evidence.

### Blocking merge conditions
1. Independent current-head review gauntlet passes.
2. Exact pinned OpenJarvis native path passes strict handshake/snapshot/health/shutdown.
3. No regression in K=47 / denominator=7,565 / OpenJarvis=646 / VERIFIED=0.
4. PR convergence is explicit: PR #29 must not later be merged again if PR #28 is chosen.

### External release blocker
`main` is not protected and no repository rulesets are present. This is an administrative
security blocker for production/privileged release, even if the code candidate passes.

## Code review

### Strong
- `sync_channel` plus `try_send` bounds queued frames.
- raw wire-byte budget is reserved before protobuf decode.
- writer completion uses a timeout and poisons the session on ambiguity.
- control exchanges centralize correlation validation.
- registry application is staged through `register_batch`.
- shutdown no longer calls an unbounded `child.wait()`.
- process group and cleanup hooks give the supervisor a path to kill descendants/external workloads.

### Finding — lifecycle completion is over-asserted
`terminate_bounded()` deliberately prioritizes non-blocking teardown but discards several
kill/cleanup/join results and then sets `termination_complete=true`.

That is enough to prove "Drop does not hang"; it is not sufficient to prove
"the entire external workload was successfully removed" under all failure modes.

Before container/daemon cleanup is relied upon, emit a structured termination report or
otherwise surface cleanup failure distinctly.

## Security review

- T0/T1 trust split remains coherent.
- environment inheritance is cleared.
- privilege-bearing registry metadata is filtered.
- exact upstream pin is preserved.
- no parity promotion occurs.

### Findings
- `stderr(Stdio::inherit())` is unbounded and unredacted. It must be remediated before
  provider credentials or sensitive inference payloads reach the adapter.
- Unix process-group semantics are not portable; non-Unix support needs an explicit
  constraint or native equivalent.
- branch protection/rulesets are absent and cannot be repaired by this review branch.

## Supply-chain review

The corrected workflow inventory found **51 external action uses across 20 of 36 workflows pinned to mutable tags**
such as `@v4`, `@v5` and `buf...@v1`. This is a real supply-chain finding, not a review
harness defect. The review records it as `SUPPLY-P1-UNPINNED-ACTIONS`.

The original review scanner only matched compact `- uses:` syntax and missed the common
`uses:` child of a named step. The corrected scanner covers both forms. This finding
blocks production/release hardening until those uses are replaced with audited 40-hex
commit SHAs. It does not by itself invalidate the Rust G1 behavior under review.

## QA / recovery review

The candidate contains evidence for W02-03, W02-04 and W02-05, but the final convergence
SHA itself had no associated hosted workflow run when this review began. D-0010 requires
evidence tied to the exact candidate.

The review workflow therefore re-runs:
- state/context/next-action/parity validators;
- review invariant tests;
- Python sidecar/planning/harness tests;
- Rust kernel/security/action/control/lifecycle suites;
- W02-03 adversarial I/O regressions;
- exact pinned OpenJarvis native handshake → registry snapshot → health → shutdown.

## PR convergence

Recommended sequence if the gauntlet is green:
1. Keep PR #28 as the convergence candidate.
2. Record PR #29 fixes as donors already present in PR #28; close PR #29 as superseded.
3. Record PR #15 as superseded by W02-05 evidence; never merge it mechanically.
4. Merge PR #28 only after exact-head evidence exists.
5. Open W02-06 from the merged convergence state.
6. Keep production/release blocked until branch protection/ruleset policy is enabled.

## Next architecture frontier

After G1 converges, W02-06 should define typed inference contracts.
It must not start real provider/model execution until W02-07 privacy/egress/budget controls
exist, and real model evidence remains distinct from mocks.
