# CP02 Contract Requirements — derived from CP01

These requirements are generated from the CP01 capability families. They define contract pressure, not final API syntax.

## C02-IDENTITY — identity/device/session/goal

- Required: `true`
- Evidence pressure count: `1000`
- Families: `session_identity, device_wearable, agent`
- Reason: cross-runtime continuity requires one subject/device/session/goal namespace

## C02-EVENT — event envelope + provenance/correlation/causation

- Required: `true`
- Evidence pressure count: `1037`
- Families: `channel_gateway, scheduler_automation, worker_service`
- Reason: federated runtimes need causal, replayable event semantics

## C02-CAPABILITY — capability contribution registry

- Required: `true`
- Evidence pressure count: `3269`
- Families: `agent, tool, inference, plugin_extension, channel_gateway`
- Reason: combine OpenJarvis typed primitives with OpenClaw contribution/lifecycle/rollback semantics

## C02-ACTION — policy/action/authorization/idempotency/receipt

- Required: `true`
- Evidence pressure count: `1804`
- Families: `tool, channel_gateway, scheduler_automation, device_wearable`
- Reason: side effects require explicit policy and replay-safe receipts

## C02-MEMORY — memory provenance/retention/access/state ownership

- Required: `true`
- Evidence pressure count: `851`
- Families: `memory_persistence`
- Reason: memory and persistence must converge without silent state loss

## C02-RUNTIME — runtime health/degradation/lifecycle/recovery

- Required: `true`
- Evidence pressure count: `1504`
- Families: `worker_service, plugin_extension, device_wearable`
- Reason: native adapters remain specialized and need observable lifecycle contracts

## C02-TRACE — trace/evidence/evaluation

- Required: `true`
- Evidence pressure count: `571`
- Families: `learning_evaluation, agent, inference`
- Reason: parity and learning need correlation from invocation through evidence

## C02-EMBODIMENT — perception/device/embodiment handoff

- Required: `true`
- Evidence pressure count: `1382`
- Families: `capture_perception, speech_audio, embodiment, device_wearable`
- Reason: Omi ambient perception and Clicky desktop embodiment must share identity/session while preserving native UX

## CP02 implementation gate

Define versioned schemas first, generate Rust/Python/TypeScript/Swift bindings, then require round-trip and version-skew tests before implementing the Rust kernel scaffold. Native upstream runtimes stay behind adapters until parity evidence permits convergence.
