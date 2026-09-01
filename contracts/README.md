# Clever canonical contracts — v1

These schemas are the CP02 boundary between the Clever JARVIS control plane and native OpenJarvis, OpenClaw, Omi and Clicky adapters.

## Authority

- Protobuf defines the typed cross-runtime wire model.
- JSON Schema defines canonical JSON interchange/fixtures and non-Protobuf integration surfaces.
- `contract_manifest.json` binds contract family → Proto message → JSON Schema → fixture.
- Neither representation may grant permissions through extension metadata or unknown fields.

## Design laws

1. Every cross-runtime event has version, identity/scope, correlation/causation, classification and provenance.
2. Capabilities announce an owner, interface, lifecycle, permissions, state/side effects, platform constraints and evidence.
3. Policy decisions are separate from model reasoning and are referenced by side-effecting actions.
4. Retryable side effects carry stable idempotency keys and produce receipts.
5. Memory records carry ownership, access scope, retention, provenance and native runtime ownership.
6. Runtime health can be degraded/unavailable; false-green health is not representable as success-only state.
7. Perception records consent/permission state and avoids assuming raw capture is permanently retained.
8. Unknown major contract versions fail closed. Minor additions must preserve old-field semantics.

## CP02 sequence

`schemas → fixtures/round-trip/version-skew → language bindings → Rust kernel scaffold → action/lifecycle/audit → gauntlet`.
