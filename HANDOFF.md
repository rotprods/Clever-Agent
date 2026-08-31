# HANDOFF — Clever-Agent

## Identity

- Project: `CLEVER-JARVIS-001`
- Global checkpoint: `CP01 — Forensic upstream inventory`
- Iteration: `I01 — Forensic Capability Compiler`
- Completed subcheckpoints: `I01.0`, `I01.1`, `I01.2`
- Active subcheckpoint/wave: `I01.3 / I01-W03 — Public/behavioral surface extraction`
- First executable task: `W03-001 — Behavioral surface schema`
- Capability denominator: `NOT_GENERATED`
- PR: `#4` (draft while CP01 work continues)

## Consciousness / recovery entrypoint

Read in this order after the mandatory authority files:

1. `docs/ACTA_DE_CONSCIENCIA.md`
2. `docs/REGRESSION_2026-08-31.md`
3. `IMPLEMENTATION_PLAN.md`
4. `TASKS.md`
5. `.agentic/context/NEXT_ACTIONS.json`
6. `.agentic/context/CURRENT_CONTEXT.json`

The machine task DAG determines the executable frontier. ContextPack is derived, not primary truth.

## What has been proven

### W01 — exact source truth

Full forensic run `33402789051` / job `99522924366` succeeded across all four exact upstream pins. Artifact `9762075538`, digest `sha256:f09dbec5fd39dbb97c56e8a3c986602a6b260adefb49f34a08aed791fc8fe6bc`.

Raw Graphify/COS pass: 1,179,885 evidence nodes, 1,181,257 edges, 139 provisional components, 110 cross-repo provisional components. These are evidence/candidates, not capability counts.

### Context/COS V2 integrity

Agentic Contract `33429197911` and Graphify/COS `33429197696` passed on `8dded838...` after the regression fixes. ContextPack is ledger-backed, orphan-ID checked, deterministic and linked to an executable acyclic task DAG.

### W02 — complete structural census

Structural run `33429197669`, job `99610115447`, succeeded against source head `8dded8384ae113e7a9c73b21691c33a529696b60`.

Artifact `9771912520`, digest `sha256:71dc9e002a8874cffdb63440c9fdd0d4042ceb623ec7927b214e6a4ae0a94221`.

Totals:

- 50,681 tree entries;
- 390 manifests;
- 17,651 test files;
- 615 runtime/service/app boundaries.

Per source:

| Source | Tree | Manifests | Tests | Runtime boundaries |
|---|---:|---:|---:|---:|
| OpenClaw | 35,757 | 213 | 13,613 | 362 |
| Omi | 12,731 | 141 | 3,314 | 198 |
| OpenJarvis | 2,108 | 32 | 724 | 51 |
| Clicky | 85 | 4 | 0 | 4 |

The previous 20-minute W02 timeout was traced to `git ls-tree -l` resolving blob sizes in `blob:none` partial clones. The scanner now uses tree metadata only and the risk is closed.

## Current architecture doctrine

Four one-way planes:

`P0 SOURCE_EVIDENCE → P1 SEMANTIC_SURFACE → P2 COS20D_DECISION → P3 AGENT_CONTEXT`.

20L answers *where runtime responsibility executes*. 20D answers *what must be understood/proven before change*. Neither grants migration authority.

Promotion ladder:

`OBSERVED_SOURCE → DISCOVERED_CANDIDATE → BEHAVIOR_MAPPED → CONTRACT_MAPPED → TEST_MAPPED → VERIFIED → MIGRATION_ELIGIBLE`.

Destructive convergence before `MIGRATION_ELIGIBLE` is forbidden.

## Exact next action

Run:

```bash
python scripts/validate_agentic_state.py
python scripts/context/validate_next_actions.py
python scripts/context/validate_context_pack.py
python scripts/context/build_context_pack.py --check
```

Then execute `/empezarproyecto`, claim `I01-W03`, and implement `W03-001`.

### W03-001 output

Freeze `inventory/schemas/behavioral_surface.schema.json` and evidence-strength/promotion semantics.

Required fields include source provenance, family/kind, runtime owner, source path/symbol/route/key, registration/protocol evidence, permissions, state effects, lifecycle, failure semantics, platform constraints, evidence strength and promotion status.

### After W03-001

Parallelize four disjoint lanes:

- `W03-002`: OpenJarvis typed registries/registrations + runtime surfaces.
- `W03-003`: OpenClaw contribution/lifecycle/gateway/session surfaces.
- `W03-004`: Omi routes/listen/perception/state/device/reconciliation surfaces.
- `W03-005`: Clicky native PTT/screen/TTS/overlay/pointing/proxy surfaces.

Merge later without behavior deduplication, then run completeness gauntlet.

## Open risks

- `RISK-0001`: human/machine state mirror drift.
- `RISK-0002`: dynamic/plugin/platform-gated capability undercount.
- `RISK-0003`: lexical/raw symbol inflation and false overlap.

## Hard stops

- W03 surface extraction does not mark Clever capabilities VERIFIED.
- W04 denominator cannot start before W03 completeness evidence.
- CP02 kernel contracts cannot start before CP01 closes.
- Provisional COS decisions cannot execute migration/state removal.
