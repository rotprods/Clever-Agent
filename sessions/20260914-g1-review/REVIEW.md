# CP03-W02 G1 — code, security and QA review

Date: 2026-09-14  
Repository: `rotprods/Clever-Agent`  
Target reviewed: PR #28, `wave/cp03/w02-teardown-cleanup` at `3885ba717cba450fd7283eb45a9e43b09b26b1a0`  
Base: `main` at `f7f30badc9f1852c6f42117c528f9f32dad74bd7`

## Decision

**CHANGES REQUIRED / release gate BLOCKED.** The Python, state, evidence-linkage and changed-workflow lanes pass, but the exact PR head has no GitHub workflow runs or commit statuses and this runner has no Cargo toolchain. The Rust lifecycle and Clippy lane therefore remains unverified at this head. No parity promotion is authorized.

## Code review

- The control-response repair is coherent: requests get unique kernel frame IDs and every sidecar response now returns that request ID in `correlation_id`.
- The lifecycle design is bounded: Unix child process groups are isolated, shutdown/drop force the group, cleanup commands require absolute programs, inherit an empty environment and have time budgets.
- The mutable workflow paths use exact-branch gates, mutation allowlists and compare-and-swap checks before push.
- No new correctness or injection defect was found in the reviewed PR #28 diff. Rust approval remains blocked by missing executable proof, not by a known source-level defect.

## QA review and repairs

The full Python suite originally exposed five false-red failures across three isolation defects. This review repaired them without weakening assertions:

1. the Xcode supply-chain test now scans a temporary fixture root instead of the repository root;
2. the historical CP02 release test validates its persisted CP02 evidence, while a new test proves that rerunning the evaluator at CP03 fails closed;
3. W02 scope compiler tests generate outputs inside temporary roots instead of requiring deliberately untracked build products.

Current result after reconciling the independent review overlay: **238 tests run, 238 pass**. The added release gauntlet also verifies canonical state, ContextPack determinism, next actions, W02 plan, parity invariants, G1 evidence linkage, critical Python regressions and changed-workflow security.

Strict gauntlet result: **BLOCKED**, as designed, because Cargo is unavailable. Diagnostic result: `PASS_WITH_RUST_BLOCKED`; that value is not a release approval.

## Security review

### PR #28 scope

- PASS: 7/7 external action references in the two changed workflows are pinned to full commit SHAs.
- PASS: no `pull_request_target`, writable manual dispatch or curl-to-shell path.
- PASS: write jobs use branch-specific CAS guards and explicit mutation allowlists.
- Residual risk: workflow code can self-commit to its branch. The branch restriction and CAS reduce race/scope risk, but branch protection remains the repository-level control.

### Repository-wide backlog

- **HIGH — supply-chain pinning:** 20 of 36 workflows contain 51 action references pinned only to mutable tags such as `@v4`, `@v5` or `@v1`.
- **MEDIUM — write surface:** 19 of 36 workflows request `contents: write`. Each should be reduced to job scope and audited for event gating, path allowlists and CAS persistence.
- These are pre-existing, repository-wide findings. They should be handled in a dedicated hardening wave rather than silently expanding PR #28.

## Architecture and state invariants

- Canonical frontier remains `CP03 / I03 / W02-06`.
- G1 evidence proves bounded transport, correlation, atomic registry application and bounded teardown; it does not prove inference.
- Frozen scope remains K=47 (37 owned + 10 shared), global denominator 7,565, OpenJarvis obligations 646 and VERIFIED 0.
- PR #29 remains a donor/repair draft; PR #15 remains an older draft. Neither supersedes PR #28 automatically.

## Merge requirements

1. Run the strict gauntlet with Cargo available on the exact review head.
2. Obtain passing `rustfmt`, lifecycle legacy, adapter lifecycle, control regressions and workspace Clippy results.
3. Publish those results as immutable CI evidence or commit checks attached to the exact SHA.
4. Keep parity promotions at zero and preserve `W02-06` as the next product frontier.
