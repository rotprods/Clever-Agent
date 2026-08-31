# STATE — Clever-Agent live pointer

> Human-readable mutable pointer. Machine mirrors: `GOAL_STATE.json`, `EXECUTION_STATE.json`, `iterations/01/STATE.json`. Evidence/Git outrank this file if drift is detected.

## Current

- Goal: `CLEVER-JARVIS-001`
- Global status: `IN_PROGRESS`
- Active checkpoint: `CP01 — Forensic upstream inventory`
- Active iteration: `I01 — Forensic Capability Compiler`
- Completed iteration gates: `I01.0 — Agentic repository bootstrap`, `I01.1 — Pinned upstream acquisition`
- Next executable wave: `I01-W02 — Structural inventory`
- Parity: `0 verified / denominator not generated`
- Blocking issues: none known

## Canonical frontier

Finish validation/persistence of `I01-W02`, then execute `I01-W03 — Public/behavioral surface extraction` from `iterations/01/METAPROMPT.md`.

The CP01 compiler now has two distinct evidence layers:

1. complete pinned Git-tree structural inventory;
2. sparse-source Graphify/COS semantic projection.

Do **not** treat raw Graphify symbol counts or provisional COS groups as the capability denominator. Do **not** implement final Rust kernel contracts before W03/W04 produce evidence-backed behavioral surfaces and canonical capability rows.

## Persistence health

- Stable goal: present
- Global checkpoint registry: present
- Human checkpoint map: present
- Agent execution contract: present
- Project boot command: present
- Iteration metaprompt: present
- Wave/claim/run ledgers: active
- Evidence ledger: active
- Capability ledger: initialized, denominator pending
- Handoff: reconciled through W01
- W01 exact-SHA acquisition + full four-upstream forensic scan: PASS (`EVID-0002`, GitHub Actions run `33402789051`)
- Graphify/COS contract: PASS (`EVID-0003`, GitHub Actions run `33402789018`)
- Agentic Contract at W01 validated head: PASS (run `33402788994`)

## Last structural decisions

- Acquire upstreams as partial Git object stores with immutable local pin refs; materialize source-only sparse worktrees only when source content is needed.
- `/graphify` is the evidence projection backend; `/cosgraphengine` is a non-destructive integration overlay.
- Raw source/symbol graph nodes remain evidence candidates. Only W03/W04 may promote evidence-backed behavioral surfaces into the capability denominator.

## Next expected durable outputs

1. `inventory/upstreams/{openjarvis,openclaw,omi,clicky}.json` from complete pinned Git trees.
2. W02 structural inventory evidence and deterministic rerun proof.
3. `I01-W03` extractors for routes, commands, registries, extension points, agents, providers, channels, persistence, media/device/security surfaces and tests.
4. `I01-W04` canonical capability rows with provenance-preserving deduplication.
5. Baseline, license and completeness-gauntlet evidence required before CP01 can close.

## Recovery instruction

A fresh agent should not ask for chat context. Run `/empezarproyecto`, read `HANDOFF.md`, validate state, inspect W02 CI evidence, claim the next non-conflicting wave and continue from persisted evidence.
