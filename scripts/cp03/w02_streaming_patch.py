from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source anchor, found {count}")
    return text.replace(old, new, 1)


def patch_sidecar(text: str) -> str:
    text = replace_once(
        text,
        "from adapters.openjarvis.unary_inference import UnaryInferenceRejected, execute_unary\n",
        "from adapters.openjarvis.streaming_inference import execute_stream\nfrom adapters.openjarvis.unary_inference import UnaryInferenceRejected, execute_unary\n",
        "sidecar streaming import",
    )
    text = replace_once(
        text,
        '            "unary-inference",\n        ],\n',
        '            "unary-inference",\n            "streaming-inference",\n        ],\n',
        "sidecar streaming feature",
    )
    start = text.find('        elif body == "inference_request":\n')
    end = text.find('        elif body == "shutdown":\n', start)
    if start < 0 or end < 0:
        raise RuntimeError("sidecar inference dispatch anchors missing")
    existing = text[start:end]
    if "execute_stream(" in existing:
        return text
    replacement = '''        elif body == "inference_request":\n            native_request = request.inference_request\n            try:\n                if native_request.HasField("config") and native_request.config.stream:\n                    def emit_chunk(chunk: inference_pb2.InferenceChunk) -> None:\n                        write_frame(\n                            stdout,\n                            _frame(\n                                f"inference-chunk:{request.frame_id}:{chunk.sequence}",\n                                "inference_chunk",\n                                chunk,\n                                correlation_id=request.frame_id,\n                            ),\n                        )\n\n                    def emit_terminal(terminal: inference_pb2.InferenceTerminal) -> None:\n                        write_frame(\n                            stdout,\n                            _frame(\n                                f"inference-terminal:{request.frame_id}",\n                                "inference_terminal",\n                                terminal,\n                                correlation_id=request.frame_id,\n                            ),\n                        )\n\n                    execute_stream(\n                        native_request,\n                        emit_chunk=emit_chunk,\n                        emit_terminal=emit_terminal,\n                    )\n                    continue\n\n                outcome = execute_unary(native_request)\n            except UnaryInferenceRejected as exc:\n                failure = inference_pb2.InferenceError(\n                    contract_version=common_pb2.ContractVersion(major=1, minor=2),\n                    request_id=native_request.request_id,\n                    attempt_id=native_request.attempt_id,\n                    code=exc.code,\n                    message=str(exc),\n                    retryable=exc.retryable,\n                )\n                write_frame(\n                    stdout,\n                    _frame(\n                        f"inference-error:{request.frame_id}",\n                        "inference_error",\n                        failure,\n                        correlation_id=request.frame_id,\n                    ),\n                )\n                continue\n            write_frame(\n                stdout,\n                _frame(\n                    f"inference-chunk:{request.frame_id}",\n                    "inference_chunk",\n                    outcome.chunk,\n                    correlation_id=request.frame_id,\n                ),\n            )\n            write_frame(\n                stdout,\n                _frame(\n                    f"inference-terminal:{request.frame_id}",\n                    "inference_terminal",\n                    outcome.terminal,\n                    correlation_id=request.frame_id,\n                ),\n            )\n'''
    return text[:start] + replacement + text[end:]


