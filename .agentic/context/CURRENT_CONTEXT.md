# CURRENT CONTEXT — Clever-Agent

> Deterministic derived recovery view. It is never a primary source of truth; Git, canonical state and evidence outrank it.

## Frontier

- Project: `CLEVER-JARVIS-001`
- Checkpoint: `CP03`
- Iteration: `I03` / `I03.1`
- Next wave: `CP03-W01 — Transport lifecycle and registry bridge`
- Parity denominator: `GENERATED_UNVERIFIED`
- Protocol: `COS-GRAPH-ENGINE-V2-20D`
- 20D model: `COS-20D-v2` (20 dimensions)

## Planning

- First executable task: `CP03-001`
- Active iteration state: `iterations/03/STATE.json`
- Machine task graph: `.agentic/context/NEXT_ACTIONS.json`
- Implementation plan: `IMPLEMENTATION_PLAN.md`
- Regression: `docs/REGRESSION_2026-08-31.md`
- Acta de consciencia: `docs/ACTA_DE_CONSCIENCIA.md`

## Hard invariants

- `chat_is_authority` = `false`
- `raw_graph_is_not_parity_denominator` = `true`
- `candidate_is_not_capability` = `true`
- `source_graph_is_immutable` = `true`
- `cos_decisions_are_provisional_until_promoted` = `true`
- `automatic_destructive_merge_forbidden` = `true`
- `migration_requires_behavioral_equivalence_evidence` = `true`
- `context_pack_is_derived_not_primary_truth` = `true`
- `max_context_loss_interactions` = `1`

## Active claims


## Open / mitigating risks

- `RISK-0001` · `MEDIUM` · `OPEN` · detail in `ledgers/RISK_LEDGER.ndjson`
- `RISK-0002` · `HIGH` · `OPEN` · detail in `ledgers/RISK_LEDGER.ndjson`
- `RISK-0003` · `HIGH` · `OPEN` · detail in `ledgers/RISK_LEDGER.ndjson`

## Recovery order

1. `GOAL.md`
2. `SECURITY_MODEL.md`
3. `AGENTS.md`
4. `ARCHITECTURE.md`
5. `CAPABILITY_PARITY.md`
6. `docs/ACTA_DE_CONSCIENCIA.md`
7. `docs/COS_GRAPH_ENGINE_V2.md`
8. `docs/GRAPH_ENGINEERING_PROTOCOL.md`
9. `CHECKPOINT_REGISTRY.json`
10. `STATE.md`
11. `GOAL_STATE.json`
12. `EXECUTION_STATE.json`
13. `iterations/03/STATE.json`
14. `IMPLEMENTATION_PLAN.md`
15. `TASKS.md`
16. `.agentic/context/NEXT_ACTIONS.json`
17. `.agentic/context/CURRENT_CONTEXT.json`
18. `HANDOFF.md`

## Resume

- `python scripts/validate_agentic_state.py`
- `python scripts/context/validate_context_pack.py`
- `python scripts/context/build_context_pack.py --check`
- `python scripts/context/validate_next_actions.py`
- `/empezarproyecto`
