from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source anchor, found {count}")
    return text.replace(old, new, 1)


def replace_region(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_at = text.find(start)
    end_at = text.find(end, start_at + len(start))
    if start_at < 0 or end_at < 0:
        raise RuntimeError(f"{label}: anchors missing")
    return text[:start_at] + replacement + text[end_at:]


def patch_adapter(text: str) -> str:
    text = replace_once(
        text,
        "    inference_security::{authorize_inference_egress, InferenceReservation, InferenceTarget},\n    version::validate_contract_version,\n",
        "    inference_fallback::{\n        execute_streaming_fallbacks, AttemptReceipt, FallbackCandidate, FallbackHistoryError,\n        FallbackPolicy, InferenceTargetClass, StreamingAttemptFailure, StreamingAttemptSuccess,\n        StreamingFallbackExecution,\n    },\n    inference_security::{authorize_inference_egress, InferenceReservation, InferenceTarget},\n    version::validate_contract_version,\n",
        "fallback imports",
    )

    result_anchor = '''#[derive(Debug, Clone, PartialEq)]\npub struct StreamingInferenceResult {\n    pub chunks: Vec<InferenceChunk>,\n    pub text: String,\n    pub terminal: InferenceTerminal,\n}\n'''
    result_block = result_anchor + '''\n#[derive(Debug, Clone, PartialEq, Eq)]\npub struct LocalStreamingFallbackCandidate {\n    pub model_id: String,\n    pub reserved_cost_microusd: u64,\n}\n'''
    text = replace_once(text, result_anchor, result_block, "fallback candidate type")

    replacement = r'''    pub fn infer_stream(
        &mut self,
        request: InferenceRequest,
    ) -> Result<StreamingInferenceResult, AdapterSupervisorError> {
        match self.infer_stream_attempt(request, true) {
            Ok(success) => Ok(success.value),
            Err(failure) => {
                let error = failure.error;
                if matches!(error, AdapterSupervisorError::InferenceFailed { .. }) {
                    self.fail_protocol(error)
                } else {
                    Err(error)
                }
            }
        }
    }

    /// Execute one logical streaming request with a bounded local llama.cpp
    /// fallback chain. The initial request stays on the pinned W02 model lane;
    /// fallback candidates may select a different non-empty llama.cpp model,
    /// but cannot change engine class, grant egress, or splice partial output.
    ///
    /// A retryable `InferenceError` is the only failure that may trigger a
    /// second transport attempt. Protocol/I/O failures are fail-closed and any
    /// emitted chunk permanently disables further attempts.
    pub fn infer_stream_with_local_fallbacks(
        &mut self,
        request: InferenceRequest,
        initial_reserved_cost_microusd: u64,
        candidates: &[LocalStreamingFallbackCandidate],
        policy: &FallbackPolicy,
    ) -> Result<
        StreamingFallbackExecution<StreamingInferenceResult, AdapterSupervisorError>,
        FallbackHistoryError,
    > {
        let request_id = request.request_id.clone();
        let base_request = request.clone();
        match self.infer_stream_attempt(request.clone(), true) {
            Ok(success) => Ok(StreamingFallbackExecution::Recovered {
                value: success.value,
                history: vec![AttemptReceipt {
                    attempt_id: request.attempt_id,
                    engine_id: request.engine_id,
                    model_id: request.model_id,
                    emitted_chunks: success.emitted_chunks,
                    reserved_cost_microusd: initial_reserved_cost_microusd,
                    target_class: InferenceTargetClass::Local,
                }],
                cumulative_reserved_cost_microusd: initial_reserved_cost_microusd,
            }),
            Err(initial_failure) => {
                let history = vec![AttemptReceipt {
                    attempt_id: request.attempt_id,
                    engine_id: request.engine_id,
                    model_id: request.model_id,
                    emitted_chunks: initial_failure.emitted_chunks,
                    reserved_cost_microusd: initial_reserved_cost_microusd,
                    target_class: InferenceTargetClass::Local,
                }];
                let fallback_candidates = candidates
                    .iter()
                    .map(|candidate| FallbackCandidate {
                        engine_id: W02_UNARY_ENGINE_ID.to_owned(),
                        model_id: candidate.model_id.clone(),
                        target_class: InferenceTargetClass::Local,
                        reserved_cost_microusd: candidate.reserved_cost_microusd,
                    })
                    .collect::<Vec<_>>();

                execute_streaming_fallbacks(
                    &request_id,
                    history,
                    initial_failure,
                    &fallback_candidates,
                    policy,
                    |attempt_id, candidate| {
                        let mut retry_request = base_request.clone();
                        retry_request.attempt_id = attempt_id.to_owned();
                        retry_request.engine_id = candidate.engine_id.clone();
                        retry_request.model_id = candidate.model_id.clone();
                        self.infer_stream_attempt(retry_request, false)
                    },
                )
            }
        }
    }

    fn infer_stream_attempt(
        &mut self,
        request: InferenceRequest,
        pinned_model_only: bool,
    ) -> Result<
        StreamingAttemptSuccess<StreamingInferenceResult>,
        StreamingAttemptFailure<AdapterSupervisorError>,
    > {
        if let Err(error) = self.ensure_io_healthy() {
            return Err(Self::streaming_attempt_failure(error, false, 0));
        }
        if !self.negotiated_features.contains("streaming-inference") {
            return Err(Self::streaming_attempt_failure(
                AdapterSupervisorError::InvalidInferenceRequest(
                    "peer did not negotiate streaming-inference".to_owned(),
                ),
                false,
                0,
            ));
        }

        let reservation = InferenceReservation {
            estimated_input_tokens: 0,
            estimated_cost_microusd: 0,
        };
        let local_target = InferenceTarget {
            provider_id: "openjarvis.llamacpp".to_owned(),
            origin: "loopback".to_owned(),
            external: false,
        };
        if let Err(error) = authorize_inference_egress(&request, &local_target, None, &reservation, 0)
        {
            return Err(Self::streaming_attempt_failure(
                AdapterSupervisorError::InvalidInferenceRequest(error.to_string()),
                false,
                0,
            ));
        }
        let config = match request.config.as_ref() {
            Some(config) => config,
            None => {
                return Err(Self::streaming_attempt_failure(
                    AdapterSupervisorError::InvalidInferenceRequest(
                        "config is required".to_owned(),
                    ),
                    false,
                    0,
                ))
            }
        };
        let invalid_model = request.model_id.trim().is_empty()
            || (pinned_model_only && request.model_id != W02_UNARY_MODEL_ID);
        if request.engine_id != W02_UNARY_ENGINE_ID
            || invalid_model
            || request.idempotency_key.trim().is_empty()
            || request.inputs.is_empty()
            || request.deadline_at.is_none()
            || !config.stream
            || config.max_output_tokens == 0
            || config.max_output_tokens > 256
            || request
                .inputs
                .iter()
                .any(|input| input.role == 0 || input.content.trim().is_empty())
        {
            return Err(Self::streaming_attempt_failure(
                AdapterSupervisorError::InvalidInferenceRequest(
                    "request is outside the bounded local llama.cpp streaming lane".to_owned(),
                ),
                false,
                0,
            ));
        }

        let frame = self.next_control_frame(
            adapter_frame::Body::InferenceRequest(request.clone()),
            self.policy.request_timeout,
        );
        let frame_id = frame.frame_id.clone();
        if let Err(error) = self.write_frame(&frame) {
            return Err(self.streaming_protocol_failure(error, 0));
        }

        let mut chunks = Vec::new();
        let mut text = String::new();
        let mut expected_sequence = 1_u64;
        loop {
            let emitted_chunks = u64::try_from(chunks.len()).unwrap_or(u64::MAX);
            let response = match self.receive_frame(self.policy.request_timeout, "streaming inference") {
                Ok(response) => response,
                Err(error) => return Err(self.streaming_protocol_failure(error, emitted_chunks)),
            };
            if let Err(error) = self.validate_inference_outer(&response, &frame_id) {
                return Err(Self::streaming_attempt_failure(error, false, emitted_chunks));
            }
            match response.body {
                Some(adapter_frame::Body::InferenceChunk(chunk)) => {
                    if let Err(error) = self.validate_stream_chunk(&chunk, &request, expected_sequence)
                    {
                        return Err(Self::streaming_attempt_failure(error, false, emitted_chunks));
                    }
                    text.push_str(&chunk.text_delta);
                    chunks.push(chunk);
                    expected_sequence = expected_sequence.saturating_add(1);
                }
                Some(adapter_frame::Body::InferenceTerminal(terminal)) => {
                    if chunks.is_empty() {
                        let error = AdapterSupervisorError::InvalidRuntimeResponse(
                            "stream terminal arrived before any content chunk".to_owned(),
                        );
                        return Err(self.streaming_protocol_failure(error, emitted_chunks));
                    }
                    let final_sequence = expected_sequence.saturating_sub(1);
                    if let Err(error) =
                        self.validate_stream_terminal(&terminal, &request, final_sequence)
                    {
                        return Err(Self::streaming_attempt_failure(error, false, emitted_chunks));
                    }
                    let emitted_chunks = u64::try_from(chunks.len()).unwrap_or(u64::MAX);
                    return Ok(StreamingAttemptSuccess {
                        value: StreamingInferenceResult {
                            chunks,
                            text,
                            terminal,
                        },
                        emitted_chunks,
                    });
                }
                Some(adapter_frame::Body::InferenceError(error)) => {
                    if error.request_id != request.request_id || error.attempt_id != request.attempt_id
                    {
                        let protocol_error = AdapterSupervisorError::InvalidRuntimeResponse(
                            "inference error identity mismatch".to_owned(),
                        );
                        return Err(self.streaming_protocol_failure(
                            protocol_error,
                            emitted_chunks,
                        ));
                    }
                    let retryable = error.retryable;
                    return Err(Self::streaming_attempt_failure(
                        AdapterSupervisorError::InferenceFailed {
                            code: error.code,
                            message: error.message,
                            retryable,
                        },
                        retryable,
                        emitted_chunks,
                    ));
                }
                _ => {
                    let error = AdapterSupervisorError::UnexpectedFrame("streaming inference");
                    return Err(self.streaming_protocol_failure(error, emitted_chunks));
                }
            }
        }
    }

    fn streaming_attempt_failure(
        error: AdapterSupervisorError,
        retryable: bool,
        emitted_chunks: u64,
    ) -> StreamingAttemptFailure<AdapterSupervisorError> {
        StreamingAttemptFailure {
            error,
            retryable,
            emitted_chunks,
        }
    }

    fn streaming_protocol_failure(
        &mut self,
        error: AdapterSupervisorError,
        emitted_chunks: u64,
    ) -> StreamingAttemptFailure<AdapterSupervisorError> {
        let error = match self.fail_protocol::<()>(error) {
            Ok(()) => unreachable!("fail_protocol always returns Err"),
            Err(error) => error,
        };
        Self::streaming_attempt_failure(error, false, emitted_chunks)
    }

'''
    text = replace_region(
        text,
        "    pub fn infer_stream(\n",
        "    fn send_inference_cancel_frame(\n",
        replacement,
        "AdapterSupervisor streaming fallback boundary",
    )
    return text


def patch_fake_sidecar(text: str) -> str:
    helper_anchor = '''def stream_terminal(request, final_sequence: int) -> adapter_pb2.AdapterFrame:\n    body = inference_pb2.InferenceTerminal(\n        contract_version=inference_version(),\n        request_id=request.request_id,\n        attempt_id=request.attempt_id,\n        final_sequence=final_sequence,\n        finish_reason=inference_pb2.INFERENCE_FINISH_REASON_STOP,\n        usage=inference_pb2.InferenceUsage(\n            measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN\n        ),\n    )\n    return frame(\n        "stream-terminal",\n        "inference_terminal",\n        body,\n        correlation_id="__REQUEST_FRAME__",\n    )\n\n\n'''
    helper_block = helper_anchor + '''def stream_error(request, *, retryable: bool, message: str) -> adapter_pb2.AdapterFrame:\n    body = inference_pb2.InferenceError(\n        contract_version=inference_version(),\n        request_id=request.request_id,\n        attempt_id=request.attempt_id,\n        code=13,\n        message=message,\n        retryable=retryable,\n    )\n    return frame(\n        "stream-error",\n        "inference_error",\n        body,\n        correlation_id="__REQUEST_FRAME__",\n    )\n\n\n'''
    text = replace_once(text, helper_anchor, helper_block, "fake fallback inference error")

    mode_anchor = '''    if mode.startswith("stream-"):\n        envelope = read_frame()\n'''
    mode_block = '''    if mode.startswith("stream-fallback-"):\n        envelope = read_frame()\n        if envelope is None or envelope.WhichOneof("body") != "inference_request":\n            return 68\n        primary = envelope.inference_request\n        if mode == "stream-fallback-pre-token":\n            failure = stream_error(primary, retryable=True, message="primary unavailable")\n            failure.correlation_id = envelope.frame_id\n            write_frame(failure)\n            retry_envelope = read_frame()\n            if retry_envelope is None or retry_envelope.WhichOneof("body") != "inference_request":\n                return 69\n            retry = retry_envelope.inference_request\n            if retry.request_id != primary.request_id or retry.attempt_id == primary.attempt_id:\n                return 70\n            chunk = stream_chunk(retry, 1, "fallback")\n            terminal = stream_terminal(retry, 1)\n            chunk.correlation_id = retry_envelope.frame_id\n            terminal.correlation_id = retry_envelope.frame_id\n            write_coalesced(chunk, terminal)\n            return 0\n        if mode == "stream-fallback-partial":\n            chunk = stream_chunk(primary, 1, "partial")\n            failure = stream_error(primary, retryable=True, message="failed after partial")\n            chunk.correlation_id = envelope.frame_id\n            failure.correlation_id = envelope.frame_id\n            write_coalesced(chunk, failure)\n            time.sleep(0.2)\n            return 0\n        if mode == "stream-fallback-retry-partial":\n            first_failure = stream_error(primary, retryable=True, message="primary unavailable")\n            first_failure.correlation_id = envelope.frame_id\n            write_frame(first_failure)\n            retry_envelope = read_frame()\n            if retry_envelope is None or retry_envelope.WhichOneof("body") != "inference_request":\n                return 71\n            retry = retry_envelope.inference_request\n            chunk = stream_chunk(retry, 1, "partial-retry")\n            retry_failure = stream_error(retry, retryable=True, message="retry failed after partial")\n            chunk.correlation_id = retry_envelope.frame_id\n            retry_failure.correlation_id = retry_envelope.frame_id\n            write_coalesced(chunk, retry_failure)\n            time.sleep(0.2)\n            return 0\n        return 72\n\n    if mode.startswith("stream-"):\n        envelope = read_frame()\n'''
    return replace_once(text, mode_anchor, mode_block, "fake fallback transport modes")


def patch_tests(text: str) -> str:
    text = replace_once(
        text,
        "        AdapterSupervisorError, InferenceCancelOutcome, SupervisorPolicy,\n    },\n    capabilities::CapabilityRegistry,\n    error::KernelError,\n",
        "        AdapterSupervisorError, InferenceCancelOutcome, LocalStreamingFallbackCandidate,\n        SupervisorPolicy,\n    },\n    capabilities::CapabilityRegistry,\n    error::KernelError,\n    inference_fallback::{\n        FallbackPolicy, FallbackStopReason, InferenceTargetClass, StreamingFallbackExecution,\n    },\n",
        "adapter fallback test imports",
    )

    helper_anchor = '''fn fake_stream_request() -> InferenceRequest {\n'''
    helper_block = '''fn local_fallback_policy() -> FallbackPolicy {\n    FallbackPolicy {\n        max_attempts: 3,\n        max_cumulative_reserved_cost_microusd: 100,\n        max_target_class: InferenceTargetClass::Local,\n    }\n}\n\nfn local_fallback_candidate(model_id: &str, reserved_cost_microusd: u64) -> LocalStreamingFallbackCandidate {\n    LocalStreamingFallbackCandidate {\n        model_id: model_id.to_owned(),\n        reserved_cost_microusd,\n    }\n}\n\nfn fake_stream_request() -> InferenceRequest {\n'''
    text = replace_once(text, helper_anchor, helper_block, "fallback test helpers")

    test_anchor = '''#[test]\nfn cancellation_before_first_chunk_requires_ack_and_cancelled_terminal() {\n'''
    tests = r'''#[test]
fn fallback_transport_retries_only_pre_token_with_fresh_attempt_identity() {
    let command = fake_command("stream-fallback-pre-token");
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())
        .expect("connect fallback fake sidecar");
    let request = fake_stream_request();
    let request_id = request.request_id.clone();
    let original_attempt_id = request.attempt_id.clone();
    let candidates = vec![local_fallback_candidate("qwen3:0.6b-fallback", 20)];

    let execution = supervisor
        .infer_stream_with_local_fallbacks(request, 10, &candidates, &local_fallback_policy())
        .expect("fallback history must remain internally consistent");

    match execution {
        StreamingFallbackExecution::Recovered {
            value,
            history,
            cumulative_reserved_cost_microusd,
        } => {
            assert_eq!(value.text, "fallback");
            assert_eq!(value.chunks.len(), 1);
            assert_eq!(history.len(), 2);
            assert_eq!(history[0].attempt_id, original_attempt_id);
            assert_eq!(history[0].emitted_chunks, 0);
            assert_eq!(history[1].attempt_id, format!("{request_id}:attempt:2"));
            assert_eq!(history[1].model_id, "qwen3:0.6b-fallback");
            assert_eq!(history[1].emitted_chunks, 1);
            assert_eq!(cumulative_reserved_cost_microusd, 30);
        }
        StreamingFallbackExecution::Stopped { .. } => panic!("pre-token retry should recover"),
    }
    assert!(!supervisor.is_poisoned());
}

#[test]
fn fallback_transport_stops_after_primary_partial_output_without_splicing() {
    let command = fake_command("stream-fallback-partial");
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())
        .expect("connect partial fallback fake sidecar");
    let candidates = vec![local_fallback_candidate("qwen3:0.6b-fallback", 20)];

    let execution = supervisor
        .infer_stream_with_local_fallbacks(
            fake_stream_request(),
            10,
            &candidates,
            &local_fallback_policy(),
        )
        .expect("partial-output stop must remain internally consistent");

    match execution {
        StreamingFallbackExecution::Stopped {
            last_error,
            reason,
            history,
            cumulative_reserved_cost_microusd,
        } => {
            assert!(matches!(
                last_error,
                AdapterSupervisorError::InferenceFailed {
                    retryable: true,
                    ..
                }
            ));
            assert_eq!(reason, FallbackStopReason::PartialOutput);
            assert_eq!(history.len(), 1);
            assert_eq!(history[0].emitted_chunks, 1);
            assert_eq!(cumulative_reserved_cost_microusd, 10);
        }
        StreamingFallbackExecution::Recovered { .. } => panic!("partial stream must never recover"),
    }
    assert!(!supervisor.is_poisoned());
}

#[test]
fn fallback_transport_never_starts_third_attempt_after_retry_partial_output() {
    let command = fake_command("stream-fallback-retry-partial");
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())
        .expect("connect retry-partial fallback fake sidecar");
    let candidates = vec![
        local_fallback_candidate("qwen3:0.6b-fallback-a", 20),
        local_fallback_candidate("qwen3:0.6b-fallback-b", 30),
    ];

    let execution = supervisor
        .infer_stream_with_local_fallbacks(
            fake_stream_request(),
            10,
            &candidates,
            &local_fallback_policy(),
        )
        .expect("retry-partial stop must remain internally consistent");

    match execution {
        StreamingFallbackExecution::Stopped {
            reason,
            history,
            cumulative_reserved_cost_microusd,
            ..
        } => {
            assert_eq!(reason, FallbackStopReason::PartialOutput);
            assert_eq!(history.len(), 2, "no third attempt may be invoked");
            assert_eq!(history[0].emitted_chunks, 0);
            assert_eq!(history[1].emitted_chunks, 1);
            assert_eq!(history[1].model_id, "qwen3:0.6b-fallback-a");
            assert_eq!(cumulative_reserved_cost_microusd, 30);
        }
        StreamingFallbackExecution::Recovered { .. } => {
            panic!("partial retry output must never be spliced into a later attempt")
        }
    }
    assert!(!supervisor.is_poisoned());
}

'''
    return replace_once(text, test_anchor, tests + test_anchor, "adapter fallback tests")


def main() -> None:
    paths = {
        "adapter": ROOT / "kernel/crates/clever-kernel/src/adapter.rs",
        "fixture": ROOT / "kernel/crates/clever-kernel/tests/fixtures/fake_adapter_sidecar.py",
        "tests": ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs",
    }
    original = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    patched = {
        "adapter": patch_adapter(original["adapter"]),
        "fixture": patch_fake_sidecar(original["fixture"]),
        "tests": patch_tests(original["tests"]),
    }
    for name, path in paths.items():
        path.write_text(patched[name], encoding="utf-8")


if __name__ == "__main__":
    main()
