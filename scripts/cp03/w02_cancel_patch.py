from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, new: str, label: str) -> str:
    if text.count(start) != 1 or text.count(end) < 1:
        raise RuntimeError(f"{label}: marker mismatch")
    left = text.index(start)
    right = text.index(end, left)
    return text[:left] + new + text[right:]


def patch_sidecar(text: str) -> str:
    text = replace_once(
        text,
        "import json\nfrom pathlib import Path\nimport struct\nimport sys\nimport time\nfrom typing import BinaryIO, Iterable\n",
        "import json\nfrom pathlib import Path\nimport queue\nimport struct\nimport sys\nimport threading\nimport time\nfrom typing import BinaryIO, Iterable\n",
        "sidecar imports",
    )
    text = replace_once(
        text,
        "from adapters.openjarvis.streaming_inference import execute_stream\n",
        "from adapters.openjarvis.cancellation import (\n    cancelled_terminal,\n    decode_worker_event,\n    poll_worker_event,\n    start_stream_worker,\n    terminate_worker_bounded,\n)\nfrom adapters.openjarvis.streaming_inference import execute_stream\n",
        "sidecar cancellation imports",
    )
    start = "def run_protocol(stdin: BinaryIO, stdout: BinaryIO) -> int:\n"
    end = "\n\ndef main() -> int:\n"
    new = r'''def run_protocol(stdin: BinaryIO, stdout: BinaryIO) -> int:
    snapshot, diagnostics = discover_registry_snapshot()
    write_frame(stdout, hello_frame())
    first = read_frame(stdin)
    if first is None or first.WhichOneof("body") != "hello_ack" or not first.hello_ack.accepted:
        return 64

    inbox: queue.Queue[tuple[str, object]] = queue.Queue()

    def reader_loop() -> None:
        while True:
            try:
                frame = read_frame(stdin)
            except BaseException as exc:
                inbox.put(("error", exc))
                return
            if frame is None:
                inbox.put(("eof", None))
                return
            inbox.put(("frame", frame))

    threading.Thread(target=reader_loop, name="clever-sidecar-control-reader", daemon=True).start()
    recent_terminal: tuple[str, str] | None = None

    def next_inbound(timeout: float | None = None) -> tuple[str, object]:
        return inbox.get(timeout=timeout) if timeout is not None else inbox.get()

    def adapter_error(code: str, message: str, request_frame_id: str) -> None:
        error = adapter_pb2.AdapterError(code=code, message=message, retryable=False)
        write_frame(
            stdout,
            _frame(f"error:{request_frame_id}", "error", error, correlation_id=request_frame_id),
        )

    while True:
        kind, payload = next_inbound()
        if kind == "eof":
            return 0
        if kind == "error":
            return 74
        request = payload
        assert isinstance(request, adapter_pb2.AdapterFrame)
        body = request.WhichOneof("body")
        if body == "registry_snapshot_request":
            response = _frame(f"registry:{request.frame_id}", "registry_snapshot", snapshot, correlation_id=request.frame_id)
            write_frame(stdout, response)
        elif body == "health_request":
            write_frame(stdout, health_frame(reasons=diagnostics["unsupported_registries"], correlation_id=request.frame_id))
        elif body == "cancel":
            # Legacy adapter cancellation remains control-plane only; it is never inference-stop proof.
            write_frame(stdout, health_frame(correlation_id=request.frame_id))
        elif body == "inference_cancel":
            target = request.inference_cancel
            if recent_terminal == (target.target_request_id, target.target_attempt_id):
                adapter_error("CANCEL_AFTER_TERMINAL", "inference already reached a terminal state", request.frame_id)
            else:
                adapter_error("CANCEL_TARGET_NOT_ACTIVE", "no matching active inference request/attempt", request.frame_id)
        elif body == "inference_request":
            native_request = request.inference_request
            try:
                if native_request.HasField("config") and native_request.config.stream:
                    active = start_stream_worker(native_request, request_frame_id=request.frame_id)
                    completed = False
                    while not completed:
                        # Control gets priority so cancel-before cannot be starved by a fast worker.
                        try:
                            control_kind, control_payload = next_inbound(timeout=0.005)
                        except queue.Empty:
                            control_kind, control_payload = "none", None
                        if control_kind == "eof":
                            terminate_worker_bounded(active)
                            return 0
                        if control_kind == "error":
                            terminate_worker_bounded(active)
                            return 74
                        if control_kind == "frame":
                            control = control_payload
                            assert isinstance(control, adapter_pb2.AdapterFrame)
                            control_body = control.WhichOneof("body")
                            if control_body == "inference_cancel":
                                cancel = control.inference_cancel
                                if (
                                    not cancel.HasField("contract_version")
                                    or cancel.contract_version.major != 1
                                    or not cancel.target_request_id.strip()
                                    or not cancel.target_attempt_id.strip()
                                    or cancel.target_request_id != active.request_id
                                    or cancel.target_attempt_id != active.attempt_id
                                ):
                                    adapter_error(
                                        "CANCEL_TARGET_MISMATCH",
                                        "cancel request/attempt does not match active inference",
                                        control.frame_id,
                                    )
                                    continue
                                receipt = terminate_worker_bounded(active)
                                if not receipt.process_stopped:
                                    adapter_error(
                                        "CANCEL_TERMINATION_FAILED",
                                        "local inference worker did not stop inside bounded kill window",
                                        control.frame_id,
                                    )
                                    return 75
                                # ACK means the local worker is no longer alive. It does not attest any
                                # remote provider/billing effect; W02-12 records that separately as UNKNOWN.
                                write_frame(stdout, health_frame(correlation_id=control.frame_id))
                                terminal = cancelled_terminal(active)
                                write_frame(
                                    stdout,
                                    _frame(
                                        f"inference-cancelled:{request.frame_id}",
                                        "inference_terminal",
                                        terminal,
                                        correlation_id=request.frame_id,
                                    ),
                                )
                                recent_terminal = (active.request_id, active.attempt_id)
                                completed = True
                                continue
                            busy = adapter_pb2.AdapterBusy(
                                retry_after_ms=25,
                                reason="single-flight inference active; only matching inference_cancel is accepted",
                            )
                            write_frame(
                                stdout,
                                _frame(f"busy:{control.frame_id}", "busy", busy, correlation_id=control.frame_id),
                            )
                            continue

                        event = poll_worker_event(active, timeout=0.005)
                        if event is None:
                            if not active.process.is_alive():
                                # One final queue poll closes the race between process exit and feeder flush.
                                event = poll_worker_event(active, timeout=0.05)
                                if event is None:
                                    failure = inference_pb2.InferenceError(
                                        contract_version=common_pb2.ContractVersion(major=1, minor=2),
                                        request_id=active.request_id,
                                        attempt_id=active.attempt_id,
                                        code=inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                                        message="stream worker exited without terminal/error",
                                        retryable=False,
                                    )
                                    write_frame(
                                        stdout,
                                        _frame(
                                            f"inference-error:{request.frame_id}",
                                            "inference_error",
                                            failure,
                                            correlation_id=request.frame_id,
                                        ),
                                    )
                                    recent_terminal = (active.request_id, active.attempt_id)
                                    completed = True
                            continue
                        event_kind, event_payload = event
                        message = decode_worker_event(event_kind, event_payload)
                        if event_kind == "worker_exit":
                            continue
                        if event_kind == "chunk":
                            assert isinstance(message, inference_pb2.InferenceChunk)
                            active.last_sequence = message.sequence
                            write_frame(
                                stdout,
                                _frame(
                                    f"inference-chunk:{request.frame_id}:{message.sequence}",
                                    "inference_chunk",
                                    message,
                                    correlation_id=request.frame_id,
                                ),
                            )
                            continue
                        if event_kind == "terminal":
                            assert isinstance(message, inference_pb2.InferenceTerminal)
                            active.process.join(timeout=0.25)
                            write_frame(
                                stdout,
                                _frame(
                                    f"inference-terminal:{request.frame_id}",
                                    "inference_terminal",
                                    message,
                                    correlation_id=request.frame_id,
                                ),
                            )
                            recent_terminal = (active.request_id, active.attempt_id)
                            completed = True
                            continue
                        if event_kind == "error":
                            assert isinstance(message, inference_pb2.InferenceError)
                            active.process.join(timeout=0.25)
                            write_frame(
                                stdout,
                                _frame(
                                    f"inference-error:{request.frame_id}",
                                    "inference_error",
                                    message,
                                    correlation_id=request.frame_id,
                                ),
                            )
                            recent_terminal = (active.request_id, active.attempt_id)
                            completed = True
                    continue

                outcome = execute_unary(native_request)
            except UnaryInferenceRejected as exc:
                failure = inference_pb2.InferenceError(
                    contract_version=common_pb2.ContractVersion(major=1, minor=2),
                    request_id=native_request.request_id,
                    attempt_id=native_request.attempt_id,
                    code=exc.code,
                    message=str(exc),
                    retryable=exc.retryable,
                )
                write_frame(
                    stdout,
                    _frame(
                        f"inference-error:{request.frame_id}",
                        "inference_error",
                        failure,
                        correlation_id=request.frame_id,
                    ),
                )
                recent_terminal = (native_request.request_id, native_request.attempt_id)
                continue
            write_frame(
                stdout,
                _frame(
                    f"inference-chunk:{request.frame_id}",
                    "inference_chunk",
                    outcome.chunk,
                    correlation_id=request.frame_id,
                ),
            )
            write_frame(
                stdout,
                _frame(
                    f"inference-terminal:{request.frame_id}",
                    "inference_terminal",
                    outcome.terminal,
                    correlation_id=request.frame_id,
                ),
            )
            recent_terminal = (native_request.request_id, native_request.attempt_id)
        elif body == "shutdown":
            seconds, nanos = _now_timestamp()
            stopping = runtime_pb2.RuntimeHealth(
                contract_version=contract_version(),
                runtime_id=RUNTIME_ID,
                status=runtime_pb2.RUNTIME_HEALTH_STATUS_STOPPING,
            )
            stopping.observed_at.seconds = seconds
            stopping.observed_at.nanos = nanos
            write_frame(stdout, _frame("openjarvis-stopping", "health", stopping, correlation_id=request.frame_id))
            return 0
        else:
            error = adapter_pb2.AdapterError(
                code="UNSUPPORTED_W02_FRAME",
                message=f"W02 sidecar does not execute frame body {body!r}",
                retryable=False,
            )
            write_frame(stdout, _frame(f"error:{request.frame_id}", "error", error, correlation_id=request.frame_id))
'''
    return replace_between(text, start, end, new, "sidecar run_protocol")


