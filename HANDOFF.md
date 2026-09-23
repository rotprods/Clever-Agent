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

`W02-17 — Paridad y grafo W02` (`READY`).

W02-16 is evidence-backed COMPLETE: prior P02 recovery/flakiness remains PASS and P01 now has a fixed-budget same-host direct-vs-adapted baseline with latency, TTFT, memory and throughput recorded. W02-17 is the only newly opened READY DAG frontier. No parity promotion, denominator mutation, provider egress or tool execution occurred.

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

## W02-16 recovery retest — PARTIAL

- Evidence: `EVID-W02-RECOVERY-RETEST-20260922` on exact tested head `1254e6f206596afcc6ce7c5f4323c5af31fb4ceb` / run `35756510838`.
- P02: 20/20 fixed repetitions executed; cancellation, frame-flood, byte-flood and crash/restart-budget probes all PASS; all 80 invocation records retained; failed invocations 0; no best-rerun selection.
- P01 same-host direct-vs-adapted performance: `NOT_RUN`; latency/TTFT/memory/throughput are therefore not claimed.
- Provider egress 0; model executions 0; tool executions 0; parity promotions 0; denominator 7565; OpenJarvis obligations 646.
- Claim `CLAIM-CP03-W02-RECOVERY-PERF-20260922` released at the end of this bounded sub-wave. `W02-16` remains `READY`; `W02-17` remains `BLOCKED`.
- Exact next sub-slice: W02-16 P01 fixed-budget same-host performance baseline.

## W02-16 recovery + performance — COMPLETE

- P02 evidence: `EVID-W02-RECOVERY-RETEST-20260922` remains PASS (20/20 repetitions; all 80 invocation records retained).
- P01 evidence: `EVID-W02-PERFORMANCE-BASELINE-20260922` on exact tested head `701a86a1c044bb69693034f78e58e3124346437b` / run `35769847083`. Fixed budget: 1 warmup + 3 measured samples per path, 32 max output tokens, temperature 0, fixed interleaved order.
- Direct median: latency 132.490 ms; TTFT 47.578 ms; throughput 45.286 tok/s; client peak RSS 46068 KiB.
- Adapted median: latency 424.320 ms; TTFT 340.192 ms; throughput 14.140 tok/s; client peak RSS 59148 KiB. Ratios adapted/direct: latency 3.2026, TTFT 7.1502, throughput 0.3122.
- Measurement-only: no post-hoc threshold, no parity promotion, denominator 7565 unchanged, OpenJarvis obligations 646, provider egress 0, tool executions 0.
- Claim `CLAIM-CP03-W02-PERFORMANCE-20260922` released. Exact next task: `W02-17 — Paridad y grafo W02`.

## W02-17 parity/graph — IN_PROGRESS

- Claim `CLAIM-CP03-W02-PARITY-GRAPH-20260922` acquired from exact base `465fe294e28fd683c7683aaca1e0acfcb03052a9`.
- Scope is G6 proof-plane compilation/validation only; parity promotions remain 0, denominator 7565 and OpenJarvis obligations 646 remain immutable. W02-18/W02-19 remain BLOCKED.

## W02-17 G6 proof plane — partial verified

- `EVID-W02-PARITY-GRAPH-CORE-20260922`: deterministic K=47 P0→P1→P2→P3 proof matrix/graph is implemented and fail-closed against forged/stale evidence, NOT_RUN/BLOCKED/PLATFORM_GATED/waivers and shared terminal attribution.
- This is not parity: 47/47 proof units remain `UNBOUND`, verified capabilities remain 0 and parity promotions remain 0. `W02-17` stays `IN_PROGRESS`; `W02-18` and `W02-19` stay `BLOCKED`.
- Exact next slice: author explicit capability→test→evidence bindings, validated against completed-task PASS proof + exact evidence SHA + field-level expectations; preserve the real OpenJarvis fallback model lane as `NOT_RUN`.
- Claim scope amended at exact continuation base `ab1f7665682cffe960906e8a6c1808f14acd9318` to include `inventory/cp03/w02_evidence_bindings.jsonl`; this authorizes explicit G6 bindings only and does not promote parity.

## W02-17 explicit binding seed — partial verified

