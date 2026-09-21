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
        "from clever.v1 import adapter_pb2, common_pb2, runtime_pb2\n",
        "from clever.v1 import adapter_pb2, common_pb2, inference_pb2, runtime_pb2\n",
        "sidecar protobuf imports",
    )
    text = replace_once(
        text,
        "from adapters.openjarvis import ADAPTER_ID, RUNTIME_ID, UPSTREAM_COMMIT, UPSTREAM_REPOSITORY\n",
        "from adapters.openjarvis import ADAPTER_ID, RUNTIME_ID, UPSTREAM_COMMIT, UPSTREAM_REPOSITORY\nfrom adapters.openjarvis.unary_inference import UnaryInferenceRejected, execute_unary\n",
        "sidecar unary executor import",
    )
    text = replace_once(
        text,
        '            "shutdown",\n        ],\n',
        '            "shutdown",\n            "unary-inference",\n        ],\n',
        "sidecar hello feature",
    )
    text = replace_once(
        text,
        '''        elif body == "shutdown":\n            seconds, nanos = _now_timestamp()\n''',
        '''        elif body == "inference_request":\n            native_request = request.inference_request\n            try:\n                outcome = execute_unary(native_request)\n            except UnaryInferenceRejected as exc:\n                failure = inference_pb2.InferenceError(\n                    contract_version=common_pb2.ContractVersion(major=1, minor=2),\n                    request_id=native_request.request_id,\n                    attempt_id=native_request.attempt_id,\n                    code=exc.code,\n                    message=str(exc),\n                    retryable=exc.retryable,\n                )\n                write_frame(\n                    stdout,\n                    _frame(\n                        f"inference-error:{request.frame_id}",\n                        "inference_error",\n                        failure,\n                        correlation_id=request.frame_id,\n                    ),\n                )\n                continue\n            write_frame(\n                stdout,\n                _frame(\n                    f"inference-chunk:{request.frame_id}",\n                    "inference_chunk",\n                    outcome.chunk,\n                    correlation_id=request.frame_id,\n                ),\n            )\n            write_frame(\n                stdout,\n                _frame(\n                    f"inference-terminal:{request.frame_id}",\n                    "inference_terminal",\n                    outcome.terminal,\n                    correlation_id=request.frame_id,\n                ),\n            )\n        elif body == "shutdown":\n            seconds, nanos = _now_timestamp()\n''',
        "sidecar inference dispatch",
    )
    return text


