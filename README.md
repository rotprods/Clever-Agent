# Clever-Agent — JARVIS

`Clever-Agent` is the control plane for a real, local-first, multimodal personal AI system that unifies the capabilities of four upstream projects while preserving their strongest native runtimes.

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

## Canonical control files

- `GOAL.md` — mission, invariants, non-goals and definition of done.
- `AGENTS.md` — repository execution contract for coding agents.
- `AUTOPROMPT.md` — autonomous execution metaprompt.
- `ARCHITECTURE.md` — target system architecture and runtime boundaries.
- `CAPABILITY_PARITY.md` — parity methodology and seeded capability map.
- `SECURITY_MODEL.md` — trust zones, permissions and action-risk policy.
- `UPSTREAM_LEDGER.yaml` — pinned upstream snapshots and provenance.
- `CHECKPOINT_REGISTRY.json` — canonical implementation gates.
- `GOAL_STATE.json` / `EXECUTION_STATE.json` — durable current state.
- `ROADMAP.md` — implementation sequence.

## Status

Bootstrap specification only. No upstream code is considered integrated yet.