- `EVID-W02-PARITY-BINDING-SEED-20260922`: `cap_49014a3c03b104c8ec2f4ca1` (`InferenceEngine`, OWNED) is explicitly bound to the real unary-inference test `adapter_supervisor::real_openjarvis_unary_inference_uses_pinned_llamacpp_lane`, completed-task evidence `EVID-W02-UNARY-INFERENCE-20260921`, exact evidence SHA `a29389d41642ca74ed9c09ccfb9ec9f1725b48d7`, and field-level runtime expectations.
- Binding state only: 1 `EVIDENCE_BACKED_CANDIDATE`, 46 `UNBOUND`, VERIFIED capabilities 0, parity promotions 0. Denominator 7565 and OpenJarvis obligations 646 unchanged.
- Real OpenJarvis fallback model execution remains `NOT_RUN`; W02-18/W02-19 remain `BLOCKED`; W02-17 remains `IN_PROGRESS`.
- Exact next slice: bind the next W02 capability that has capability-specific executed test evidence; never infer a binding from task-level PASS alone.

## W02-17 Ollama registry binding — partial verified

- `EVID-W02-PARITY-BINDING-OLLAMA-20260923`: `cap_a5ae164f941b35e6fafd357c` (`ollama`, OWNED registry registration) is bound to completed W02-08 evidence `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4`.
- Capability-specific executed test: `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_ollama_registry_binding_is_capability_specific_and_evidence_backed`; the test resolves the frozen source surface `src/openjarvis/engine/ollama.py:106` to the exact preserved native-catalog row `openjarvis.engine.ollama.OllamaEngine`, state `REGISTERED`, with zero model/provider execution.
- G6 binding state is now 2 `EVIDENCE_BACKED_CANDIDATE` / 45 `UNBOUND`; VERIFIED capabilities remain 0 and parity promotions remain 0. Denominator 7565 and OpenJarvis obligations 646 are unchanged.
- `NOT_RUN`, `BLOCKED`, `PLATFORM_GATED` and waiver states remain non-proof. Real OpenJarvis fallback model execution remains `NOT_RUN`. W02-17 stays `IN_PROGRESS`; W02-18/W02-19 stay `BLOCKED`.
- Exact next slice: bind the next W02 capability only when its own executed test can be named and traced to an exact completed-task receipt; do not infer parity from task-level PASS or catalog membership alone.

## W02-17 LiteLLM registry binding — partial verified

- `EVID-W02-PARITY-BINDING-LITELLM-20260923`: `cap_149d7cf3bf745e7bea3fa1b0` (`litellm`, OWNED registry registration) is bound to completed W02-08 evidence `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4`.
- Capability-specific executed test: `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_litellm_registry_binding_is_capability_specific_and_evidence_backed`; it resolves frozen source `src/openjarvis/engine/litellm.py:16` to native catalog `openjarvis.engine.litellm.LiteLLMEngine`, state `REGISTERED`, with zero model/provider execution.
- G6 is now 3 `EVIDENCE_BACKED_CANDIDATE` / 44 `UNBOUND`; VERIFIED remains 0 and parity promotions remain 0. Denominator 7565 and OpenJarvis obligations 646 are unchanged.
- `NOT_RUN`, `BLOCKED`, `PLATFORM_GATED` and waivers remain non-proof. Real OpenJarvis fallback model execution remains `NOT_RUN`. W02-17 stays `IN_PROGRESS`; W02-18/W02-19 stay `BLOCKED`.
- Exact next slice: bind the next W02 capability only when its own executed test can be named and traced to an exact completed-task receipt.

## W02-17 Cloud registry binding — partial verified

- `EVID-W02-PARITY-BINDING-CLOUD-20260923`: `cap_49e508ee1377a8861a33b2f0` (`cloud`, OWNED registry registration) is bound to completed W02-08 evidence `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4`.
- Capability-specific executed test: `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_cloud_registry_binding_is_capability_specific_and_evidence_backed`; it resolves frozen source `src/openjarvis/engine/cloud.py:323` to native catalog `openjarvis.engine.cloud.CloudEngine`, state `REGISTERED`, with zero model/provider execution.
- G6 is now 4 `EVIDENCE_BACKED_CANDIDATE` / 43 `UNBOUND`; VERIFIED remains 0 and parity promotions remain 0. Denominator 7565 and OpenJarvis obligations 646 are unchanged.
- `NOT_RUN`, `BLOCKED`, `PLATFORM_GATED` and waivers remain non-proof. Real OpenJarvis fallback model execution remains `NOT_RUN`. W02-17 stays `IN_PROGRESS`; W02-18/W02-19 stay `BLOCKED`.
- Exact next slice: bind the next W02 capability only when its own executed test can be named and traced to an exact completed-task receipt.

## W02-17 NIM registry binding — partial verified