def patch_adapter(text: str) -> str:
    text = replace_once(
        text,
        "AdapterShutdown, CapabilityDescriptor, ContractVersion, InferenceChunk, InferenceError,\n    InferenceFinishReason, InferenceRequest, InferenceTerminal, InferenceUsageMeasurement,\n",
        "AdapterShutdown, CapabilityDescriptor, ContractVersion, InferenceCancel, InferenceChunk,\n    InferenceError, InferenceFinishReason, InferenceRequest, InferenceTerminal,\n    InferenceUsageMeasurement,\n",
        "adapter InferenceCancel import",
    )
    anchor = '''#[derive(Debug, Clone, PartialEq)]\npub struct StreamingInferenceResult {\n    pub chunks: Vec<InferenceChunk>,\n    pub text: String,\n    pub terminal: InferenceTerminal,\n}\n'''
    block = anchor + '''\n#[derive(Debug, Clone, PartialEq)]\npub struct CancelledInferenceResult {\n    pub chunks: Vec<InferenceChunk>,\n    pub text: String,\n    pub cancel_ack: RuntimeHealth,\n    pub terminal: InferenceTerminal,\n}\n'''
    text = replace_once(text, anchor, block, "adapter cancel result")
    method_anchor = "    fn validate_stream_chunk(\n"
    methods = r'''    pub fn infer_stream_cancel_after_sequence(
        &mut self,
        request: InferenceRequest,
        cancel_after_sequence: u64,
        reason: impl Into<String>,
    ) -> Result<CancelledInferenceResult, AdapterSupervisorError> {
        self.ensure_io_healthy()?;
        if !self.negotiated_features.contains("streaming-inference")
            || !self.negotiated_features.contains("cancel")
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(
                "peer did not negotiate streaming-inference + cancel".to_owned(),
            ));
        }
        let config = request.config.as_ref().ok_or_else(|| {
            AdapterSupervisorError::InvalidInferenceRequest("config is required".to_owned())
        })?;
        if request.engine_id != W02_UNARY_ENGINE_ID
            || request.model_id != W02_UNARY_MODEL_ID
            || request.request_id.trim().is_empty()
            || request.attempt_id.trim().is_empty()
            || request.idempotency_key.trim().is_empty()
            || request.inputs.is_empty()
            || request.deadline_at.is_none()
            || !config.stream
            || config.max_output_tokens == 0
            || config.max_output_tokens > 256
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(
                "request is outside the bounded W02-12 cancellable streaming lane".to_owned(),
            ));
        }

        let inference_frame = self.next_control_frame(
            adapter_frame::Body::InferenceRequest(request.clone()),
            self.policy.request_timeout,
        );
        let inference_frame_id = inference_frame.frame_id.clone();
        self.write_frame(&inference_frame)?;

        let reason = reason.into();
        let mut chunks = Vec::new();
        let mut text = String::new();
        let mut expected_sequence = 1_u64;
        let mut cancel_frame_id: Option<String> = None;
        let mut cancel_ack: Option<RuntimeHealth> = None;

        if cancel_after_sequence == 0 {
            cancel_frame_id = Some(self.send_inference_cancel(&request, reason.clone())?);
        }

        loop {
            let response = match self.receive_frame(self.policy.request_timeout, "cancellable stream") {
                Ok(response) => response,
                Err(error) => return self.fail_protocol(error),
            };

            if let Some(cancel_id) = cancel_frame_id.as_ref() {
                if response.correlation_id == *cancel_id {
                    if cancel_ack.is_some() {
                        return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                            "duplicate cancellation ACK".to_owned(),
                        ));
                    }
                    cancel_ack = Some(self.extract_health(response, "inference cancel ack")?);
                    continue;
                }
            }

            self.validate_inference_outer(&response, &inference_frame_id)?;
            match response.body {
                Some(adapter_frame::Body::InferenceChunk(chunk)) => {
                    if cancel_ack.is_some() {
                        return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                            "stream emitted content after cancellation ACK".to_owned(),
                        ));
                    }
                    self.validate_stream_chunk(&chunk, &request, expected_sequence)?;
                    text.push_str(&chunk.text_delta);
                    chunks.push(chunk);
                    expected_sequence = expected_sequence.saturating_add(1);
                    if cancel_frame_id.is_none()
                        && u64::try_from(chunks.len()).unwrap_or(u64::MAX) >= cancel_after_sequence
                    {
                        cancel_frame_id = Some(self.send_inference_cancel(&request, reason.clone())?);
                    }
                }
                Some(adapter_frame::Body::InferenceTerminal(terminal)) => {
                    if cancel_frame_id.is_none() {
                        return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                            "stream reached terminal before requested cancellation point".to_owned(),
                        ));
                    }
                    let ack = cancel_ack.take().ok_or_else(|| {
                        AdapterSupervisorError::InvalidRuntimeResponse(
                            "cancelled terminal arrived before cancellation ACK".to_owned(),
                        )
                    })?;
                    self.validate_cancelled_terminal(
                        &terminal,
                        &request,
                        expected_sequence.saturating_sub(1),
                    )?;
                    return Ok(CancelledInferenceResult {
                        chunks,
                        text,
                        cancel_ack: ack,
                        terminal,
                    });
                }
                Some(adapter_frame::Body::InferenceError(error)) => {
                    return self.inference_failure(error, &request)
                }
                Some(adapter_frame::Body::Error(error)) => {
                    return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                        format!("adapter rejected cancellation: {}: {}", error.code, error.message),
                    ))
                }
                _ => {
                    return self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(
                        "cancellable stream",
                    ))
                }
            }
        }
    }

    pub fn cancel_inference(
        &mut self,
        target_request_id: impl Into<String>,
        target_attempt_id: impl Into<String>,
        reason: impl Into<String>,
    ) -> Result<RuntimeHealth, AdapterSupervisorError> {
        self.ensure_io_healthy()?;
        let request_id = target_request_id.into();
        let attempt_id = target_attempt_id.into();
        if request_id.trim().is_empty() || attempt_id.trim().is_empty() {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "cancel request/attempt ids must be non-empty".to_owned(),
            ));
        }
        let frame_id = self.send_inference_cancel_ids(request_id, attempt_id, reason.into())?;
        let response = self.receive_frame(self.policy.request_timeout, "inference cancel")?;
        if response.correlation_id != frame_id || response.frame_id.trim().is_empty() {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "inference cancel response correlation mismatch".to_owned(),
            ));
        }
        match response.body {
            Some(adapter_frame::Body::Health(_)) => self.extract_health(response, "inference cancel"),
            Some(adapter_frame::Body::Error(error)) => self.fail_protocol(
                AdapterSupervisorError::InvalidRuntimeResponse(format!(
                    "inference cancel rejected: {}: {}", error.code, error.message
                )),
            ),
            _ => self.fail_protocol(AdapterSupervisorError::UnexpectedFrame("inference cancel")),
        }
    }

    fn send_inference_cancel(
        &mut self,
        request: &InferenceRequest,
        reason: String,
    ) -> Result<String, AdapterSupervisorError> {
        self.send_inference_cancel_ids(request.request_id.clone(), request.attempt_id.clone(), reason)
    }

    fn send_inference_cancel_ids(
        &mut self,
        request_id: String,
        attempt_id: String,
        reason: String,
    ) -> Result<String, AdapterSupervisorError> {
        let frame = self.next_control_frame(
            adapter_frame::Body::InferenceCancel(InferenceCancel {
                contract_version: Some(ContractVersion { major: 1, minor: 2 }),
                target_request_id: request_id,
                target_attempt_id: attempt_id,
                reason,
            }),
            self.policy.request_timeout,
        );
        let frame_id = frame.frame_id.clone();
        self.write_frame(&frame)?;
        Ok(frame_id)
    }

    fn validate_cancelled_terminal(
        &mut self,
        terminal: &InferenceTerminal,
        request: &InferenceRequest,
        expected_final_sequence: u64,
    ) -> Result<(), AdapterSupervisorError> {
        if let Err(error) = validate_contract_version(terminal.contract_version.as_ref()) {
            return self.fail_protocol(error.into());
        }
        let usage_unknown = terminal.usage.as_ref().is_some_and(|usage| {
            InferenceUsageMeasurement::try_from(usage.measurement)
                == Ok(InferenceUsageMeasurement::Unknown)
                && usage.input_tokens.is_none()
                && usage.output_tokens.is_none()
                && usage.total_tokens.is_none()
        });
        if terminal.request_id != request.request_id
            || terminal.attempt_id != request.attempt_id
            || terminal.final_sequence != expected_final_sequence
            || InferenceFinishReason::try_from(terminal.finish_reason)
                != Ok(InferenceFinishReason::Cancelled)
            || !usage_unknown
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "invalid cancelled terminal identity/sequence/finish/usage".to_owned(),
            ));
        }
        Ok(())
    }

'''
    if text.count(method_anchor) != 1:
        raise RuntimeError("adapter cancel method anchor mismatch")
    text = text.replace(method_anchor, methods + method_anchor, 1)
    return text


