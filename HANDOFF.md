# HANDOFF — Clever-Agent

- Checkpoint: `CP03`
- Iteration: `I03`
- Completed implementation: `CP03-001` / `CP03-W01`
- Implementation evidence: `EVID-0014`
- Next canonical task: `CP03-002` / `CP03-W02`
- Planning support: `CP03-W02-PLAN-01` (2026-09-07), based on `d3499fac7e098273d39244570b3f66fe8d529f56`.

Run `/empezarproyecto`, validate state/context, then read `iterations/03/waves/CP03-W02/PLAN.md` and its `METAPROMPT.md`. The subordinate `TASK_GRAPH.json` starts at `W02-00`; no W02 implementation task is complete yet.

First implementation focus: preflight, obligation selection and false-green test harness, followed by bounded I/O/lifecycle, request correlation and atomic registry application. Static findings are recorded in `REVIEW_FINDINGS.json`; they are not new exploit reproductions or already-applied fixes.

The plan separates G3 first real inference from G7 full W02 completion. Missing real-model or platform evidence keeps the affected gate/wave open. Preserve 7565 global obligations, 646 OpenJarvis obligations and zero VERIFIED until actual behavioral gates produce valid evidence.

Planning tests: `python -m unittest discover -s tests -p 'test_cp03_w02_plan.py' -v`; `python scripts/cp03/validate_w02_plan.py`. These do not execute inference. Global state/ContextPack remain authoritative and unchanged by this planning package.