- `EVID-W02-PARITY-BINDING-NIM-20260923`: `cap_fa50b5646f0cfab91c7efec5` (`nim`, OWNED registry registration) is bound to completed W02-08 evidence `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4`.
- Capability-specific executed test: `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_nim_registry_binding_is_capability_specific_and_evidence_backed`; it resolves frozen source `src/openjarvis/engine/nim.py:26` to native catalog `openjarvis.engine.nim.NIMEngine`, state `REGISTERED`, with zero model/provider execution.
- G6 is now 5 `EVIDENCE_BACKED_CANDIDATE` / 42 `UNBOUND`; VERIFIED remains 0 and parity promotions remain 0. Denominator 7565 and OpenJarvis obligations 646 are unchanged.
- `NOT_RUN`, `BLOCKED`, `PLATFORM_GATED` and waivers remain non-proof. Real OpenJarvis fallback model execution remains `NOT_RUN`. W02-17 stays `IN_PROGRESS`; W02-18/W02-19 stay `BLOCKED`.
- Exact next slice: bind the next W02 capability only when its own executed test can be named and traced to an exact completed-task receipt.

## W02-17 GemmaCpp registry binding — partial verified

- `EVID-W02-PARITY-BINDING-GEMMA-CPP-20260923`: `cap_5cf599d5c98778fc324cbd0c` (`gemma_cpp`, OWNED registry registration) is bound to completed W02-08 evidence `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4`.
- Capability-specific executed test: `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_gemma_cpp_registry_binding_is_capability_specific_and_evidence_backed`; it resolves frozen source `src/openjarvis/engine/gemma_cpp.py:24` to native catalog `openjarvis.engine.gemma_cpp.GemmaCppEngine`, state `REGISTERED`, with zero model/provider execution.
- G6 is now 6 `EVIDENCE_BACKED_CANDIDATE` / 41 `UNBOUND`; VERIFIED remains 0 and parity promotions remain 0. Denominator 7565 and OpenJarvis obligations 646 are unchanged.
- `NOT_RUN`, `BLOCKED`, `PLATFORM_GATED` and waivers remain non-proof. Real OpenJarvis fallback model execution remains `NOT_RUN`. W02-17 stays `IN_PROGRESS`; W02-18/W02-19 stay `BLOCKED`.
- Exact next slice: bind the next W02 capability only when its own executed test can be named and traced to an exact completed-task receipt.

## W02-17 OpenAI-compat register binding — partial verified

- `EVID-W02-PARITY-BINDING-OPENAI-COMPAT-REGISTER-20260923`: `cap_5411f850a1935d329d2c53a0` (`register`, OWNED registry registration) is bound to completed W02-08 evidence `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4`.
- Capability-specific executed test: `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_openai_compat_register_binding_is_capability_specific_and_evidence_backed`; it resolves frozen source `src/openjarvis/engine/openai_compat_engines.py:27` and verifies the ten persisted OpenAI-compatible registered engine keys with zero model/provider execution.
- G6 is now 7 `EVIDENCE_BACKED_CANDIDATE` / 40 `UNBOUND`; VERIFIED remains 0 and parity promotions remain 0. Denominator 7565 and OpenJarvis obligations 646 are unchanged.
- `NOT_RUN`, `BLOCKED`, `PLATFORM_GATED` and waivers remain non-proof. Real OpenJarvis fallback model execution remains `NOT_RUN`. W02-17 stays `IN_PROGRESS`; W02-18/W02-19 stay `BLOCKED`.
- Exact next slice: bind the next W02 capability only when its own executed test can be named and traced to an exact completed-task receipt.

## W02-17 model register_value binding — partial verified

- `EVID-W02-PARITY-BINDING-MODEL-REGISTER-VALUE-20260923`: `cap_1d68bea6da6cb4c552cee405` (`register_value`, OWNED registry registration) is bound to completed W02-08 evidence `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4`.
- Capability-specific executed test: `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_model_register_value_binding_is_capability_specific_and_evidence_backed`; it resolves frozen source `src/openjarvis/intelligence/model_catalog.py:1074`, proves the executed bridge calls `register_builtin_models`, and validates the 69 persisted `ModelSpec` registrations with zero model/provider/tool execution.
- G6 is now 8 `EVIDENCE_BACKED_CANDIDATE` / 39 `UNBOUND`; VERIFIED remains 0 and parity promotions remain 0. Denominator 7565 and OpenJarvis obligations 646 are unchanged.
- `NOT_RUN`, `BLOCKED`, `PLATFORM_GATED` and waivers remain non-proof. Real OpenJarvis fallback model execution remains `NOT_RUN`. W02-17 stays `IN_PROGRESS`; W02-18/W02-19 stay `BLOCKED`.
- Exact next slice: bind the next W02 capability only when its own executed test can be named and traced to an exact completed-task receipt.

