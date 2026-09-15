# ADR CP03-W02-006 — Typed inference wire contract

Status: accepted for W02-06 contract validation; runtime execution remains unavailable.

## Context

The v1.1 adapter transport supports discovery and control but cannot represent an
inference attempt without hiding identity, sequencing, deadlines or terminal state
inside untyped metadata. W02-06 requires a compatible contract before egress,
provider credentials, real model execution or cancellation workers are introduced.

## Decision

Add `clever/v1/inference.proto` and extend `AdapterFrame` additively as wire v1.2.

- A request has stable `request_id` and per-execution `attempt_id`, canonical
  principal/session identity, explicit engine/model, bounded output configuration,
  an absolute deadline and idempotency key.
- Chunks are ordered within one attempt by a zero-based sequence.
- Exactly one terminal message ends an attempt with a typed finish reason and usage.
  Usage declares whether values are unknown, estimated or exact; absent optional
  token counts are not interpreted as zero.
- Errors use a finite code set and retryability flag. A retry must use a new
  `attempt_id`; streams from attempts may never be spliced.
- Cancellation targets both request and attempt. An acknowledgement is not yet a
  claim that execution or remote billing stopped; those semantics belong to W02-12.
- Tool roles and `TOOL_CALL` finish reasons are representational data only. W02-06
  does not authorize or execute tools.

The Rust kernel remains the T0 owner of admission, identity, policy, egress and
budget. Python/native runtimes translate behavior and cannot grant themselves those
permissions through inference messages.

## Compatibility

This is an additive minor extension. Existing v1.0/v1.1 fixtures remain valid and
unknown major versions continue to fail closed. Field numbers 20–24 are newly added
to `AdapterFrame`; existing field numbers are unchanged.

## Verification

Required before W02-06 completion:

1. schema and hostile fixture tests;
2. Buf format/lint/build;
3. deterministic Python fixture generation;
4. Python, TypeScript, Rust and Swift decode/encode round trips;
5. historical event and adapter fixtures still pass;
6. exact-head CI evidence with no parity promotion.

This ADR does not prove a model was loaded or invoked.
