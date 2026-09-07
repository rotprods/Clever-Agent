# CP03-W02-CONTROL-01 — Scoped regression support

Session 2026-09-07. Base: 7feba0d207413b67f6a612e81fc16c04cc4c51da. Parent CP03-W02 remains open.

Bootstrap ownership: this branch owns new guard tests, exact-source repair recipe, read-only validation gate and scoped persistence. Before any mutation of existing production source, the repair job must validate canonical state/context, prove there are no active claims, append WORK_STARTED and an ACTIVE claim, and regenerate ContextPack. On success it releases the claim. Failed runs retain logs as artifacts without claiming completion.

Objective: replace static observations with 13 reproducible control-path regressions, fix them minimally, pass 15 control tests and retest, run existing Rust/Python regression and the real pinned OpenJarvis registry lane. No inference, model execution, platform parity, queue/lifecycle completion or W02 closure.

Scope: adapter.rs response guards and atomic registry bridge; sidecar control correlation; strict supervisor-test prerequisites; test fixtures; test-result parser; CI and evidence/task/context support. No changes to upstream pins, denominator, contracts or permissions.

Tests and code repair are performed on GitHub Actions because the local session has no Rust/Docker toolchain and GitHub DNS is unavailable. Local Python parser tests are runnable. Exact input blobs are asserted before the repair. Product code from the repair will be committed on this branch and re-tested on its exact SHA before merge.

Task ordering: W02-00/02 are the primary runnable work. W02-05 receives partial support evidence only; it cannot close before W02-03. Next: W02-01 obligation compiler and W02-03 bounded I/O. G1, M1 and M2 are explicitly NOT complete.