def patch_fake_sidecar(text: str) -> str:
    text = replace_once(
        text,
        "from clever.v1 import adapter_pb2, common_pb2, runtime_pb2\n",
        "from clever.v1 import adapter_pb2, common_pb2, inference_pb2, runtime_pb2\n",
        "fake inference import",
    )
    helpers_anchor = '''def write_frame(frame: adapter_pb2.AdapterFrame) -> None:\n    payload = frame.SerializeToString(deterministic=True)\n    sys.stdout.buffer.write(struct.pack(\">I\", len(payload)))\n    sys.stdout.buffer.write(payload)\n    sys.stdout.buffer.flush()\n\n\n'''
    helpers = helpers_anchor + '''def framed_bytes(value: adapter_pb2.AdapterFrame) -> bytes:\n    payload = value.SerializeToString(deterministic=True)\n    return struct.pack(\">I\", len(payload)) + payload\n\n\ndef write_fragmented_utf8_frame(value: adapter_pb2.AdapterFrame) -> None:\n    wire = framed_bytes(value)\n    needle = \"hé\".encode(\"utf-8\")\n    index = wire.find(needle)\n    if index < 0:\n        raise SystemExit(92)\n    split = index + 2  # after ASCII h plus first byte (0xc3) of é\n    sys.stdout.buffer.write(wire[:split])\n    sys.stdout.buffer.flush()\n    time.sleep(0.01)\n    sys.stdout.buffer.write(wire[split:])\n    sys.stdout.buffer.flush()\n\n\ndef write_coalesced(*values: adapter_pb2.AdapterFrame) -> None:\n    sys.stdout.buffer.write(b\"\".join(framed_bytes(value) for value in values))\n    sys.stdout.buffer.flush()\n\n\ndef inference_version() -> common_pb2.ContractVersion:\n    return common_pb2.ContractVersion(major=1, minor=2)\n\n\ndef stream_chunk(request, sequence: int, text: str) -> adapter_pb2.AdapterFrame:\n    body = inference_pb2.InferenceChunk(\n        contract_version=inference_version(),\n        request_id=request.request_id,\n        attempt_id=request.attempt_id,\n        sequence=sequence,\n        text_delta=text,\n    )\n    return frame(\n        f\"stream-chunk-{sequence}\",\n        \"inference_chunk\",\n        body,\n        correlation_id=\"__REQUEST_FRAME__\",\n    )\n\n\ndef stream_terminal(request, final_sequence: int) -> adapter_pb2.AdapterFrame:\n    body = inference_pb2.InferenceTerminal(\n        contract_version=inference_version(),\n        request_id=request.request_id,\n        attempt_id=request.attempt_id,\n        final_sequence=final_sequence,\n        finish_reason=inference_pb2.INFERENCE_FINISH_REASON_STOP,\n        usage=inference_pb2.InferenceUsage(\n            measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN\n        ),\n    )\n    return frame(\n        \"stream-terminal\",\n        \"inference_terminal\",\n        body,\n        correlation_id=\"__REQUEST_FRAME__\",\n    )\n\n\n'''
    text = replace_once(text, helpers_anchor, helpers, "fake stream helpers")
    text = replace_once(
        text,
        '            "shutdown",\n        ],\n',
        '            "shutdown",\n            "unary-inference",\n            "streaming-inference",\n        ],\n',
        "fake streaming features",
    )
    mode_anchor = '''    if mode == "no-read-after-hello":\n        time.sleep(5)\n        return 0\n\n    while True:\n'''
    mode_block = '''    if mode == "no-read-after-hello":\n        time.sleep(5)\n        return 0\n\n    if mode.startswith("stream-"):\n        envelope = read_frame()\n        if envelope is None or envelope.WhichOneof("body") != "inference_request":\n            return 65\n        request = envelope.inference_request\n        first = stream_chunk(request, 1, "hé")\n        second = stream_chunk(request, 2, "llo")\n        terminal = stream_terminal(request, 2)\n        for value in (first, second, terminal):\n            value.correlation_id = envelope.frame_id\n        if mode == "stream-valid":\n            write_fragmented_utf8_frame(first)\n            write_coalesced(second, terminal)\n            return 0\n        if mode == "stream-duplicate":\n            duplicate = stream_chunk(request, 1, "duplicate")\n            duplicate.correlation_id = envelope.frame_id\n            write_coalesced(first, duplicate, terminal)\n            return 0\n        if mode == "stream-reordered":\n            write_coalesced(second, terminal)\n            return 0\n        if mode == "stream-eof":\n            write_frame(first)\n            return 0\n        return 66\n\n    while True:\n'''
    return replace_once(text, mode_anchor, mode_block, "fake stream adversarial modes")


