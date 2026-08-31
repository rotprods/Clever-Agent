# HANDOFF — Clever-Agent

## Handoff identity

- Project: `CLEVER-JARVIS-001`
- Iteration: `I01 — Forensic Capability Compiler`
- Completed wave: `I01-W00 — Agentic project bootstrap`
- Next wave: `I01-W01 — Reproducible upstream acquisition`
- Target branch after merge: `main`
- Global checkpoint: `CP01`

## What was established

- Stable `GOAL.md` mutation policy and multi-agent continuity invariant.
- Canonical `AGENTS.md` authority/precedence model.
- `/empezarproyecto` mandatory boot protocol.
- Mandatory `/wave` ownership and claim/lease semantics.
- `CHECKPOINTS.md` with CP01 subcheckpoints I01.0–I01.8.
- Iteration 01 plan + execution METAPROMPT.
- `STATE.md` as human live pointer, mirrored by JSON.
- Append-only run/wave/claim/decision/risk/evidence ledgers.
- Claude/Codex shims that route back to `AGENTS.md`.
- Repository validation script and CI contract workflow.

## Current truth

The JARVIS implementation itself has **not** advanced beyond CP01. No upstream capability is yet marked VERIFIED. The next task is not to design more architecture; it is to build the forensic acquisition/inventory compiler.

## Exact next action

1. Execute `/empezarproyecto`.
2. Read `iterations/01/METAPROMPT.md`.
3. Claim `I01-W01`.
4. Implement deterministic acquisition of the four pinned refs in `UPSTREAM_LEDGER.yaml` into a local ignored cache.
5. Produce committed acquisition manifests + evidence; do not vendor upstream trees.
6. Test wrong-SHA/network-failure/retry behavior.
7. Persist ledgers/state/handoff before closing the wave.

## Files to inspect first

```text
AGENTS.md
STATE.md
GOAL.md
CHECKPOINTS.md
iterations/01/ITERATION.md
iterations/01/METAPROMPT.md
UPSTREAM_LEDGER.yaml
PROTOCOLS.md
```

## Known risks

- Drift between human Markdown and machine JSON state: CI validator mitigates core fields, but future generated-state tooling should make JSON/Markdown updates atomic.
- Capability denominator inflation/under-counting: defer claims until the extraction + gauntlet pipeline exists.
- Upstream repositories are large; acquisition tooling must cache and avoid committing source mirrors.

## Blockers

None known.
