# Clever-Agent — JARVIS

`Clever-Agent` is the control plane for a real, local-first, multimodal personal AI system that unifies the capabilities of four upstream projects while preserving their strongest native runtimes.

## Start here

For any repository-capable coding agent:

1. Read `AGENTS.md`.
2. Execute `/empezarproyecto` using `commands/EMPEZARPROYECTO.md`.
3. Run `python scripts/validate_agentic_state.py`.
4. Resolve the active iteration and claim the next wave before material changes.

Current durable frontier is in `STATE.md`; never rely on this README remaining current.

## Upstream foundations

- **OpenJarvis** — local intelligence, model/engine routing, agents, memory, traces, learning, evaluation, security and scheduling.
- **OpenClaw** — gateway, sessions, channels, nodes, plugins, browser/exec tools, automation and device routing.
- **Omi** — ambient audio/screen capture, real-time transcription, diarization, episodic memory, mobile/wearable hardware and SDKs.
- **Clicky** — native macOS companion, push-to-talk, screen perception, TTS, visual pointing and cursor-overlay embodiment.

The target is not a source-code collage. `Clever-Agent` owns the contracts that make those systems behave as **one assistant**: identity, capability discovery, event semantics, goals, policy, permissions, memory, traces, state, evaluation and upstream synchronization.

## Prime directive

**Capability preservation before consolidation.** No upstream feature is considered integrated until it is inventoried, assigned a canonical capability ID, mapped to an adapter, exercised by a parity test and backed by evidence.

## Architecture direction

The target remains polyglot on purpose:

- **Rust** — new JARVIS kernel: event contracts, identity, policy broker, capability registry, goal runtime and audit core.
- **Python** — OpenJarvis cognitive runtime and Omi backend integration.
- **TypeScript / Node.js** — OpenClaw gateway/plugin ecosystem.
- **Swift** — macOS desktop embodiment and Clicky-derived interaction layer.
- **Flutter** — Omi-derived mobile clients.
- **C/C++ / Zephyr** — wearable and embedded hardware.
- **Protobuf + versioned JSON Schema** — cross-runtime contracts.

## Canonical project-control files

- `GOAL.md` — stable mission, invariants and Definition of Done.
- `AGENTS.md` — authoritative multi-agent execution contract.
- `STATE.md` — human-readable live frontier.
- `CHECKPOINTS.md` + `CHECKPOINT_REGISTRY.json` — human/machine gates.
- `HANDOFF.md` — exact continuation state.
- `PROTOCOLS.md` — waves, claims, reconciliation, gauntlet and persistence.
- `AUTOPROMPT.md` — master iteration dispatcher.
- `iterations/<id>/METAPROMPT.md` — executable iteration prompt.
- `.agentic/CONFIG.yaml` — machine-oriented development configuration.
- `UPSTREAM_LEDGER.yaml` — pinned upstream snapshots and provenance.
- `ledgers/` + `evidence/` — append-only operational truth and proof.

## Current development model

**No wave, no production.** Every material change has a wave, claim, acceptance criteria, tests/evidence and handoff. Chat is a temporary interaction surface, not project memory.