def patch_adapter(text: str) -> str:
    text = replace_once(
        text,
        'const OPTIONAL_FEATURES: [&str; 1] = ["unary-inference"];\n',
        'const OPTIONAL_FEATURES: [&str; 2] = ["unary-inference", "streaming-inference"];\n',
        "adapter streaming feature",
    )
    result_anchor = '''#[derive(Debug, Clone, PartialEq)]\npub struct UnaryInferenceResult {\n    pub text: String,\n    pub terminal: InferenceTerminal,\n}\n'''
    result_block = result_anchor + '''\n#[derive(Debug, Clone, PartialEq)]\npub struct StreamingInferenceResult {\n    pub chunks: Vec<InferenceChunk>,\n    pub text: String,\n    pub terminal: InferenceTerminal,\n}\n'''
    text = replace_once(text, result_anchor, result_block, "adapter streaming result")

    method_anchor = '''    fn validate_inference_outer(\n        &mut self,\n        frame: &AdapterFrame,\n        request_frame_id: &str,\n    ) -> Result<(), AdapterSupervisorError> {\n'''
    method = '''    pub fn infer_stream(\n        &mut self,\n        request: InferenceRequest,\n    ) -> Result<StreamingInferenceResult, AdapterSupervisorError> {\n        self.ensure_io_healthy()?;\n        if !self.negotiated_features.contains("streaming-inference") {\n            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(\n                "peer did not negotiate streaming-inference".to_owned(),\n            ));\n        }\n        let reservation = InferenceReservation {\n            estimated_input_tokens: 0,\n            estimated_cost_microusd: 0,\n        };\n        let local_target = InferenceTarget {\n            provider_id: "openjarvis.llamacpp".to_owned(),\n            origin: "loopback".to_owned(),\n            external: false,\n        };\n        authorize_inference_egress(&request, &local_target, None, &reservation, 0)\n            .map_err(|error| AdapterSupervisorError::InvalidInferenceRequest(error.to_string()))?;\n        let config = request.config.as_ref().ok_or_else(|| {\n            AdapterSupervisorError::InvalidInferenceRequest("config is required".to_owned())\n        })?;\n        if request.engine_id != W02_UNARY_ENGINE_ID\n            || request.model_id != W02_UNARY_MODEL_ID\n            || request.idempotency_key.trim().is_empty()\n            || request.inputs.is_empty()\n            || request.deadline_at.is_none()\n            || !config.stream\n            || config.max_output_tokens == 0\n            || config.max_output_tokens > 256\n            || request\n                .inputs\n                .iter()\n                .any(|input| input.role == 0 || input.content.trim().is_empty())\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(\n                "request is outside the bounded W02-11 streaming lane".to_owned(),\n            ));\n        }\n\n        let frame = self.next_control_frame(\n            adapter_frame::Body::InferenceRequest(request.clone()),\n            self.policy.request_timeout,\n        );\n        let frame_id = frame.frame_id.clone();\n        if let Err(error) = self.write_frame(&frame) {\n            return self.fail_protocol(error);\n        }\n\n        let mut chunks = Vec::new();\n        let mut text = String::new();\n        let mut expected_sequence = 1_u64;\n        loop {\n            let response = match self.receive_frame(\n                self.policy.request_timeout,\n                "streaming inference",\n            ) {\n                Ok(response) => response,\n                Err(error) => return self.fail_protocol(error),\n            };\n            self.validate_inference_outer(&response, &frame_id)?;\n            match response.body {\n                Some(adapter_frame::Body::InferenceChunk(chunk)) => {\n                    self.validate_stream_chunk(&chunk, &request, expected_sequence)?;\n                    text.push_str(&chunk.text_delta);\n                    chunks.push(chunk);\n                    expected_sequence = expected_sequence.saturating_add(1);\n                }\n                Some(adapter_frame::Body::InferenceTerminal(terminal)) => {\n                    if chunks.is_empty() {\n                        return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                            "stream terminal arrived before any content chunk".to_owned(),\n                        ));\n                    }\n                    let final_sequence = expected_sequence.saturating_sub(1);\n                    self.validate_stream_terminal(&terminal, &request, final_sequence)?;\n                    return Ok(StreamingInferenceResult {\n                        chunks,\n                        text,\n                        terminal,\n                    });\n                }\n                Some(adapter_frame::Body::InferenceError(error)) => {\n                    return self.inference_failure(error, &request)\n                }\n                _ => {\n                    return self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(\n                        "streaming inference",\n                    ))\n                }\n            }\n        }\n    }\n\n    fn validate_stream_chunk(\n        &mut self,\n        chunk: &InferenceChunk,\n        request: &InferenceRequest,\n        expected_sequence: u64,\n    ) -> Result<(), AdapterSupervisorError> {\n        if let Err(error) = validate_contract_version(chunk.contract_version.as_ref()) {\n            return self.fail_protocol(error.into());\n        }\n        if chunk.request_id != request.request_id\n            || chunk.attempt_id != request.attempt_id\n            || chunk.sequence != expected_sequence\n            || chunk.text_delta.is_empty()\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(format!(\n                "invalid streaming chunk identity/sequence/content: expected sequence {expected_sequence}"\n            )));\n        }\n        Ok(())\n    }\n\n    fn validate_stream_terminal(\n        &mut self,\n        terminal: &InferenceTerminal,\n        request: &InferenceRequest,\n        expected_final_sequence: u64,\n    ) -> Result<(), AdapterSupervisorError> {\n        if let Err(error) = validate_contract_version(terminal.contract_version.as_ref()) {\n            return self.fail_protocol(error.into());\n        }\n        let finish = InferenceFinishReason::try_from(terminal.finish_reason).ok();\n        let usage = terminal.usage.as_ref();\n        let measurement =\n            usage.and_then(|value| InferenceUsageMeasurement::try_from(value.measurement).ok());\n        let usage_valid = match (measurement, usage) {\n            (Some(InferenceUsageMeasurement::Exact), Some(value)) => {\n                value.input_tokens.is_some()\n                    && value.output_tokens.is_some()\n                    && value.total_tokens.is_some()\n            }\n            (Some(InferenceUsageMeasurement::Unknown), Some(value)) => {\n                value.input_tokens.is_none()\n                    && value.output_tokens.is_none()\n                    && value.total_tokens.is_none()\n            }\n            _ => false,\n        };\n        if terminal.request_id != request.request_id\n            || terminal.attempt_id != request.attempt_id\n            || terminal.final_sequence != expected_final_sequence\n            || !matches!(\n                finish,\n                Some(InferenceFinishReason::Unspecified)\n                    | Some(InferenceFinishReason::Stop)\n                    | Some(InferenceFinishReason::Length)\n                    | Some(InferenceFinishReason::ContentFilter)\n            )\n            || !usage_valid\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                "invalid streaming terminal identity/sequence/finish/usage".to_owned(),\n            ));\n        }\n        Ok(())\n    }\n\n'''
    if "pub fn infer_stream(" not in text:
        count = text.count(method_anchor)
        if count != 1:
            raise RuntimeError(f"adapter infer_stream anchor: expected one, found {count}")
        text = text.replace(method_anchor, method + method_anchor, 1)
    return text


