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

`W02-14 — Fallback retry y salida parcial` (`READY`).

W02-13 is evidence-backed COMPLETE. The next and only opened DAG frontier is W02-14; W02-15+ remain BLOCKED. No parity promotion, denominator mutation, provider egress, or tool execution occurred in the W02-13 completion wave.

## W02-14 fallback — active

- Active claim: `CLAIM-CP03-W02-FALLBACK-20260922` on `wave/cp03/w02-fallback-20260922`; no overlapping active claim was accepted.
- Preserved core evidence: `EVID-W02-FALLBACK-CORE-20260922` proves the authority-free fallback decision core: fresh attempt IDs, cumulative reservation ceiling, repeated-target rejection, explicit target-class authorization, non-retryable stop, and mandatory no-retry after partial output.
- New partial evidence: `EVID-W02-FALLBACK-BOUNDARY-20260922` proves the generic supervised streaming attempt state machine around that core. A retryable pre-first-token failure may invoke exactly a fresh fallback attempt; an initial partial-output failure never invokes a fallback; and if a retry itself emits partial output before failing, no third attempt is invoked and streams are never spliced.
- RED evidence is retained rather than rewritten: run `35704980485` exposed self-induced stale event-SHA CAS after legal claim reconciliation; run `35706711804` exposed a wrong one-vs-two structured-frontier assertion cardinality assumption; PR run `35707116490` exposed missing workspace rustfmt conformance; run `35708253012` proved the persistence guard was over-specified by requiring `CURRENT_CONTEXT.md` to be dirty even when a deterministic rebuild legitimately left it byte-identical. Each root cause was diagnosed and corrected in the same W02-14 wave.
- W02-14 remains `IN_PROGRESS` with no task proof. The generic boundary is verified, but actual `AdapterSupervisor`/OpenJarvis sidecar F01/F02 wiring is still `NOT_RUN`; provider egress is 0, model executions in this sub-slice are 0, tool executions are 0, parity promotions are 0, denominator remains 7565, and OpenJarvis obligations remain 646.
- Exact next sub-slice: wire the proven state machine into the real `AdapterSupervisor` streaming transport boundary and prove, with correlated fake-sidecar/adversarial transport tests, retry only after a retryable failure before the first token plus a hard partial-output/no-splice terminal path. Do not open W02-15 until that evidence closes W02-14.
