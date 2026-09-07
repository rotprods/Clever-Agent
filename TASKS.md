# TASKS — CLEVER-JARVIS-001 executable backlog

Machine authority: `.agentic/context/NEXT_ACTIONS.json`.

## CP03

- [x] **CP03-000 / CP03-W00 — Run hermetic pinned OpenJarvis baseline and classify gated tests.** Status: `COMPLETE`.
- [x] **CP03-001 / CP03-W01 — Implement supervised adapter transport, lifecycle and typed registry bridge.** Status: `COMPLETE`.
- [ ] **CP03-002 / CP03-W02 — Map models, engines and inference behavior through canonical contracts.** Status: `READY`.
- [ ] **CP03-003 / CP03-W03 — Map agents, tools and MCP while enforcing Clever action authority.** Status: `BLOCKED`.
- [ ] **CP03-004 / CP03-W04 — Map memory/retrieval with principal-scoped ownership and provenance.** Status: `BLOCKED`.
- [ ] **CP03-005 / CP03-W05 — Map traces, telemetry, evals and proposal-only learning signals.** Status: `BLOCKED`.
- [ ] **CP03-006 / CP03-W06 — Map scheduler/proactive/persistent operative semantics with replay safety.** Status: `BLOCKED`.
- [ ] **CP03-007 / CP03-W07 — Reconcile OpenJarvis defense-in-depth security under Clever T0 policy.** Status: `BLOCKED`.
- [ ] **CP03-008 / CP03-W08 — Compile and burn down parity for all 646 OpenJarvis obligations.** Status: `BLOCKED`.
- [ ] **CP03-009 / CP03-W09 — Run adversarial recovery and performance gauntlet.** Status: `BLOCKED`.
- [ ] **CP03-010 / CP03-W10 — Reconcile CP03 release evidence and hand off to CP04.** Status: `BLOCKED`.

## CP03-002 implementation decomposition

Read `iterations/03/waves/CP03-W02/PLAN.md`, `TASK_GRAPH.json`, `REVIEW_FINDINGS.json`, `TEST_PROTOCOL.md`, `COS20D_REVIEW.json` and `METAPROMPT.md` before W02 implementation. The subordinate graph has 20 tasks and eight gates; first task is `W02-00`. It does not replace the global DAG. A first real inference (G3) does not close W02 (G7).

Planning validation: `python scripts/cp03/validate_w02_plan.py` and `python -m unittest discover -s tests -p 'test_cp03_w02_plan.py' -v`. These tests certify plan integrity only; no inference parity is promoted.