def patch_fake(text: str) -> str:
    start = '    if mode.startswith("stream-"):\n'
    end = '    while True:\n'
    new = r'''    if mode.startswith("stream-"):
        envelope = read_frame()
        if envelope is None or envelope.WhichOneof("body") != "inference_request":
            return 65
        request = envelope.inference_request
        first = stream_chunk(request, 1, "hé")
        second = stream_chunk(request, 2, "llo")
        terminal = stream_terminal(request, 2)
        for value in (first, second, terminal):
            value.correlation_id = envelope.frame_id

        def cancelled(final_sequence: int) -> adapter_pb2.AdapterFrame:
            body = inference_pb2.InferenceTerminal(
                contract_version=inference_version(),
                request_id=request.request_id,
                attempt_id=request.attempt_id,
                final_sequence=final_sequence,
                finish_reason=inference_pb2.INFERENCE_FINISH_REASON_CANCELLED,
                usage=inference_pb2.InferenceUsage(
                    measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN
                ),
            )
            return frame(
                "stream-cancelled",
                "inference_terminal",
                body,
                correlation_id=envelope.frame_id,
            )

        def read_cancel() -> adapter_pb2.AdapterFrame:
            cancel = read_frame()
            if cancel is None or cancel.WhichOneof("body") != "inference_cancel":
                raise SystemExit(93)
            return cancel

        def ack_cancel(cancel: adapter_pb2.AdapterFrame) -> None:
            write_frame(
                frame(
                    f"cancel-ack:{cancel.frame_id}",
                    "health",
                    health(runtime_pb2.RUNTIME_HEALTH_STATUS_READY),
                    correlation_id=cancel.frame_id,
                )
            )

        if mode == "stream-cancel-before":
            cancel = read_cancel()
            if (
                cancel.inference_cancel.target_request_id != request.request_id
                or cancel.inference_cancel.target_attempt_id != request.attempt_id
            ):
                return 94
            ack_cancel(cancel)
            write_frame(cancelled(0))
            return 0
        if mode == "stream-cancel-during":
            write_frame(first)
            cancel = read_cancel()
            if (
                cancel.inference_cancel.target_request_id != request.request_id
                or cancel.inference_cancel.target_attempt_id != request.attempt_id
            ):
                return 94
            ack_cancel(cancel)
            write_frame(cancelled(1))
            return 0
        if mode == "stream-cancel-after-terminal":
            one_terminal = stream_terminal(request, 1)
            one_terminal.correlation_id = envelope.frame_id
            write_coalesced(first, one_terminal)
            cancel = read_cancel()
            error = adapter_pb2.AdapterError(
                code="CANCEL_AFTER_TERMINAL",
                message="inference already terminal",
                retryable=False,
            )
            write_frame(
                frame(
                    f"cancel-error:{cancel.frame_id}",
                    "error",
                    error,
                    correlation_id=cancel.frame_id,
                )
            )
            return 0
        if mode == "stream-valid":
            write_fragmented_utf8_frame(first)
            write_coalesced(second, terminal)
            return 0
        if mode == "stream-duplicate":
            duplicate = stream_chunk(request, 1, "duplicate")
            duplicate.correlation_id = envelope.frame_id
            write_coalesced(first, duplicate, terminal)
            return 0
        if mode == "stream-reordered":
            write_coalesced(second, terminal)
            return 0
        if mode == "stream-eof":
            write_frame(first)
            return 0
        return 66

'''
    return replace_between(text, start, end, new, "fake streaming branch")


