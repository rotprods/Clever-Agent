# Iteration 02 — Canonical Contracts + Rust Kernel Scaffold

## Identity

- Iteration: `I02`
- Goal: `CLEVER-JARVIS-001`
- Global checkpoint: `CP02`
- Type: canonical contract compiler / cross-runtime compatibility / Rust kernel foundation

## Objective

Convert the evidence-backed CP01 capability denominator into the smallest stable set of cross-runtime contracts needed to make OpenJarvis, OpenClaw, Omi and Clicky behave as one system without rewriting their mature native implementations.

CP02 is **contract-first**. The Rust kernel may only implement semantics already represented by versioned contracts and contract tests.

## Required contract families

1. Identity: user/device/channel/session/goal identities and scopes.
2. Event: message ID, correlation/causation, provenance, classification and versioning.
3. Capability contribution: typed family, owner, lifecycle, permissions, state effects, health/degradation, rollback and evidence mapping.
4. Policy/action: action intent, risk class, authorization, idempotency, receipt/result and audit correlation.
5. Memory/state: provenance, retention, access scope, derivation, native owner and migration metadata.
6. Runtime lifecycle: health, readiness, degradation, startup/shutdown and recovery.
7. Trace/evaluation: invocation spans, evidence pointers, quality/cost/energy metrics and promotion outcomes.
8. Perception/embodiment handoff: audio/screen/device observations and native client response/pointing handoff.

## Subcheckpoints

- `I02.0` — CP01 evidence handoff / iteration bootstrap.
- `I02.1` — canonical schema vocabulary + Protobuf/JSON Schema definitions.
- `I02.2` — Rust/Python/TypeScript/Swift binding/codegen strategy + round-trip/version-skew tests.
- `I02.3` — Rust kernel workspace: identity, event bus, capability registry and policy decision skeleton.
- `I02.4` — action receipts, lifecycle/health and append-only audit primitives.
- `I02.5` — cross-runtime contract fixtures + adversarial malformed/version-skew/replay tests.
- `I02.6` — CP02 reconciliation and close.

## Hard gates

- No native upstream implementation is deleted or migrated during CP02.
- No `MERGE_STATE` is executed from a provisional COS decision.
- Contract versions are explicit and unknown versions fail safely.
- Side-effect contracts carry idempotency and policy decision correlation.
- Memory contracts preserve provenance/access/retention metadata.
- Kernel code does not embed provider/channel/device-specific assumptions that belong in adapters.

## Definition of Done

CP02 closes only when versioned contracts exist, their target-language representations/fixtures round-trip deterministically, version skew is tested, and a Rust kernel scaffold implements identity/event/capability/policy primitives behind those contracts with tests and recovery/security evidence.
