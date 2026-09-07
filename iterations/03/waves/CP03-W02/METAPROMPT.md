# /CP03-W02 — Evidence-bound inference implementation

Read AGENTS.md and execute /empezarproyecto. Reconcile GOAL, SECURITY_MODEL, ARCHITECTURE, parity, machine state, I03, claims, ContextPack, global task DAG and HANDOFF. Then read this folder's PLAN.md, TASK_GRAPH.json, REVIEW_FINDINGS.json, TEST_PROTOCOL.md and COS20D_REVIEW.json. Newer validated repository state outranks this plan.

Examined source: d3499fac7e098273d39244570b3f66fe8d529f56. This is provenance, NOT a reset instruction. Never discard newer work. Expected frontier: CP03-002 / CP03-W02.

## Mission

Real models/engines/inference through Rust kernel → canonical wire → sidecar → pinned OpenJarvis native engine. OpenJarvis pin 72033b8ec288aa067ce4530ff9d96bf231e9c4e5. Preserve 7565 global and 646 OpenJarvis obligations. Compile K for W02, never invent its count. This task graph only decomposes CP03-002.

## First action

Validate state/context/global DAG and `python scripts/cp03/validate_w02_plan.py`. Acquire a non-conflicting implementation claim. Start W02-00, then W02-01/02 as dependencies permit. Do not start by adding generate(), UI or another framework.

## Execute

Follow W02-00 through W02-19 dependencies. Each significant slice requires RED/characterization test, minimal fix, neighboring regression, hostile retest, evidence and persisted handoff. Use COS V2 loop and exact D00-D19 dimensions. Single writer on shared schemas/state; coordinate Rust/Python contracts before parallel edits.

Sequence: eliminate false-green tests; bound queues/writes/teardown; enforce correlation and atomic registry application; minimal inference contracts; authorize egress/budget/privacy; provision real-model lane; real unary; streaming and actual cancellation; structured/tool fragments; safe fallback; security/recovery/parity/release.

## Hard boundaries

Rust owns T0 policy/admission/identity; Python translates native behavior. Do not duplicate authorization. Clear inherited secrets, authorize destinations/cost, preserve principal/scope, redact logs.

Every request/attempt/chunk/terminal is correlated. Bound bytes/messages and deadlines, including teardown. A bounded blocking queue alone does not fix cancellation. A docker launcher exiting does not prove the container stopped. SHA declared by peer does not attest the loaded artifact: link source/image/model digests.

W01 cancel is explicitly no-op because no inference ran there. Build responsive control loop plus isolated worker. Single-flight with tested BUSY is acceptable; do not claim multiplexing until cancellation isolation is proven. ACK is not termination. No chunks after terminal. Do not claim remote cancel/billing cessation without proof.

Separate retry attempts and cumulative budget. Never splice two engines' streams or downgrade privacy. Structured output and tool-call fragments remain data: no shell/MCP/browser/tool execution in W02. Runtime liveness is not model readiness. No native-state migration or upstream rewrite.

## Proof lanes

Mocks prove adapter behavior, not real model/provider parity. Mandatory preflight fails on missing interpreter/image/weights. Empty JUnit, silent early returns and omitted required cases cannot satisfy a gate. Record executed test IDs, source/upstream/runtime/model hashes, lane and artifacts. Hardware/provider gaps remain BLOCKED/NOT_RUN, never waived by the implementation agent or counted VERIFIED.

## Milestones and close

M1 = real inference through Rust and native engine with actual weights. It does NOT close W02.
M2 = G0-G7 plus all K obligations, security/recovery and clean release evidence. Only M2 closes W02 and opens W03. If real hardware/proof is unavailable, persist exact blocker and leave the wave open rather than promoting a demo.

## Resolve

Defect→reproduce→root cause→RED→fix→GREEN→regression→hostile retest→evidence→reconcile. Refactor only when characterization tests justify it; preserve compatibility and compare same-host performance. No deleting failed evidence, relaxing thresholds after failure or claiming future work DONE.

## Finish

Persist run/claim/state/graph/evidence/handoff. Report SOURCE, CHECKPOINT, WAVE, TASK, IMPLEMENTED, EXECUTED TESTS BY LANE, STATIC VS REPRODUCED FINDINGS, GATES, K/VERIFIED DELTA, SECURITY/RECOVERY/PERFORMANCE, ARTIFACTS/COMMIT/PR and NEXT EXACT TASK. Report only persisted truth.