def patch_tests(text: str) -> str:
    anchor = "#[test]\nfn real_openjarvis_unary_inference_uses_pinned_llamacpp_lane() {\n"
    tests = r'''#[test]
fn cancel_before_first_chunk_requires_ack_and_cancelled_terminal() {
    let command = fake_command("stream-cancel-before");
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())
        .expect("connect cancel-before fake sidecar");
    let result = supervisor
        .infer_stream_cancel_after_sequence(fake_stream_request(), 0, "operator cancel")
        .expect("cancel-before must be acknowledged and terminated");
    assert!(result.chunks.is_empty());
    assert!(result.text.is_empty());
    assert_eq!(result.cancel_ack.status, RuntimeHealthStatus::Ready as i32);
    assert_eq!(result.terminal.final_sequence, 0);
    assert_eq!(
        InferenceFinishReason::try_from(result.terminal.finish_reason),
        Ok(InferenceFinishReason::Cancelled)
    );
    assert!(!supervisor.is_poisoned());
}

#[test]
fn cancel_during_stream_preserves_prior_chunks_and_stops_locally() {
    let command = fake_command("stream-cancel-during");
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())
        .expect("connect cancel-during fake sidecar");
    let result = supervisor
        .infer_stream_cancel_after_sequence(fake_stream_request(), 1, "operator cancel")
        .expect("cancel-during must be acknowledged and terminated");
    assert_eq!(result.chunks.len(), 1);
    assert_eq!(result.text, "hé");
    assert_eq!(result.terminal.final_sequence, 1);
    assert_eq!(
        InferenceFinishReason::try_from(result.terminal.finish_reason),
        Ok(InferenceFinishReason::Cancelled)
    );
    assert_eq!(result.cancel_ack.status, RuntimeHealthStatus::Ready as i32);
}

#[test]
fn cancel_after_terminal_is_rejected_not_relabelled_success() {
    let command = fake_command("stream-cancel-after-terminal");
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())
        .expect("connect post-terminal fake sidecar");
    let result = supervisor
        .infer_stream(fake_stream_request())
        .expect("stream must first reach its real terminal");
    assert_eq!(
        InferenceFinishReason::try_from(result.terminal.finish_reason),
        Ok(InferenceFinishReason::Stop)
    );
    let error = supervisor
        .cancel_inference("w02-11-request", "w02-11-attempt", "too late")
        .expect_err("post-terminal cancel must be rejected");
    assert!(matches!(error, AdapterSupervisorError::InvalidRuntimeResponse(_)));
    assert!(supervisor.is_poisoned());
}

'''
    if text.count(anchor) != 1:
        raise RuntimeError("adapter test insertion anchor mismatch")
    return text.replace(anchor, tests + anchor, 1)