def patch_adapter_tests(text: str) -> str:
    helper_anchor = '''fn fast_policy() -> SupervisorPolicy {\n    SupervisorPolicy {\n        handshake_timeout: Duration::from_millis(300),\n        request_timeout: Duration::from_millis(500),\n        restart_backoff: Duration::from_millis(5),\n        ..SupervisorPolicy::default()\n    }\n}\n'''
    helper_block = helper_anchor + '''\nfn fake_stream_request() -> InferenceRequest {\n    let now = SystemTime::now()\n        .duration_since(UNIX_EPOCH)\n        .expect("system time after epoch");\n    let deadline = now + Duration::from_secs(10);\n    InferenceRequest {\n        contract_version: Some(ContractVersion { major: 1, minor: 2 }),\n        request_id: "w02-11-request".to_owned(),\n        attempt_id: "w02-11-attempt".to_owned(),\n        principal: Some(PrincipalRef {\n            user_id: "local-test-user".to_owned(),\n            device_id: String::new(),\n            channel_id: String::new(),\n            tenant_id: String::new(),\n        }),\n        session_id: "w02-11-session".to_owned(),\n        engine_id: "llamacpp".to_owned(),\n        model_id: "qwen3:0.6b".to_owned(),\n        inputs: vec![InferenceInput {\n            role: InferenceRole::User as i32,\n            content: "stream utf8".to_owned(),\n            name: String::new(),\n        }],\n        config: Some(InferenceConfig {\n            max_output_tokens: 16,\n            temperature: Some(0.0),\n            top_p: None,\n            stop_sequences: Vec::new(),\n            stream: true,\n        }),\n        deadline_at: Some(prost_types::Timestamp {\n            seconds: i64::try_from(deadline.as_secs()).expect("deadline seconds fit i64"),\n            nanos: i32::try_from(deadline.subsec_nanos()).expect("deadline nanos fit i32"),\n        }),\n        idempotency_key: "w02-11-idempotency".to_owned(),\n    }\n}\n'''
    text = replace_once(text, helper_anchor, helper_block, "adapter test stream request helper")
    test_anchor = '''#[test]\nfn real_openjarvis_unary_inference_uses_pinned_llamacpp_lane() {\n'''
    tests = '''#[test]\nfn stream_handles_fragmented_coalesced_utf8_and_single_terminal() {\n    let command = fake_command("stream-valid");\n    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())\n        .expect("connect streaming fake sidecar");\n    assert!(supervisor\n        .negotiated_features()\n        .contains("streaming-inference"));\n    let result = supervisor\n        .infer_stream(fake_stream_request())\n        .expect("fragmented/coalesced UTF-8 stream must succeed");\n    assert_eq!(result.chunks.len(), 2);\n    assert_eq!(result.chunks[0].sequence, 1);\n    assert_eq!(result.chunks[1].sequence, 2);\n    assert_eq!(result.text, "héllo");\n    assert_eq!(result.terminal.final_sequence, 2);\n    assert_eq!(\n        InferenceFinishReason::try_from(result.terminal.finish_reason),\n        Ok(InferenceFinishReason::Stop)\n    );\n    let usage = result.terminal.usage.expect("stream terminal usage");\n    assert_eq!(\n        InferenceUsageMeasurement::try_from(usage.measurement),\n        Ok(InferenceUsageMeasurement::Unknown)\n    );\n    assert!(!supervisor.is_poisoned());\n}\n\n#[test]\nfn stream_duplicate_sequence_fails_closed() {\n    let command = fake_command("stream-duplicate");\n    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())\n        .expect("connect duplicate stream sidecar");\n    let error = supervisor\n        .infer_stream(fake_stream_request())\n        .expect_err("duplicate sequence must not produce success");\n    assert!(matches!(error, AdapterSupervisorError::InvalidRuntimeResponse(_)));\n    assert!(supervisor.is_poisoned());\n}\n\n#[test]\nfn stream_reordered_sequence_fails_closed() {\n    let command = fake_command("stream-reordered");\n    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())\n        .expect("connect reordered stream sidecar");\n    let error = supervisor\n        .infer_stream(fake_stream_request())\n        .expect_err("reordered sequence must not produce success");\n    assert!(matches!(error, AdapterSupervisorError::InvalidRuntimeResponse(_)));\n    assert!(supervisor.is_poisoned());\n}\n\n#[test]\nfn stream_eof_before_terminal_fails_closed() {\n    let command = fake_command("stream-eof");\n    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())\n        .expect("connect EOF stream sidecar");\n    let error = supervisor\n        .infer_stream(fake_stream_request())\n        .expect_err("EOF before terminal must not produce success");\n    assert_eq!(error, AdapterSupervisorError::ProcessExited);\n    assert!(supervisor.is_poisoned());\n}\n\n'''
    if "stream_handles_fragmented_coalesced_utf8_and_single_terminal" not in text:
        count = text.count(test_anchor)
        if count != 1:
            raise RuntimeError(f"adapter test insertion anchor: expected one, found {count}")
        text = text.replace(test_anchor, tests + test_anchor, 1)
    return text


