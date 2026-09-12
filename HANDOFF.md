# HANDOFF — CP03-W02

- `W02-00..W02-03` COMPLETE; `W02-05` COMPLETE with `EVID-W02-CONTROL-ATOMIC-20260909`.
- Frozen scope remains K=47 (37 owned + 10 shared); global denominator 7,565; OpenJarvis 646; VERIFIED 0.
- First executable task remains `W02-04 — Teardown y cleanup reales`.
- `W02-06` remains BLOCKED until W02-04 closes the G1 lifecycle boundary.
- W02-05 proves correlated control exchanges, poison-on-ambiguity, strict health and atomic registry replay. It does not prove inference.
- Do not merge or mutate historical PR #15; relevant behavior was ported cleanly and re-proven.

- 2026-09-12 CI support: W02-06 now explicitly depends on W02-04 as required by the G1 handoff. No task status or proof changed. Local plan/finalizer checks pass; full evidence: `sessions/20260912-plan-integrity/summary.json`. Review the support PR and require current-head hosted checks; PR #28 remains the separate W02-04 implementation candidate.
- Follow-up: historical harness-transition assertions now read the immutable wave ledger instead of requiring W02-03 to remain READY forever. 15 harness unit tests pass locally; `sessions/20260912-plan-integrity/harness-summary.json`. Current-head native harness CI still required.