def patch_adapter(text: str) -> str:
    text = replace_once(
        text,
        '''    AdapterShutdown, CapabilityDescriptor, ContractVersion, LifecycleMode, NativeRegistryEntry,\n    PlatformConstraint, ProvenanceRef, RegistryPrimitive, RegistrySnapshot,\n    RegistrySnapshotRequest, RuntimeHealth, RuntimeHealthStatus, RuntimeOwner,\n''',
        '''    AdapterShutdown, CapabilityDescriptor, ContractVersion, InferenceChunk, InferenceError,\n    InferenceFinishReason, InferenceRequest, InferenceTerminal, InferenceUsageMeasurement,\n    LifecycleMode, NativeRegistryEntry, PlatformConstraint, PrincipalRef, ProvenanceRef,\n    RegistryPrimitive, RegistrySnapshot, RegistrySnapshotRequest, RuntimeHealth,\n    RuntimeHealthStatus, RuntimeOwner,\n''',
        "adapter inference contract imports",
    )
    text = replace_once(
        text,
        '''use crate::{\n    capabilities::CapabilityRegistry, error::KernelError, version::validate_contract_version,\n};\n''',
        '''use crate::{\n    capabilities::CapabilityRegistry,\n    error::KernelError,\n    inference_security::{\n        authorize_inference_egress, InferenceReservation, InferenceTarget,\n    },\n    version::validate_contract_version,\n};\n''',
        "adapter inference security imports",
    )
    text = replace_once(
        text,
        '''const REQUIRED_FEATURES: [&str; 5] = [\n    "be32-length-prefix",\n    "registry-snapshot",\n    "runtime-health",\n    "cancel",\n    "shutdown",\n];\n''',
        '''const REQUIRED_FEATURES: [&str; 5] = [\n    "be32-length-prefix",\n    "registry-snapshot",\n    "runtime-health",\n    "cancel",\n    "shutdown",\n];\nconst OPTIONAL_FEATURES: [&str; 1] = ["unary-inference"];\nconst W02_UNARY_ENGINE_ID: &str = "llamacpp";\nconst W02_UNARY_MODEL_ID: &str = "qwen3:0.6b";\n''',
        "adapter optional unary feature",
    )
    text = replace_once(
        text,
        '''    InvalidRuntimeResponse(String),\n    RestartBudgetExhausted { attempts: u32, last_error: String },\n''',
        '''    InvalidRuntimeResponse(String),\n    InvalidInferenceRequest(String),\n    InferenceFailed { code: i32, message: String, retryable: bool },\n    RestartBudgetExhausted { attempts: u32, last_error: String },\n''',
        "adapter inference error variants",
    )
    text = replace_once(
        text,
        '''            Self::InvalidRuntimeResponse(message) => {\n                write!(formatter, "invalid runtime response: {message}")\n            }\n            Self::RestartBudgetExhausted {\n''',
        '''            Self::InvalidRuntimeResponse(message) => {\n                write!(formatter, "invalid runtime response: {message}")\n            }\n            Self::InvalidInferenceRequest(message) => {\n                write!(formatter, "invalid inference request: {message}")\n            }\n            Self::InferenceFailed { code, message, retryable } => write!(\n                formatter,\n                "inference failed code={code} retryable={retryable}: {message}"\n            ),\n            Self::RestartBudgetExhausted {\n''',
        "adapter inference error display",
    )
    text = replace_once(
        text,
        '''struct WriterRequest {\n    bytes: Vec<u8>,\n    completion: SyncSender<Result<(), AdapterSupervisorError>>,\n}\n''',
        '''struct WriterRequest {\n    bytes: Vec<u8>,\n    completion: SyncSender<Result<(), AdapterSupervisorError>>,\n}\n\n#[derive(Debug, Clone, PartialEq)]\npub struct UnaryInferenceResult {\n    pub text: String,\n    pub terminal: InferenceTerminal,\n}\n''',
        "adapter unary result type",
    )
    text = replace_once(
        text,
        '''        let negotiated = REQUIRED_FEATURES\n            .iter()\n            .map(|feature| (*feature).to_owned())\n            .collect();\n        Ok((peer_max.min(self.policy.max_frame_bytes), negotiated))\n''',
        '''        let mut negotiated: BTreeSet<String> = REQUIRED_FEATURES\n            .iter()\n            .map(|feature| (*feature).to_owned())\n            .collect();\n        for optional in OPTIONAL_FEATURES {\n            if advertised.contains(optional) {\n                negotiated.insert(optional.to_owned());\n            }\n        }\n        Ok((peer_max.min(self.policy.max_frame_bytes), negotiated))\n''',
        "adapter unary feature negotiation",
    )
    anchor = '''    pub fn shutdown(\n        mut self,\n        reason: impl Into<String>,\n    ) -> Result<RuntimeHealth, AdapterSupervisorError> {\n'''
    method = '''    pub fn infer_unary(\n        &mut self,\n        request: InferenceRequest,\n    ) -> Result<UnaryInferenceResult, AdapterSupervisorError> {\n        self.ensure_io_healthy()?;\n        if !self.negotiated_features.contains("unary-inference") {\n            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(\n                "peer did not negotiate unary-inference".to_owned(),\n            ));\n        }\n        let reservation = InferenceReservation {\n            estimated_input_tokens: 0,\n            estimated_cost_microusd: 0,\n        };\n        let local_target = InferenceTarget {\n            provider_id: "openjarvis.llamacpp".to_owned(),\n            origin: "loopback".to_owned(),\n            external: false,\n        };\n        authorize_inference_egress(&request, &local_target, None, &reservation, 0).map_err(\n            |error| AdapterSupervisorError::InvalidInferenceRequest(error.to_string()),\n        )?;\n        let config = request.config.as_ref().ok_or_else(|| {\n            AdapterSupervisorError::InvalidInferenceRequest("config is required".to_owned())\n        })?;\n        if request.engine_id != W02_UNARY_ENGINE_ID\n            || request.model_id != W02_UNARY_MODEL_ID\n            || request.idempotency_key.trim().is_empty()\n            || request.inputs.is_empty()\n            || request.deadline_at.is_none()\n            || config.stream\n            || config.max_output_tokens == 0\n            || config.max_output_tokens > 256\n            || request\n                .inputs\n                .iter()\n                .any(|input| input.role == 0 || input.content.trim().is_empty())\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(\n                "request is outside the bounded W02-10 unary lane".to_owned(),\n            ));\n        }\n\n        let frame = self.next_control_frame(\n            adapter_frame::Body::InferenceRequest(request.clone()),\n            self.policy.request_timeout,\n        );\n        let frame_id = frame.frame_id.clone();\n        if let Err(error) = self.write_frame(&frame) {\n            return self.fail_protocol(error);\n        }\n\n        let first = match self.receive_frame(self.policy.request_timeout, "unary inference chunk") {\n            Ok(response) => response,\n            Err(error) => return self.fail_protocol(error),\n        };\n        self.validate_inference_outer(&first, &frame_id)?;\n        let chunk = match first.body {\n            Some(adapter_frame::Body::InferenceChunk(chunk)) => chunk,\n            Some(adapter_frame::Body::InferenceError(error)) => {\n                return self.inference_failure(error, &request)\n            }\n            _ => {\n                return self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(\n                    "unary inference chunk",\n                ))\n            }\n        };\n        self.validate_inference_chunk(&chunk, &request)?;\n\n        let second = match self.receive_frame(self.policy.request_timeout, "unary inference terminal") {\n            Ok(response) => response,\n            Err(error) => return self.fail_protocol(error),\n        };\n        self.validate_inference_outer(&second, &frame_id)?;\n        let terminal = match second.body {\n            Some(adapter_frame::Body::InferenceTerminal(terminal)) => terminal,\n            Some(adapter_frame::Body::InferenceError(error)) => {\n                return self.inference_failure(error, &request)\n            }\n            _ => {\n                return self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(\n                    "unary inference terminal",\n                ))\n            }\n        };\n        self.validate_inference_terminal(&terminal, &request)?;\n        Ok(UnaryInferenceResult {\n            text: chunk.text_delta,\n            terminal,\n        })\n    }\n\n    fn validate_inference_outer(\n        &mut self,\n        frame: &AdapterFrame,\n        request_frame_id: &str,\n    ) -> Result<(), AdapterSupervisorError> {\n        if frame.frame_id.trim().is_empty() || frame.correlation_id != request_frame_id {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                "inference response correlation mismatch".to_owned(),\n            ));\n        }\n        Ok(())\n    }\n\n    fn validate_inference_chunk(\n        &mut self,\n        chunk: &InferenceChunk,\n        request: &InferenceRequest,\n    ) -> Result<(), AdapterSupervisorError> {\n        if let Err(error) = validate_contract_version(chunk.contract_version.as_ref()) {\n            return self.fail_protocol(error.into());\n        }\n        if chunk.request_id != request.request_id\n            || chunk.attempt_id != request.attempt_id\n            || chunk.sequence != 1\n            || chunk.text_delta.trim().is_empty()\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                "invalid unary inference chunk identity/sequence/content".to_owned(),\n            ));\n        }\n        Ok(())\n    }\n\n    fn validate_inference_terminal(\n        &mut self,\n        terminal: &InferenceTerminal,\n        request: &InferenceRequest,\n    ) -> Result<(), AdapterSupervisorError> {\n        if let Err(error) = validate_contract_version(terminal.contract_version.as_ref()) {\n            return self.fail_protocol(error.into());\n        }\n        let finish = InferenceFinishReason::try_from(terminal.finish_reason).ok();\n        let usage = terminal.usage.as_ref();\n        let measurement = usage\n            .and_then(|value| InferenceUsageMeasurement::try_from(value.measurement).ok());\n        if terminal.request_id != request.request_id\n            || terminal.attempt_id != request.attempt_id\n            || terminal.final_sequence != 1\n            || !matches!(\n                finish,\n                Some(InferenceFinishReason::Stop)\n                    | Some(InferenceFinishReason::Length)\n                    | Some(InferenceFinishReason::ContentFilter)\n            )\n            || measurement != Some(InferenceUsageMeasurement::Exact)\n            || usage.is_none_or(|value| {\n                value.input_tokens.is_none()\n                    || value.output_tokens.is_none()\n                    || value.total_tokens.is_none()\n            })\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                "invalid unary inference terminal identity/finish/usage".to_owned(),\n            ));\n        }\n        Ok(())\n    }\n\n    fn inference_failure<T>(\n        &mut self,\n        error: InferenceError,\n        request: &InferenceRequest,\n    ) -> Result<T, AdapterSupervisorError> {\n        if error.request_id != request.request_id || error.attempt_id != request.attempt_id {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                "inference error identity mismatch".to_owned(),\n            ));\n        }\n        self.fail_protocol(AdapterSupervisorError::InferenceFailed {\n            code: error.code,\n            message: error.message,\n            retryable: error.retryable,\n        })\n    }\n\n'''
    if method not in text:
        count = text.count(anchor)
        if count != 1:
            raise RuntimeError(f"adapter unary method anchor: expected one, found {count}")
        text = text.replace(anchor, method + anchor, 1)
    return text