## W02-17 model register_value:1088 binding — partial verified

- `EVID-W02-PARITY-BINDING-MODEL-REGISTER-VALUE-1088-20260923`: `cap_d0bb7e74057a2b59835f2143` (`register_value`, OWNED registry registration) is bound to completed W02-08 evidence `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4`.
- Capability-specific executed test: `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_model_register_value_1088_binding_is_capability_specific_and_evidence_backed`; it resolves frozen source `src/openjarvis/intelligence/model_catalog.py:1088`, verifies the obligation registrar is `ModelRegistry.register_value`, and validates the 69 persisted `ModelSpec` registrations with zero model/provider/tool execution.
- G6 is now 9 `EVIDENCE_BACKED_CANDIDATE` / 38 `UNBOUND`; VERIFIED remains 0 and parity promotions remain 0. Denominator 7565 and OpenJarvis obligations 646 are unchanged.
- `NOT_RUN`, `BLOCKED`, `PLATFORM_GATED` and waivers remain non-proof. Real OpenJarvis fallback model execution remains `NOT_RUN`. W02-17 stays `IN_PROGRESS`; W02-18/W02-19 stay `BLOCKED`.
- Exact next slice: bind the next W02 capability only when its own executed test can be named and traced to an exact completed-task receipt.

## W02-17 CLI model list register_builtin_models binding — partial verified

- `EVID-W02-PARITY-BINDING-CLI-MODEL-LIST-REGISTER-BUILTIN-20260923`: `cap_a1156e1a8626c074910758f9` (`register_builtin_models`, OWNED registry registration) is bound to completed W02-08 evidence `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4` plus an exact pinned-source probe for `src/openjarvis/cli/model.py:38`.
- Capability-specific executed test: `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_cli_model_list_register_builtin_binding_is_capability_specific_and_evidence_backed`. The source probe proves `list_models` calls `register_builtin_models` before engine discovery at upstream `72033b8ec288aa067ce4530ff9d96bf231e9c4e5`; W02-08 separately persists 69 registered `ModelSpec` entries. The CLI source itself remains `NOT_EXECUTED` in this slice.
- G6 is now 10 `EVIDENCE_BACKED_CANDIDATE` / 37 `UNBOUND`; VERIFIED remains 0 and parity promotions remain 0. Denominator 7565 and OpenJarvis obligations 646 are unchanged.
- `NOT_RUN`, `BLOCKED`, `PLATFORM_GATED`, source-only proof and waivers remain non-proof for VERIFIED parity. Real OpenJarvis fallback model execution remains `NOT_RUN`. W02-17 stays `IN_PROGRESS`; W02-18/W02-19 stay `BLOCKED`.
- Exact next slice: bind the next W02 capability only when its own executed test can be named and traced to exact completed-task evidence; do not infer behavioral parity from source presence alone.

## W02-17 CLI model info register_builtin_models binding — partial verified

- `EVID-W02-PARITY-BINDING-CLI-MODEL-INFO-REGISTER-BUILTIN-20260923`: `cap_bdc045630a6fcf4735394782` (`register_builtin_models`, OWNED registry registration) is bound to completed W02-08 evidence `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4` plus an exact pinned-source probe for `src/openjarvis/cli/model.py:90`.
- Capability-specific executed test: `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_cli_model_info_register_builtin_binding_is_capability_specific_and_evidence_backed`. The source probe proves `info` calls `register_builtin_models` before engine discovery at upstream `72033b8ec288aa067ce4530ff9d96bf231e9c4e5`; W02-08 separately persists 69 registered `ModelSpec` entries. The CLI source itself remains `NOT_EXECUTED` in this slice.
- G6 is now 11 `EVIDENCE_BACKED_CANDIDATE` / 36 `UNBOUND`; VERIFIED remains 0 and parity promotions remain 0. Denominator 7565 and OpenJarvis obligations 646 are unchanged.
- `NOT_RUN`, `BLOCKED`, `PLATFORM_GATED`, source-only proof and waivers remain non-proof for VERIFIED parity. Real OpenJarvis fallback model execution remains `NOT_RUN`. W02-17 stays `IN_PROGRESS`; W02-18/W02-19 stay `BLOCKED`.
- Exact next slice: bind the next W02 capability only when its own executed test can be named and traced to exact completed-task evidence; do not infer behavioral parity from source presence alone.
