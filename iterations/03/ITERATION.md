# Iteration 03 — OpenJarvis Cognitive Adapter

## Identity

- Iteration: `I03`
- Goal: `CLEVER-JARVIS-001`
- Global checkpoint: `CP03`
- Pinned upstream: `open-jarvis/OpenJarvis@72033b8ec288aa067ce4530ff9d96bf231e9c4e5`
- Frozen OpenJarvis obligation set: **646** behavior-mapped capabilities
- Deferred OpenJarvis candidates: **2188** definitions; not denominator-eligible unless promoted by a separate evidence transaction

## Objective

Expose the complete evidence-backed OpenJarvis cognitive runtime through Clever canonical contracts while preserving native behavior and keeping Clever's Rust kernel/policy core as T0 authority.

CP03 is federation and adapter parity. It is not native-state convergence and it is not a rewrite of OpenJarvis.

## Architecture

```text
Clever Rust kernel (T0)
        |
        | canonical framed contract
        v
supervised OpenJarvis adapter process (T1)
        |
        v
pinned OpenJarvis Python runtime
```

The transport choice is finalized by ADR-CP03-001 after measuring in-process PyO3 vs supervised stdio vs loopback RPC. Default hypothesis: supervised framed stdio because it gives crash/kill/restart isolation without embedding Python into T0.

## Non-negotiable authority split

OpenJarvis may request cognition and actions. Clever decides authorization. Native OpenJarvis RBAC, taint, confirmation and guardrails are preserved as defense-in-depth but can never convert a Clever DENY into ALLOW or self-assign risk/privilege.

## Waves

### CP03-W00 — Hermetic upstream baseline

Execute the safe OpenJarvis test subset from the exact pin in a network-disabled, secret-free, read-only-source sandbox. Classify cloud/live/hardware/Docker/external-framework tests explicitly.

### CP03-W01 — Transport/lifecycle/registry bridge

Create transport ADR, supervised adapter lifecycle, canonical handshake, registry snapshot and capability announcements. Test malformed frames, unknown versions, crash/restart, backpressure and self-escalation attempts.

### CP03-W02 — Models/engines/inference

Map ModelRegistry/EngineRegistry and engine behaviors: discovery, health, generate, stream, stream_full, structured output, tool-call fragments, fallback and degradation.

### CP03-W03 — Agents/tools/MCP

Map agents, tools and MCP while routing side effects through Clever ActionIntent/PolicyDecision/Receipt. R2+ execution must be process-isolated and killable; native Python thread timeout is not treated as cancellation.

### CP03-W04 — Memory/retrieval

Preserve native memory behavior while enforcing canonical PrincipalRef, scope, classification, retention and provenance. Prove cross-user denial. Do not migrate native state in CP03.

### CP03-W05 — Traces/telemetry/evals/learning signals

Correlate native traces with canonical events/actions/evidence. Learning emits proposals only; no automatic production prompt/skill/policy promotion.

### CP03-W06 — Scheduler/proactive/persistent operatives

Map scheduling and proactive execution with fake-clock/DST/restart/replay/idempotency tests. Scheduling never implies side-effect authorization.

### CP03-W07 — Security reconciliation

Preserve native guardrails, injection scanning, SSRF, taint, audit, signing and sandbox signals under Clever T0 policy authority.

### CP03-W08 — Parity compiler/gap burn-down

Use append-only `PARITY_LEDGER.ndjson` over the immutable CP01 denominator. Drive all 646 obligations through MAPPED → IMPLEMENTED → TESTED → VERIFIED or a globally permitted evidenced terminal exception.

### CP03-W09 — Adversarial/recovery/performance gauntlet

Attack sidecar crashes/hangs, malformed/duplicate/out-of-order frames, zombie tools, memory isolation, prompt injection, SSRF, audit tamper, poisoned learning, scheduler replay and performance regressions.

### CP03-W10 — Release reconciliation

Clean-room rebuild all CP03 evidence and close only if every OpenJarvis obligation has a valid evidence-backed terminal state and all release/security/recovery gates pass.

## Definition of Done

- CP02 is merged and release evidence is durable.
- The global denominator remains 7565.
- The OpenJarvis obligation manifest remains exactly 646 for the pinned source.
- Baseline truth is executable and hermetic where supported.
- Adapter lifecycle and registry are versioned and supervised.
- Inference/agents/tools/memory/traces/learning/scheduler/security are mapped through canonical contracts.
- R2+ tool execution cannot rely on non-killable Python thread timeouts.
- Memory isolation is enforced before ranking/retrieval.
- Learning remains proposal-only.
- Every parity state is derived from `PARITY_LEDGER.ndjson` and evidence.
- CP03 gauntlet and release gate pass.
