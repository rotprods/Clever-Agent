# HANDOFF — CP03-W02

- Checkpoint: `CP03`; iteration: `I03`; parent wave `CP03-W02` remains `IN_PROGRESS`.
- Frozen proof scope: **K=47 = 37 owned + 10 shared**; global denominator 7,565; OpenJarvis obligations 646; VERIFIED 0.
- COMPLETE: `W02-00..W02-12`.
- W02-09 evidence: `EVID-W02-REAL-MODEL-20260921`.
- W02-10 G3 evidence: `EVID-W02-UNARY-INFERENCE-20260921`; one real model execution, correlated unary chunk+terminal, provider egress 0, tool executions 0, parity promotions 0.
- W02-11 G4 evidence: `EVID-W02-STREAMING-20260921`; native `stream_full` bridge semantics + fragmented/coalesced canonical transport PASS; duplicate/reordered/EOF-before-terminal paths fail closed; provider egress 0; parity promotions 0.
- W02-12 G4 evidence: `EVID-W02-CANCELLATION-20260921`; request/attempt-scoped cancellation distinguishes REQUESTED → ACK → CANCELLED terminal, cancel-before/during PASS, already-terminal REJECTED, ACK-without-termination fails closed, explicit single-flight PASS; local worker cessation PASS; remote/provider cancellation effect remains UNKNOWN; provider egress 0; parity promotions 0.
- W02-13 partial G4 evidence: `EVID-W02-STRUCTURED-CORE-20260921`; fragmented OpenJarvis tool-call arguments assemble into bounded typed inert data, malformed JSON/schema violations fail closed, malicious tool names are preserved without execution, and targeted + streaming/cancellation/contract + kernel security regressions pass on the exact head. This is not W02-13 completion: canonical AdapterFrame/sidecar transport for typed tool/structured data remains unimplemented.
- W02-13 G4 completion evidence: `EVID-W02-STRUCTURED-TRANSPORT-20260922`; explicit typed `InferenceToolCall`/`InferenceStructuredOutput` bodies cross AdapterFrame/sidecar with correlated request/attempt identity, caller schema parsing is bounded/fail-closed, four language bindings are regenerated and round-trip tested, malicious tool names remain inert, tool executions 0, provider egress 0, parity promotions 0.
- Real L2 lane: OpenJarvis `qwen3:0.6b` → `llamacpp`; base revision `66b95ce14c07166297fcbfb54aa20441af8f9d75`; runtime commit `391fac16460f15233a7740550d858ac96df3419d`.
- Real GGUF artifact: `Qwen_Qwen3-0.6B-Q4_K_M.gguf`, 484220320 bytes, SHA-256 `9acfc1e001311f34b4252001b626f2e466d592a42065f66571bff3790d4e1b14`; controlled acquisition followed by network-none verification PASS.
- Missing/corrupt/mock artifacts remain fail-closed. W02-09 acquisition itself executed no model; W02-10 subsequently executed exactly one local pinned-model inference. Provider egress remained 0; parity promotions remained 0; denominator unchanged.

## Next executable

`W02-16 — Retest recovery performance` (`READY`).

W02-15 is evidence-backed COMPLETE. The next and only READY DAG frontier is W02-16; W02-17+ remain BLOCKED. No parity promotion, denominator mutation, provider egress, model execution, or tool execution occurred in the W02-15 security closure.

## W02-14 fallback — COMPLETE

- Evidence: `EVID-W02-FALLBACK-ADAPTER-20260922` on exact tested head `503d683df9107519956f976ad8db1fc9c09509b1` / run `35724141588`.
- `AdapterSupervisor` now invokes the already-proven bounded fallback state machine at the canonical streaming transport boundary. Retry is possible only for a correlated retryable `InferenceError` before the first emitted chunk; protocol/I/O failures are non-retryable.
- Every fallback uses a generated fresh attempt ID, remains on the local `llamacpp` engine class, preserves cumulative reservation accounting, and repeated targets/attempt ceilings remain enforced by the core policy.
- Adversarial fake-sidecar transport proves: pre-token retry recovers on a fresh attempt; primary partial output stops with no retry/no splice; retry partial output blocks a third attempt.
- Real OpenJarvis fallback model execution is still `NOT_RUN`; this wave does not turn that into PASS. Provider egress 0; model executions 0; tool executions 0; parity promotions 0; denominator 7565; OpenJarvis obligations 646.
- Claim `CLAIM-CP03-W02-FALLBACK-20260922` is released after evidence-backed W02-14 completion. W02-15 is only opened as `READY`; it is not claimed or implemented here.
- Exact next task: `W02-15 — Regresión de seguridad` (G5), dependencies W02-07/W02-12/W02-13/W02-14 all COMPLETE.

## W02-15 security — COMPLETE

- Evidence: `EVID-W02-SECURITY-20260922` on exact tested head `9415e72774768fa71fc6c8077ac8c9322b58c8fc` / run `35744047938`.
- RED characterization reproduced the gap: the standalone cancellation API had no caller authority context and could reach transport using only request/attempt identifiers.
- T0 `AdapterSupervisor` now records the supervised streaming ownership tuple and requires exact request, attempt, canonical principal and session match before writing a standalone cancel frame. Cross-principal/tenant mismatch fails locally and does not poison the healthy transport.
- G5 regression remains green for injected/noncanonical egress origins, grant cross-principal/session isolation, secret canary redaction, privileged registry metadata filtering and bounded inbound flood behavior.
- Provider egress 0; model executions 0; tool executions 0; parity promotions 0; denominator 7565; OpenJarvis obligations 646. W02-14 real fallback model execution remains `NOT_RUN` and is not promoted.
- Claim `CLAIM-CP03-W02-SECURITY-20260922` is released. Exact next task: `W02-16 — Retest recovery performance` (G5), dependency W02-15 COMPLETE.