def patch_plan_tests(text: str) -> str:
    old = '''        else:\n            self.assertEqual(unary["status"], "COMPLETE")\n            self.assertTrue(unary["proof"])\n            self.assertEqual(self.task("W02-11")["status"], "READY")\n            self.assertEqual(self.plan["first_executable_task"], "W02-11")\n'''
    new = '''        else:\n            self.assertEqual(unary["status"], "COMPLETE")\n            self.assertTrue(unary["proof"])\n            frontier = self.task(self.plan["first_executable_task"])\n            self.assertEqual(frontier["status"], "READY")\n            self.assertTrue(\n                all(self.task(dep)["status"] == "COMPLETE" for dep in frontier["depends_on"])\n            )\n'''
    text = replace_once(text, old, new, "plan generic post-G3 frontier")

    old2 = '''        else:\n            expected = "W02-11"\n        self.assertEqual(self.plan["first_executable_task"], expected)\n'''
    new2 = '''        else:\n            expected = self.plan["first_executable_task"]\n        self.assertEqual(self.plan["first_executable_task"], expected)\n'''
    text = replace_once(text, old2, new2, "plan current frontier selection")

    old3 = '''        elif expected == "W02-11":\n            self.assertEqual(unary["status"], "COMPLETE")\n            self.assertTrue(unary["proof"])\n            self.assertEqual(self.task("W02-11")["status"], "READY")\n'''
    new3 = '''        else:\n            self.assertEqual(unary["status"], "COMPLETE")\n            self.assertTrue(unary["proof"])\n            frontier = self.task(expected)\n            self.assertEqual(frontier["status"], "READY")\n            self.assertTrue(\n                all(self.task(dep)["status"] == "COMPLETE" for dep in frontier["depends_on"])\n            )\n'''
    return replace_once(text, old3, new3, "plan generic post-unary assertions")


