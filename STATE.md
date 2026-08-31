# STATE — Clever-Agent live pointer

> Human-readable mutable pointer. Machine mirrors: `GOAL_STATE.json`, `EXECUTION_STATE.json`, `iterations/01/STATE.json`. Evidence/Git outrank this file if drift is detected.

## Current

- Goal: `CLEVER-JARVIS-001`
- Global status: `IN_PROGRESS`
- Active checkpoint: `CP01 — Forensic upstream inventory`
- Active iteration: `I01 — Forensic Capability Compiler`
- Completed iteration gate: `I01.0 — Agentic repository bootstrap`
- Next executable wave: `I01-W01 — Reproducible upstream acquisition`
- Parity: `0 verified / denominator not generated`
- Blocking issues: none known

## Canonical frontier

Execute `/empezarproyecto`, reconcile repository state, then implement `I01-W01` from `iterations/01/METAPROMPT.md`.

Do **not** implement final Rust kernel contracts before the CP01 capability denominator is evidence-backed.

## Persistence health

- Stable goal: present
- Global checkpoint registry: present
- Human checkpoint map: present
- Agent execution contract: present
- Project boot command: present
- Iteration metaprompt: present
- Wave/claim/run ledgers: initialized
- Evidence ledger: initialized
- Capability ledger: initialized, denominator pending
- Handoff: initialized
- Agentic Contract validation: PASS (`EVID-0001`, GitHub Actions run `33398327837`)

## Last structural decision

Adopt a wave-based multi-agent development protocol with `AGENTS.md` as execution authority, stable goal contracts, mutable state pointers and append-only ledgers/evidence.

## Next expected durable outputs

1. `scripts/upstream/*` acquisition tooling.
2. `inventory/upstreams/*.json` source manifests.
3. `evidence/cp01/acquisition/*` pin verification.
4. First generated source inventory schema/tests.
5. Updated run/wave/decision/risk/evidence ledgers.

## Recovery instruction

A fresh agent should not ask for chat context. Run `/empezarproyecto`, read `HANDOFF.md`, validate state, claim the next non-conflicting wave and continue from persisted evidence.
