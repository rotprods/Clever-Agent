# Execution Roadmap

This roadmap mirrors `CHECKPOINT_REGISTRY.json`; the JSON registry is authoritative for checkpoint status.

## CP00 — Canonical bootstrap

Establish goal, invariants, source pins, architecture, parity methodology, security model, durable state and execution prompt.

## CP01 — Forensic upstream inventory

Deliverables:

- reproducible source acquisition at exact SHAs
- repository/package/runtime manifests
- generated capability ledger
- test/build/release inventory
- provider/channel/plugin/skill/device command inventory
- license/NOTICE inventory
- upstream baseline test evidence
- dependency/capability graph

No kernel implementation is allowed to outrun the inventory enough to force architectural guesses.

## CP02 — Contracts + kernel

Build versioned Protobuf/JSON Schema contracts and a Rust kernel skeleton for identity, sessions, events, capability discovery, goals, policy decisions, action idempotency, audit and health.

Generate bindings for Rust/Python/TypeScript/Swift; add version-skew and round-trip tests.

## CP03–CP06 — Four upstream vertical integrations

Run in parallel only where contracts are stable and file ownership does not conflict:

- CP03 OpenJarvis cognition
- CP04 OpenClaw gateway/ecosystem
- CP05 Omi ambient/mobile/wearable
- CP06 Clicky macOS embodiment

Each checkpoint closes only through parity evidence, not adapter compilation.

## CP07 — Canonical state convergence

Unify identity, sessions, events and memory. Migrate duplicated state gradually and prove no behavior regression.

## CP08 — Policy/action plane

Put browser, exec, device, messaging and future computer-control side effects behind risk classification, scoped authorization, idempotency, verification and audit.

## CP09 — Cross-device continuity

Prove the same goal and memory can move among desktop, mobile/wearable nodes and messaging channels with deterministic conflict handling.

## CP10 — Learning + proactive autonomy

Connect OpenJarvis traces/learning to canonical traces and goals. Add promotion gates for prompt/skill/router updates. Implement proactive monitoring and planning with notification policy.

## CP11 — Full parity + drift synchronization

Generate the authoritative parity report. Add scheduled upstream comparison that discovers newly added/changed capabilities and creates a structured delta instead of silently drifting.

## CP12 — Production release

Hardening gates:

- E2E acceptance suite
- adversarial security suite
- crash/restart/recovery drills
- provider/network/offline degradation drills
- packaging/install/update/rollback
- SBOM and third-party notices
- performance/energy/cost baseline + regression thresholds
- supported-device compatibility matrix
- reproducible release manifest
