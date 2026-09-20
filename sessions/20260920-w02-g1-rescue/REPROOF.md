# CP03-W02 G1 rescue reproof

- Date: 2026-09-20
- Parent checkpoint: CP03-W02
- Rescue PR: #38
- Product milestone: W02-04 + G1 reconciliation only
- Product donor: `3885ba717cba450fd7283eb45a9e43b09b26b1a0`
- Base main: `f7f30badc9f1852c6f42117c528f9f32dad74bd7`
- Frozen W02 proof units: K=47
- Global denominator: 7565
- OpenJarvis obligations: 646
- Parity VERIFIED before reproof: 0

Purpose: create a non-`[skip ci]` exact PR head so GitHub re-executes all path-relevant read-only G1 gates. This file makes no product, contract, denominator or parity mutation.

Required reproof families:
- Agentic Contract
- W02 Plan Integrity
- W02 Scope Lock
- W02 Harness Integrity including pinned native OpenJarvis
- W02 IO Backpressure
- W02 Correlation Registry
- W02 Teardown Cleanup

Merge is forbidden unless the new head is green and W02-06 remains the first executable task.