def apply() -> None:
    targets = {
        ROOT / "adapters/openjarvis/sidecar.py": patch_sidecar,
        ROOT / "kernel/crates/clever-kernel/src/adapter.rs": patch_adapter,
        ROOT / "kernel/crates/clever-kernel/tests/fixtures/fake_adapter_sidecar.py": patch_fake,
        ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs": patch_tests,
    }
    for path, fn in targets.items():
        before = path.read_text(encoding="utf-8")
        after = fn(before)
        if before == after:
            raise RuntimeError(f"{path}: patch produced no delta")
        path.write_text(after, encoding="utf-8")


def check() -> None:
    sidecar = (ROOT / "adapters/openjarvis/sidecar.py").read_text(encoding="utf-8")
    adapter = (ROOT / "kernel/crates/clever-kernel/src/adapter.rs").read_text(encoding="utf-8")
    fake = (ROOT / "kernel/crates/clever-kernel/tests/fixtures/fake_adapter_sidecar.py").read_text(encoding="utf-8")
    tests = (ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs").read_text(encoding="utf-8")
    required = [
        (sidecar, "start_stream_worker"),
        (sidecar, 'body == "inference_cancel"'),
        (sidecar, "terminate_worker_bounded(active)"),
        (adapter, "infer_stream_cancel_after_sequence"),
        (adapter, "InferenceFinishReason::Cancelled"),
        (fake, 'mode == "stream-cancel-before"'),
        (fake, 'mode == "stream-cancel-during"'),
        (fake, 'mode == "stream-cancel-after-terminal"'),
        (tests, "cancel_before_first_chunk_requires_ack_and_cancelled_terminal"),
        (tests, "cancel_after_terminal_is_rejected_not_relabelled_success"),
    ]
    missing = [needle for haystack, needle in required if needle not in haystack]
    if missing:
        raise RuntimeError(f"W02-12 generated source contract missing: {missing}")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"--apply", "--check"}:
        raise SystemExit("usage: w02_cancel_patch.py --apply|--check")
    if sys.argv[1] == "--apply":
        apply()
    else:
        check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