def apply() -> None:
    targets = {
        ROOT / "adapters/openjarvis/sidecar.py": patch_sidecar,
        ROOT / "kernel/crates/clever-kernel/tests/fixtures/fake_adapter_sidecar.py": patch_fake_sidecar,
        ROOT / "kernel/crates/clever-kernel/src/adapter.rs": patch_adapter,
        ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs": patch_adapter_tests,
        ROOT / "tests/test_cp03_w02_plan.py": patch_plan_tests,
    }
    for path, transform in targets.items():
        before = path.read_text(encoding="utf-8")
        after = transform(before)
        path.write_text(after, encoding="utf-8")


def check() -> None:
    required = {
        ROOT / "adapters/openjarvis/sidecar.py": ["execute_stream(", '"streaming-inference"'],
        ROOT / "kernel/crates/clever-kernel/tests/fixtures/fake_adapter_sidecar.py": [
            'mode == "stream-valid"', "write_fragmented_utf8_frame", "write_coalesced"
        ],
        ROOT / "kernel/crates/clever-kernel/src/adapter.rs": [
            "pub struct StreamingInferenceResult", "pub fn infer_stream(",
            "fn validate_stream_chunk(", "fn validate_stream_terminal(",
        ],
        ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs": [
            "stream_handles_fragmented_coalesced_utf8_and_single_terminal",
            "stream_duplicate_sequence_fails_closed",
            "stream_reordered_sequence_fails_closed",
            "stream_eof_before_terminal_fails_closed",
        ],
        ROOT / "tests/test_cp03_w02_plan.py": ["frontier = self.task(self.plan[\"first_executable_task\"])"]
    }
    for path, needles in required.items():
        text = path.read_text(encoding="utf-8")
        missing = [needle for needle in needles if needle not in text]
        if missing:
            raise RuntimeError(f"{path}: missing W02-11 surfaces {missing}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.apply == args.check:
        parser.error("choose exactly one of --apply or --check")
    if args.apply:
        apply()
    else:
        check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
