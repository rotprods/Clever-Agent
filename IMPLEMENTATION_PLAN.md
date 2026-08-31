# IMPLEMENTATION PLAN — CLEVER-JARVIS-001

## Current position

- CP01: COMPLETE.
- CP02: IN_PROGRESS.
- Iteration: I02.
- Frontier: `CP02-W01 / CP02-001`.
- CP01 denominator: generated and unverified at Clever adapter level.

## CP02 sequence

1. **CP02-W01:** versioned Protobuf + JSON Schema contracts for identity, events, capabilities, actions/policy/receipts, memory/state, lifecycle/health, traces/evaluation and perception/embodiment.
2. **CP02-W02:** canonical fixtures + Rust/Python/TypeScript/Swift binding/codegen strategy; round-trip, malformed payload and version-skew tests.
3. **CP02-W03:** Rust kernel scaffold for identity/event/capability/policy only.
4. **CP02-W04:** idempotent action receipts, lifecycle/health and append-only audit.
5. **CP02-W05:** adversarial security/recovery/version-skew gauntlet.
6. **CP02-W06:** evidence reconciliation and CP02 close.

## Stop conditions

- Contracts before kernel implementation.
- No provider/channel/device-specific logic in the kernel.
- No state migration or upstream deletion in CP02.
- Unknown contract versions fail safely.
- Side effects require policy correlation + idempotency + receipts.