def patch_test(text: str) -> str:
    text = replace_once(
        text,
        '''    thread,\n    time::{Duration, Instant},\n};\n\nuse clever_contracts::{CapabilityAvailability, RuntimeHealthStatus};\n''',
        '''    thread,\n    time::{Duration, Instant, SystemTime, UNIX_EPOCH},\n};\n\nuse clever_contracts::{\n    CapabilityAvailability, ContractVersion, InferenceConfig, InferenceFinishReason,\n    InferenceInput, InferenceRequest, InferenceRole, InferenceUsageMeasurement, PrincipalRef,\n    RuntimeHealthStatus,\n};\n''',
        "adapter test inference imports",
    )
    test = r'''

#[test]
fn real_openjarvis_unary_inference_uses_pinned_llamacpp_lane() {
    let python = required_env("CLEVER_TEST_PYTHON");
    let upstream_src = required_env("CLEVER_OPENJARVIS_SRC");
    let model_path = required_env("CLEVER_W02_MODEL_PATH");
    let llamacpp_host = required_env("LLAMACPP_HOST");
    let root = repo_root();
    let script = root.join("adapters/openjarvis/sidecar.py");
    let generated = root.join("contracts/sdk/python/gen");
    let pythonpath = format!(
        "{}:{}:{}",
        root.display(),
        generated.display(),
        upstream_src
    );
    let mut command = AdapterCommand::new(python);
    command.args = vec![script.display().to_string()];
    command.env = BTreeMap::from([
        ("HOME".to_owned(), "/tmp".to_owned()),
        ("PYTHONPATH".to_owned(), pythonpath),
        ("PYTHONHASHSEED".to_owned(), "0".to_owned()),
        ("CLEVER_W02_MODEL_PATH".to_owned(), model_path),
        ("LLAMACPP_HOST".to_owned(), llamacpp_host),
    ]);
    let identity = AdapterIdentity::new(
        "openjarvis.cognition",
        "openjarvis",
        "https://github.com/open-jarvis/OpenJarvis.git",
        "72033b8ec288aa067ce4530ff9d96bf231e9c4e5",
    );
    let policy = SupervisorPolicy {
        handshake_timeout: Duration::from_secs(20),
        request_timeout: Duration::from_secs(120),
        write_timeout: Duration::from_secs(10),
        shutdown_timeout: Duration::from_secs(5),
        ..SupervisorPolicy::default()
    };
    let mut supervisor = AdapterSupervisor::start(command, identity, policy)
        .expect("connect exact OpenJarvis W02-10 sidecar");
    assert!(supervisor.negotiated_features().contains("unary-inference"));

    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system time after epoch");
    let deadline = now + Duration::from_secs(90);
    let request = InferenceRequest {
        contract_version: Some(ContractVersion { major: 1, minor: 2 }),
        request_id: "w02-10-real-request".to_owned(),
        attempt_id: "w02-10-attempt-1".to_owned(),
        principal: Some(PrincipalRef {
            user_id: "local-test-user".to_owned(),
            device_id: String::new(),
            channel_id: String::new(),
            tenant_id: String::new(),
        }),
        session_id: "w02-10-session".to_owned(),
        engine_id: "llamacpp".to_owned(),
        model_id: "qwen3:0.6b".to_owned(),
        inputs: vec![InferenceInput {
            role: InferenceRole::User as i32,
            content: "Reply with one short sentence stating that the local inference path is ready.".to_owned(),
            name: String::new(),
        }],
        config: Some(InferenceConfig {
            max_output_tokens: 32,
            temperature: Some(0.0),
            top_p: None,
            stop_sequences: Vec::new(),
            stream: false,
        }),
        deadline_at: Some(prost_types::Timestamp {
            seconds: i64::try_from(deadline.as_secs()).expect("deadline seconds fit i64"),
            nanos: i32::try_from(deadline.subsec_nanos()).expect("deadline nanos fit i32"),
        }),
        idempotency_key: "w02-10-idempotency".to_owned(),
    };
    let result = supervisor
        .infer_unary(request)
        .expect("real OpenJarvis unary inference through pinned llama.cpp lane");
    assert!(!result.text.trim().is_empty());
    assert_eq!(result.terminal.request_id, "w02-10-real-request");
    assert_eq!(result.terminal.attempt_id, "w02-10-attempt-1");
    assert_eq!(result.terminal.final_sequence, 1);
    assert!(matches!(
        InferenceFinishReason::try_from(result.terminal.finish_reason),
        Ok(InferenceFinishReason::Stop | InferenceFinishReason::Length | InferenceFinishReason::ContentFilter)
    ));
    let usage = result.terminal.usage.expect("terminal carries usage");
    assert_eq!(
        InferenceUsageMeasurement::try_from(usage.measurement),
        Ok(InferenceUsageMeasurement::Exact)
    );
    assert!(usage.total_tokens.unwrap_or_default() > 0);

    let stopping = supervisor
        .shutdown("W02-10 unary proof complete")
        .expect("sidecar shutdown after real unary inference");
    assert_eq!(stopping.status, RuntimeHealthStatus::Stopping as i32);
}
'''
    if "fn real_openjarvis_unary_inference_uses_pinned_llamacpp_lane()" not in text:
        text += test
    return text


def patch(path: Path, transform) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = transform(original)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.apply == args.check:
        parser.error("choose exactly one of --apply or --check")
    targets = (
        (ROOT / "adapters/openjarvis/sidecar.py", patch_sidecar),
        (ROOT / "kernel/crates/clever-kernel/src/adapter.rs", patch_adapter),
        (ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs", patch_test),
    )
    if args.apply:
        for path, transform in targets:
            patch(path, transform)
        return 0
    for path, transform in targets:
        text = path.read_text(encoding="utf-8")
        if transform(text) != text:
            raise SystemExit(f"W02-10 source contract not applied: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
