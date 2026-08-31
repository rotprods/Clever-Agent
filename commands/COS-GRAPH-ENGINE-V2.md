# `/cos-graph-engineV2` — canonical graph-governed execution loop

## Intent

Operate one claimed wave using source evidence, Graphify V2, COS-20L runtime placement, COS-20D decision analysis, adversarial verification and durable context persistence.

## Mandatory invariants

- P0 source/evidence truth is immutable from higher graph planes.
- Raw graph nodes are not capability rows.
- Graphify V2 surfaces begin as `DISCOVERED_CANDIDATE`.
- COS decisions are `PROVISIONAL` until evidence promotes them.
- `CANONICALIZE` and `MERGE_STATE` never authorize code/state deletion.
- Destructive convergence requires `MIGRATION_ELIGIBLE`.
- Every decision retains source provenance and promotion requirements.
- ContextPack is derived; Git/state/evidence outrank it.

## Loop

`BOOT_RECONCILE → OBSERVE → GRAPHIFY → MODEL → CROSS_LINK → PROJECT_20D → DECIDE → PLAN_COMPILE → IMPLEMENT → VERIFY → GAUNTLET → EVIDENCE → PERSIST → AUTOPROMPT_REFLECT → COMMIT_RECONCILE`

## Required per-wave outputs

```text
graph_inputs
graph_delta
20D_dimensions_touched
provisional_decisions
promotion_delta
tests/evidence
risk_delta
state/context delta
exact next frontier
```

See `docs/COS_GRAPH_ENGINE_V2.md` and `docs/GRAPH_ENGINEERING_PROTOCOL.md`.
