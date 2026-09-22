use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::{Display, Formatter},
    io::{Read, Write},
    path::Path,
    process::{Child, ChildStdin, Command, Stdio},
    sync::{
        atomic::{AtomicUsize, Ordering},
        mpsc::{self, Receiver, RecvTimeoutError, SyncSender, TrySendError},
        Arc, Mutex,
    },
    thread::{self, JoinHandle},
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

#[cfg(unix)]
use std::os::unix::process::CommandExt;

use clever_contracts::{
    adapter_frame, AdapterCancel, AdapterFrame, AdapterHealthRequest, AdapterHelloAck,
    AdapterShutdown, CapabilityDescriptor, ContractVersion, InferenceCancel, InferenceChunk,
    InferenceError, InferenceFinishReason, InferenceRequest, InferenceTerminal,
    InferenceUsageMeasurement, LifecycleMode, NativeRegistryEntry, PlatformConstraint,
    PrincipalRef, ProvenanceRef, RegistryPrimitive, RegistrySnapshot, RegistrySnapshotRequest,
    RuntimeHealth, RuntimeHealthStatus, RuntimeOwner,
};
use prost::Message;

use crate::{
    capabilities::CapabilityRegistry,
    error::KernelError,
    inference_fallback::{
        execute_streaming_fallbacks, AttemptReceipt, FallbackCandidate, FallbackHistoryError,
        FallbackPolicy, InferenceTargetClass, StreamingAttemptFailure, StreamingAttemptSuccess,
        StreamingFallbackExecution,
    },
    inference_security::{authorize_inference_egress, InferenceReservation, InferenceTarget},
    version::validate_contract_version,
};

pub const DEFAULT_MAX_FRAME_BYTES: usize = 4 * 1024 * 1024;
pub const DEFAULT_MAX_INBOUND_FRAMES: usize = 64;
pub const DEFAULT_MAX_INBOUND_BYTES: usize = 16 * 1024 * 1024;
const WIRE_MAJOR: u32 = 1;
const WIRE_MINOR: u32 = 1;
const REQUIRED_FEATURES: [&str; 5] = [
    "be32-length-prefix",
    "registry-snapshot",
    "runtime-health",
    "cancel",
    "shutdown",
];
const OPTIONAL_FEATURES: [&str; 3] = [
    "unary-inference",
    "streaming-inference",
    "streaming-cancellation",
];
const W02_UNARY_ENGINE_ID: &str = "llamacpp";
const W02_UNARY_MODEL_ID: &str = "qwen3:0.6b";
const RESERVED_METADATA_TOKENS: [&str; 6] = [
    "permission",
    "scope",
    "risk",
    "policy",
    "authorization",
    "authz",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AdapterSupervisorError {
    Io(String),
    Decode(String),
    InvalidCommand(String),
    FrameTooLarge(usize),
    EmptyFrame,
    TruncatedFrame,
    InboundQueueFull {
        max_frames: usize,
    },
    InboundBytesExceeded {
        attempted: usize,
        max_bytes: usize,
    },
    OutboundQueueFull,
    SessionPoisoned(String),
    Timeout(&'static str),
    ProcessExited,
    UnexpectedFrame(&'static str),
    InvalidHello(String),
    InvalidSnapshot(String),
    InvalidRuntimeResponse(String),
    InvalidInferenceRequest(String),
    InferenceFailed {
        code: i32,
        message: String,
        retryable: bool,
    },
    RestartBudgetExhausted {
        attempts: u32,
        last_error: String,
    },
    Kernel(KernelError),
}

impl Display for AdapterSupervisorError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(message) => write!(formatter, "adapter I/O error: {message}"),
            Self::Decode(message) => write!(formatter, "adapter protobuf decode error: {message}"),
            Self::InvalidCommand(message) => {
                write!(formatter, "invalid adapter command: {message}")
            }
            Self::FrameTooLarge(size) => {
                write!(formatter, "adapter frame exceeds limit: {size} bytes")
            }
            Self::EmptyFrame => write!(formatter, "adapter emitted a zero-length frame"),
            Self::TruncatedFrame => write!(formatter, "adapter emitted a truncated frame"),
            Self::InboundQueueFull { max_frames } => write!(
                formatter,
                "adapter inbound frame queue exceeded {max_frames} frames"
            ),
            Self::InboundBytesExceeded {
                attempted,
                max_bytes,
            } => write!(
                formatter,
                "adapter inbound wire-byte budget exceeded: {attempted} > {max_bytes}"
            ),
            Self::OutboundQueueFull => write!(formatter, "adapter outbound writer queue is full"),
            Self::SessionPoisoned(reason) => {
                write!(formatter, "adapter session is poisoned: {reason}")
            }
            Self::Timeout(stage) => write!(formatter, "adapter timed out during {stage}"),
            Self::ProcessExited => write!(
                formatter,
                "adapter process exited before completing protocol"
            ),
            Self::UnexpectedFrame(stage) => {
                write!(formatter, "unexpected adapter frame during {stage}")
            }
            Self::InvalidHello(message) => write!(formatter, "invalid adapter hello: {message}"),
            Self::InvalidSnapshot(message) => {
                write!(formatter, "invalid registry snapshot: {message}")
            }
            Self::InvalidRuntimeResponse(message) => {
                write!(formatter, "invalid runtime response: {message}")
            }
            Self::InvalidInferenceRequest(message) => {
                write!(formatter, "invalid inference request: {message}")
            }
            Self::InferenceFailed {
                code,
                message,
                retryable,
            } => write!(
                formatter,
                "inference failed code={code} retryable={retryable}: {message}"
            ),
            Self::RestartBudgetExhausted {
                attempts,
                last_error,
            } => write!(
                formatter,
                "adapter restart budget exhausted after {attempts} attempts: {last_error}"
            ),
            Self::Kernel(error) => Display::fmt(error, formatter),
        }
    }
}

impl std::error::Error for AdapterSupervisorError {}

impl From<KernelError> for AdapterSupervisorError {
    fn from(value: KernelError) -> Self {
        Self::Kernel(value)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdapterIdentity {
    pub adapter_id: String,
    pub runtime_id: String,
    pub upstream_repository: String,
    pub upstream_commit: String,
}

impl AdapterIdentity {
    #[must_use]
    pub fn new(
        adapter_id: impl Into<String>,
        runtime_id: impl Into<String>,
        upstream_repository: impl Into<String>,
        upstream_commit: impl Into<String>,
    ) -> Self {
        Self {
            adapter_id: adapter_id.into(),
            runtime_id: runtime_id.into(),
            upstream_repository: upstream_repository.into(),
            upstream_commit: upstream_commit.into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdapterCleanupCommand {
    pub program: String,
    pub args: Vec<String>,
    pub env: BTreeMap<String, String>,
}

impl AdapterCleanupCommand {
    #[must_use]
    pub fn new(program: impl Into<String>) -> Self {
        Self {
            program: program.into(),
            args: Vec::new(),
            env: BTreeMap::new(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdapterCommand {
    pub program: String,
    pub args: Vec<String>,
    pub env: BTreeMap<String, String>,
    pub cleanup: Option<AdapterCleanupCommand>,
}

impl AdapterCommand {
    #[must_use]
    pub fn new(program: impl Into<String>) -> Self {
        Self {
            program: program.into(),
            args: Vec::new(),
            env: BTreeMap::new(),
            cleanup: None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SupervisorPolicy {
    pub max_frame_bytes: usize,
    pub max_inbound_frames: usize,
    pub max_inbound_bytes: usize,
    pub handshake_timeout: Duration,
    pub request_timeout: Duration,
    pub write_timeout: Duration,
    pub shutdown_timeout: Duration,
    pub thread_join_timeout: Duration,
    pub cleanup_timeout: Duration,
    pub termination_poll_interval: Duration,
    pub max_restarts: u32,
    pub restart_backoff: Duration,
}

impl Default for SupervisorPolicy {
    fn default() -> Self {
        Self {
            max_frame_bytes: DEFAULT_MAX_FRAME_BYTES,
            max_inbound_frames: DEFAULT_MAX_INBOUND_FRAMES,
            max_inbound_bytes: DEFAULT_MAX_INBOUND_BYTES,
            handshake_timeout: Duration::from_secs(10),
            request_timeout: Duration::from_secs(5),
            write_timeout: Duration::from_secs(5),
            shutdown_timeout: Duration::from_secs(2),
            thread_join_timeout: Duration::from_millis(500),
            cleanup_timeout: Duration::from_secs(2),
            termination_poll_interval: Duration::from_millis(10),
            max_restarts: 2,
            restart_backoff: Duration::from_millis(50),
        }
    }
}

struct QueuedInboundFrame {
    frame: AdapterFrame,
    wire_bytes: usize,
}

struct WriterRequest {
    bytes: Vec<u8>,
    completion: SyncSender<Result<(), AdapterSupervisorError>>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct UnaryInferenceResult {
    pub text: String,
    pub terminal: InferenceTerminal,
}

#[derive(Debug, Clone, PartialEq)]
pub struct StreamingInferenceResult {
    pub chunks: Vec<InferenceChunk>,
    pub text: String,
    pub terminal: InferenceTerminal,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LocalStreamingFallbackCandidate {
    pub model_id: String,
    pub reserved_cost_microusd: u64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct CancelledStreamingInferenceResult {
    pub chunks: Vec<InferenceChunk>,
    pub text: String,
    pub terminal: InferenceTerminal,
    pub cancellation_requested: bool,
    pub cancellation_acknowledged: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InferenceCancelOutcome {
    Acknowledged,
    AlreadyTerminal,
}

#[derive(Debug, Clone, PartialEq)]
struct InferenceAuthority {
    request_id: String,
    attempt_id: String,
    principal: PrincipalRef,
    session_id: String,
}

struct InboundState {
    pending_bytes: AtomicUsize,
    frame_limit: AtomicUsize,
    fatal_error: Mutex<Option<AdapterSupervisorError>>,
}

impl InboundState {
    fn new(frame_limit: usize) -> Self {
        Self {
            pending_bytes: AtomicUsize::new(0),
            frame_limit: AtomicUsize::new(frame_limit),
            fatal_error: Mutex::new(None),
        }
    }

    fn poison(&self, error: AdapterSupervisorError) {
        let mut guard = match self.fatal_error.lock() {
            Ok(guard) => guard,
            Err(poisoned) => poisoned.into_inner(),
        };
        if guard.is_none() {
            *guard = Some(error);
        }
    }

    fn fatal(&self) -> Option<AdapterSupervisorError> {
        let guard = match self.fatal_error.lock() {
            Ok(guard) => guard,
            Err(poisoned) => poisoned.into_inner(),
        };
        guard.clone()
    }
}

pub struct AdapterSupervisor {
    child: Child,
    writer_sender: Option<SyncSender<WriterRequest>>,
    receiver: Receiver<Result<QueuedInboundFrame, AdapterSupervisorError>>,
    reader: Option<JoinHandle<()>>,
    writer: Option<JoinHandle<()>>,
    inbound_state: Arc<InboundState>,
    identity: AdapterIdentity,
    policy: SupervisorPolicy,
    negotiated_max_frame_bytes: usize,
    negotiated_features: BTreeSet<String>,
    next_frame_sequence: u64,
    session_poisoned: Option<String>,
    process_group_id: Option<u32>,
    cleanup: Option<AdapterCleanupCommand>,
    termination_complete: bool,
    last_inference_authority: Option<InferenceAuthority>,
}

impl AdapterSupervisor {
    pub fn connect_with_restarts(
        command: AdapterCommand,
        identity: AdapterIdentity,
        policy: SupervisorPolicy,
    ) -> Result<Self, AdapterSupervisorError> {
        let attempts = policy.max_restarts.saturating_add(1);
        let mut last_error = String::from("adapter did not start");
        for attempt in 0..attempts {
            match Self::start(command.clone(), identity.clone(), policy.clone()) {
                Ok(supervisor) => return Ok(supervisor),
                Err(error) => {
                    last_error = error.to_string();
                    if attempt.saturating_add(1) < attempts {
                        thread::sleep(policy.restart_backoff);
                    }
                }
            }
        }
        Err(AdapterSupervisorError::RestartBudgetExhausted {
            attempts,
            last_error,
        })
    }

    pub fn start(
        command: AdapterCommand,
        identity: AdapterIdentity,
        policy: SupervisorPolicy,
    ) -> Result<Self, AdapterSupervisorError> {
        if command.program.trim().is_empty() || !Path::new(&command.program).is_absolute() {
            return Err(AdapterSupervisorError::InvalidCommand(
                "program must be a non-empty absolute path".to_owned(),
            ));
        }
        if policy.max_frame_bytes == 0
            || policy.max_inbound_frames == 0
            || policy.max_inbound_bytes == 0
            || policy.write_timeout.is_zero()
            || policy.shutdown_timeout.is_zero()
            || policy.thread_join_timeout.is_zero()
            || policy.cleanup_timeout.is_zero()
            || policy.termination_poll_interval.is_zero()
        {
            return Err(AdapterSupervisorError::InvalidCommand(
                "frame/queue budgets and all I/O/lifecycle timeouts must be positive".to_owned(),
            ));
        }

        if let Some(cleanup) = &command.cleanup {
            if cleanup.program.trim().is_empty() || !Path::new(&cleanup.program).is_absolute() {
                return Err(AdapterSupervisorError::InvalidCommand(
                    "cleanup program must be a non-empty absolute path".to_owned(),
                ));
            }
        }

        let cleanup = command.cleanup.clone();
        let mut process = Command::new(&command.program);
        process.args(&command.args);
        process.env_clear();
        process.envs(&command.env);
        #[cfg(unix)]
        {
            process.process_group(0);
        }
        process
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit());
        let mut child = process
            .spawn()
            .map_err(|error| AdapterSupervisorError::Io(error.to_string()))?;
        #[cfg(unix)]
        let process_group_id = Some(child.id());
        #[cfg(not(unix))]
        let process_group_id = None;
        let stdin = child
            .stdin
            .take()
            .ok_or(AdapterSupervisorError::UnexpectedFrame("stdin setup"))?;
        let stdout = child
            .stdout
            .take()
            .ok_or(AdapterSupervisorError::UnexpectedFrame("stdout setup"))?;

        let max_frame_bytes = policy.max_frame_bytes;
        let max_inbound_frames = policy.max_inbound_frames;
        let max_inbound_bytes = policy.max_inbound_bytes;
        let inbound_state = Arc::new(InboundState::new(max_frame_bytes));
        let reader_state = Arc::clone(&inbound_state);
        let (sender, receiver) = mpsc::sync_channel(max_inbound_frames);
        let reader = thread::spawn(move || {
            let mut output = stdout;
            loop {
                let frame_limit = reader_state.frame_limit.load(Ordering::Acquire);
                match read_framed_frame(
                    &mut output,
                    frame_limit,
                    max_inbound_bytes,
                    &reader_state.pending_bytes,
                ) {
                    Ok(Some(queued)) => match sender.try_send(Ok(queued)) {
                        Ok(()) => {}
                        Err(TrySendError::Full(item)) => {
                            if let Ok(queued) = item {
                                reader_state
                                    .pending_bytes
                                    .fetch_sub(queued.wire_bytes, Ordering::AcqRel);
                            }
                            reader_state.poison(AdapterSupervisorError::InboundQueueFull {
                                max_frames: max_inbound_frames,
                            });
                            break;
                        }
                        Err(TrySendError::Disconnected(item)) => {
                            if let Ok(queued) = item {
                                reader_state
                                    .pending_bytes
                                    .fetch_sub(queued.wire_bytes, Ordering::AcqRel);
                            }
                            break;
                        }
                    },
                    Ok(None) => {
                        let _ = sender.try_send(Err(AdapterSupervisorError::ProcessExited));
                        break;
                    }
                    Err(error) => {
                        reader_state.poison(error.clone());
                        let _ = sender.try_send(Err(error));
                        break;
                    }
                }
            }
        });

        let (writer_sender, writer_receiver) = mpsc::sync_channel::<WriterRequest>(1);
        let writer = thread::spawn(move || {
            let mut input: ChildStdin = stdin;
            while let Ok(request) = writer_receiver.recv() {
                let result = input
                    .write_all(&request.bytes)
                    .and_then(|_| input.flush())
                    .map_err(|error| AdapterSupervisorError::Io(error.to_string()));
                let failed = result.is_err();
                let _ = request.completion.send(result);
                if failed {
                    break;
                }
            }
        });

        let mut supervisor = Self {
            child,
            writer_sender: Some(writer_sender),
            receiver,
            reader: Some(reader),
            writer: Some(writer),
            inbound_state,
            identity,
            policy,
            negotiated_max_frame_bytes: max_frame_bytes,
            negotiated_features: BTreeSet::new(),
            next_frame_sequence: 0,
            session_poisoned: None,
            process_group_id,
            cleanup,
            termination_complete: false,
            last_inference_authority: None,
        };
        let hello_frame =
            supervisor.receive_frame(supervisor.policy.handshake_timeout, "handshake")?;
        let (negotiated_max, features) = supervisor.validate_hello(&hello_frame)?;
        supervisor.negotiated_max_frame_bytes = negotiated_max;
        supervisor
            .inbound_state
            .frame_limit
            .store(negotiated_max, Ordering::Release);
        supervisor.negotiated_features = features.clone();
        supervisor.send_hello_ack(&hello_frame.frame_id, features)?;
        Ok(supervisor)
    }

    #[must_use]
    pub fn negotiated_max_frame_bytes(&self) -> usize {
        self.negotiated_max_frame_bytes
    }

    #[must_use]
    pub fn negotiated_features(&self) -> &BTreeSet<String> {
        &self.negotiated_features
    }

    #[must_use]
    pub fn pending_inbound_bytes(&self) -> usize {
        self.inbound_state.pending_bytes.load(Ordering::Acquire)
    }

    #[must_use]
    pub fn is_poisoned(&self) -> bool {
        self.session_poisoned.is_some() || self.inbound_state.fatal().is_some()
    }

    fn fail_protocol<T>(
        &mut self,
        error: AdapterSupervisorError,
    ) -> Result<T, AdapterSupervisorError> {
        self.poison_session(error.to_string());
        Err(error)
    }

    fn exchange_control(
        &mut self,
        body: adapter_frame::Body,
        stage: &'static str,
    ) -> Result<AdapterFrame, AdapterSupervisorError> {
        self.ensure_io_healthy()?;
        let request = self.next_control_frame(body, self.policy.request_timeout);
        let request_id = request.frame_id.clone();
        if let Err(error) = self.write_frame(&request) {
            return self.fail_protocol(error);
        }
        let response = match self.receive_frame(self.policy.request_timeout, stage) {
            Ok(response) => response,
            Err(error) => return self.fail_protocol(error),
        };
        if response.frame_id.trim().is_empty() || response.correlation_id != request_id {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "response frame_id is empty or correlation_id does not match active request"
                    .to_owned(),
            ));
        }
        Ok(response)
    }

    pub fn request_registry_snapshot(
        &mut self,
    ) -> Result<RegistrySnapshot, AdapterSupervisorError> {
        let response = self.exchange_control(
            adapter_frame::Body::RegistrySnapshotRequest(RegistrySnapshotRequest {}),
            "registry snapshot",
        )?;
        match response.body {
            Some(adapter_frame::Body::RegistrySnapshot(snapshot))
                if snapshot.runtime_id == self.identity.runtime_id =>
            {
                Ok(snapshot)
            }
            Some(adapter_frame::Body::RegistrySnapshot(_)) => self.fail_protocol(
                AdapterSupervisorError::InvalidSnapshot("runtime mismatch".to_owned()),
            ),
            _ => self.fail_protocol(AdapterSupervisorError::UnexpectedFrame("registry snapshot")),
        }
    }

    pub fn request_health(&mut self) -> Result<RuntimeHealth, AdapterSupervisorError> {
        let response = self.exchange_control(
            adapter_frame::Body::HealthRequest(AdapterHealthRequest {}),
            "health request",
        )?;
        self.extract_health(response, "health request")
    }

    pub fn cancel(
        &mut self,
        target_request_id: impl Into<String>,
        reason: impl Into<String>,
    ) -> Result<RuntimeHealth, AdapterSupervisorError> {
        let response = self.exchange_control(
            adapter_frame::Body::Cancel(AdapterCancel {
                target_request_id: target_request_id.into(),
                reason: reason.into(),
            }),
            "cancel",
        )?;
        self.extract_health(response, "cancel")
    }

    pub fn infer_unary(
        &mut self,
        request: InferenceRequest,
    ) -> Result<UnaryInferenceResult, AdapterSupervisorError> {
        self.ensure_io_healthy()?;
        if !self.negotiated_features.contains("unary-inference") {
            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(
                "peer did not negotiate unary-inference".to_owned(),
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
        authorize_inference_egress(&request, &local_target, None, &reservation, 0)
            .map_err(|error| AdapterSupervisorError::InvalidInferenceRequest(error.to_string()))?;
        let config = request.config.as_ref().ok_or_else(|| {
            AdapterSupervisorError::InvalidInferenceRequest("config is required".to_owned())
        })?;
        if request.engine_id != W02_UNARY_ENGINE_ID
            || request.model_id != W02_UNARY_MODEL_ID
            || request.idempotency_key.trim().is_empty()
            || request.inputs.is_empty()
            || request.deadline_at.is_none()
            || config.stream
            || config.max_output_tokens == 0
            || config.max_output_tokens > 256
            || request
                .inputs
                .iter()
                .any(|input| input.role == 0 || input.content.trim().is_empty())
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(
                "request is outside the bounded W02-10 unary lane".to_owned(),
            ));
        }

        let frame = self.next_control_frame(
            adapter_frame::Body::InferenceRequest(request.clone()),
            self.policy.request_timeout,
        );
        let frame_id = frame.frame_id.clone();
        if let Err(error) = self.write_frame(&frame) {
            return self.fail_protocol(error);
        }

        let first = match self.receive_frame(self.policy.request_timeout, "unary inference chunk") {
            Ok(response) => response,
            Err(error) => return self.fail_protocol(error),
        };
        self.validate_inference_outer(&first, &frame_id)?;
        let chunk = match first.body {
            Some(adapter_frame::Body::InferenceChunk(chunk)) => chunk,
            Some(adapter_frame::Body::InferenceError(error)) => {
                return self.inference_failure(error, &request)
            }
            _ => {
                return self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(
                    "unary inference chunk",
                ))
            }
        };
        self.validate_inference_chunk(&chunk, &request)?;

        let second =
            match self.receive_frame(self.policy.request_timeout, "unary inference terminal") {
                Ok(response) => response,
                Err(error) => return self.fail_protocol(error),
            };
        self.validate_inference_outer(&second, &frame_id)?;
        let terminal = match second.body {
            Some(adapter_frame::Body::InferenceTerminal(terminal)) => terminal,
            Some(adapter_frame::Body::InferenceError(error)) => {
                return self.inference_failure(error, &request)
            }
            _ => {
                return self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(
                    "unary inference terminal",
                ))
            }
        };
        self.validate_inference_terminal(&terminal, &request)?;
        Ok(UnaryInferenceResult {
            text: chunk.text_delta,
            terminal,
        })
    }

    pub fn infer_stream(
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
        if let Err(error) =
            authorize_inference_egress(&request, &local_target, None, &reservation, 0)
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

        if let Err(error) = self.record_inference_authority(&request) {
            return Err(Self::streaming_attempt_failure(error, false, 0));
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
            let response = match self
                .receive_frame(self.policy.request_timeout, "streaming inference")
            {
                Ok(response) => response,
                Err(error) => return Err(self.streaming_protocol_failure(error, emitted_chunks)),
            };
            if let Err(error) = self.validate_inference_outer(&response, &frame_id) {
                return Err(Self::streaming_attempt_failure(
                    error,
                    false,
                    emitted_chunks,
                ));
            }
            match response.body {
                Some(adapter_frame::Body::InferenceChunk(chunk)) => {
                    if let Err(error) =
                        self.validate_stream_chunk(&chunk, &request, expected_sequence)
                    {
                        return Err(Self::streaming_attempt_failure(
                            error,
                            false,
                            emitted_chunks,
                        ));
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
                        return Err(Self::streaming_attempt_failure(
                            error,
                            false,
                            emitted_chunks,
                        ));
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
                    if error.request_id != request.request_id
                        || error.attempt_id != request.attempt_id
                    {
                        let protocol_error = AdapterSupervisorError::InvalidRuntimeResponse(
                            "inference error identity mismatch".to_owned(),
                        );
                        return Err(self.streaming_protocol_failure(protocol_error, emitted_chunks));
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

    fn record_inference_authority(
        &mut self,
        request: &InferenceRequest,
    ) -> Result<(), AdapterSupervisorError> {
        let principal = request.principal.clone().ok_or_else(|| {
            AdapterSupervisorError::InvalidInferenceRequest(
                "inference principal is required for cancellation authority".to_owned(),
            )
        })?;
        if principal.user_id.trim().is_empty() || request.session_id.trim().is_empty() {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "inference user_id and session_id are required for cancellation authority"
                    .to_owned(),
            ));
        }
        self.last_inference_authority = Some(InferenceAuthority {
            request_id: request.request_id.clone(),
            attempt_id: request.attempt_id.clone(),
            principal,
            session_id: request.session_id.clone(),
        });
        Ok(())
    }

    fn validate_inference_cancel_authority(
        &self,
        target_request_id: &str,
        target_attempt_id: &str,
        caller_principal: &PrincipalRef,
        caller_session_id: &str,
    ) -> Result<(), AdapterSupervisorError> {
        if caller_principal.user_id.trim().is_empty() || caller_session_id.trim().is_empty() {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "cancellation caller principal/session must be non-empty".to_owned(),
            ));
        }
        let Some(authority) = self.last_inference_authority.as_ref() else {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "cancellation authority mismatch: no supervised inference ownership record"
                    .to_owned(),
            ));
        };
        if authority.request_id != target_request_id
            || authority.attempt_id != target_attempt_id
            || authority.principal != *caller_principal
            || authority.session_id != caller_session_id
        {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "cancellation authority mismatch for request/attempt/principal/session".to_owned(),
            ));
        }
        Ok(())
    }

    fn send_inference_cancel_frame(
        &mut self,
        target_request_id: &str,
        target_attempt_id: &str,
        reason: &str,
    ) -> Result<String, AdapterSupervisorError> {
        if target_request_id.trim().is_empty()
            || target_attempt_id.trim().is_empty()
            || reason.trim().is_empty()
        {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "cancellation request_id, attempt_id and reason must be non-empty".to_owned(),
            ));
        }
        let frame = self.next_control_frame(
            adapter_frame::Body::InferenceCancel(InferenceCancel {
                contract_version: Some(ContractVersion { major: 1, minor: 2 }),
                target_request_id: target_request_id.to_owned(),
                target_attempt_id: target_attempt_id.to_owned(),
                reason: reason.to_owned(),
            }),
            self.policy.request_timeout,
        );
        let frame_id = frame.frame_id.clone();
        if let Err(error) = self.write_frame(&frame) {
            return self.fail_protocol(error);
        }
        Ok(frame_id)
    }

    fn validate_inference_cancel_ack(
        &mut self,
        frame: &AdapterFrame,
        cancel_frame_id: &str,
        request: &InferenceRequest,
    ) -> Result<(), AdapterSupervisorError> {
        if frame.frame_id.trim().is_empty() || frame.correlation_id != cancel_frame_id {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "cancellation ACK correlation mismatch".to_owned(),
            ));
        }
        let ack = match frame.body.as_ref() {
            Some(adapter_frame::Body::InferenceCancel(value)) => value,
            _ => {
                return self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(
                    "inference cancellation ACK",
                ))
            }
        };
        if let Err(error) = validate_contract_version(ack.contract_version.as_ref()) {
            return self.fail_protocol(error.into());
        }
        if ack.target_request_id != request.request_id
            || ack.target_attempt_id != request.attempt_id
            || ack.reason.trim().is_empty()
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "cancellation ACK target/reason mismatch".to_owned(),
            ));
        }
        Ok(())
    }

    pub fn cancel_inference(
        &mut self,
        caller_principal: &PrincipalRef,
        caller_session_id: &str,
        target_request_id: impl Into<String>,
        target_attempt_id: impl Into<String>,
        reason: impl Into<String>,
    ) -> Result<InferenceCancelOutcome, AdapterSupervisorError> {
        self.ensure_io_healthy()?;
        if !self.negotiated_features.contains("streaming-cancellation") {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "peer did not negotiate streaming-cancellation".to_owned(),
            ));
        }
        let request_id = target_request_id.into();
        let attempt_id = target_attempt_id.into();
        let reason = reason.into();
        self.validate_inference_cancel_authority(
            &request_id,
            &attempt_id,
            caller_principal,
            caller_session_id,
        )?;
        let cancel_frame_id =
            self.send_inference_cancel_frame(&request_id, &attempt_id, &reason)?;
        let response =
            match self.receive_frame(self.policy.request_timeout, "inference cancellation ACK") {
                Ok(response) => response,
                Err(error) => return self.fail_protocol(error),
            };
        if response.frame_id.trim().is_empty() || response.correlation_id != cancel_frame_id {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "cancellation response correlation mismatch".to_owned(),
            ));
        }
        match response.body {
            Some(adapter_frame::Body::InferenceCancel(ack)) => {
                if let Err(error) = validate_contract_version(ack.contract_version.as_ref()) {
                    return self.fail_protocol(error.into());
                }
                if ack.target_request_id != request_id || ack.target_attempt_id != attempt_id {
                    return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                        "cancellation ACK target mismatch".to_owned(),
                    ));
                }
                Ok(InferenceCancelOutcome::Acknowledged)
            }
            Some(adapter_frame::Body::Error(error)) if error.code == "CANCEL_ALREADY_TERMINAL" => {
                Ok(InferenceCancelOutcome::AlreadyTerminal)
            }
            Some(adapter_frame::Body::Error(error)) => {
                Err(AdapterSupervisorError::InvalidRuntimeResponse(format!(
                    "cancellation rejected {}: {}",
                    error.code, error.message
                )))
            }
            _ => self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(
                "inference cancellation response",
            )),
        }
    }

    pub fn infer_stream_with_cancellation(
        &mut self,
        request: InferenceRequest,
        cancel_after_chunks: usize,
        reason: impl Into<String>,
    ) -> Result<CancelledStreamingInferenceResult, AdapterSupervisorError> {
        self.ensure_io_healthy()?;
        if !self.negotiated_features.contains("streaming-inference")
            || !self.negotiated_features.contains("streaming-cancellation")
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(
                "peer did not negotiate streaming inference cancellation".to_owned(),
            ));
        }
        let reason = reason.into();
        if reason.trim().is_empty() {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "cancellation reason must be non-empty".to_owned(),
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
        authorize_inference_egress(&request, &local_target, None, &reservation, 0)
            .map_err(|error| AdapterSupervisorError::InvalidInferenceRequest(error.to_string()))?;
        let config = request.config.as_ref().ok_or_else(|| {
            AdapterSupervisorError::InvalidInferenceRequest("config is required".to_owned())
        })?;
        if request.engine_id != W02_UNARY_ENGINE_ID
            || request.model_id != W02_UNARY_MODEL_ID
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
            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(
                "request is outside the bounded W02-12 cancellation lane".to_owned(),
            ));
        }

        self.record_inference_authority(&request)?;

        let frame = self.next_control_frame(
            adapter_frame::Body::InferenceRequest(request.clone()),
            self.policy.request_timeout,
        );
        let request_frame_id = frame.frame_id.clone();
        if let Err(error) = self.write_frame(&frame) {
            return self.fail_protocol(error);
        }

        let mut chunks = Vec::new();
        let mut text = String::new();
        let mut expected_sequence = 1_u64;
        let mut cancel_frame_id = None;
        let mut cancellation_acknowledged = false;
        if cancel_after_chunks == 0 {
            cancel_frame_id = Some(self.send_inference_cancel_frame(
                &request.request_id,
                &request.attempt_id,
                &reason,
            )?);
        }

        loop {
            let response = match self.receive_frame(
                self.policy.request_timeout,
                "inference cancellation termination",
            ) {
                Ok(response) => response,
                Err(error) => return self.fail_protocol(error),
            };
            match response.body.as_ref() {
                Some(adapter_frame::Body::InferenceCancel(_)) => {
                    let expected = match cancel_frame_id.as_deref() {
                        Some(value) => value,
                        None => {
                            return self.fail_protocol(
                                AdapterSupervisorError::InvalidRuntimeResponse(
                                    "unsolicited cancellation ACK".to_owned(),
                                ),
                            )
                        }
                    };
                    self.validate_inference_cancel_ack(&response, expected, &request)?;
                    if cancellation_acknowledged {
                        return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                            "duplicate cancellation ACK".to_owned(),
                        ));
                    }
                    cancellation_acknowledged = true;
                }
                Some(adapter_frame::Body::InferenceChunk(_)) => {
                    self.validate_inference_outer(&response, &request_frame_id)?;
                    let chunk = match response.body {
                        Some(adapter_frame::Body::InferenceChunk(chunk)) => chunk,
                        _ => unreachable!(),
                    };
                    self.validate_stream_chunk(&chunk, &request, expected_sequence)?;
                    text.push_str(&chunk.text_delta);
                    chunks.push(chunk);
                    expected_sequence = expected_sequence.saturating_add(1);
                    if cancel_frame_id.is_none() && chunks.len() >= cancel_after_chunks {
                        cancel_frame_id = Some(self.send_inference_cancel_frame(
                            &request.request_id,
                            &request.attempt_id,
                            &reason,
                        )?);
                    }
                }
                Some(adapter_frame::Body::InferenceTerminal(_)) => {
                    self.validate_inference_outer(&response, &request_frame_id)?;
                    if cancel_frame_id.is_none() {
                        return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                            "stream reached terminal state before cancellation was requested"
                                .to_owned(),
                        ));
                    }
                    if !cancellation_acknowledged {
                        return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                            "cancellation termination arrived before ACK".to_owned(),
                        ));
                    }
                    let terminal = match response.body {
                        Some(adapter_frame::Body::InferenceTerminal(terminal)) => terminal,
                        _ => unreachable!(),
                    };
                    let final_sequence = expected_sequence.saturating_sub(1);
                    self.validate_cancelled_terminal(&terminal, &request, final_sequence)?;
                    return Ok(CancelledStreamingInferenceResult {
                        chunks,
                        text,
                        terminal,
                        cancellation_requested: true,
                        cancellation_acknowledged,
                    });
                }
                Some(adapter_frame::Body::InferenceError(_)) => {
                    self.validate_inference_outer(&response, &request_frame_id)?;
                    let failure = match response.body {
                        Some(adapter_frame::Body::InferenceError(error)) => error,
                        _ => unreachable!(),
                    };
                    return self.inference_failure(failure, &request);
                }
                Some(adapter_frame::Body::Error(error)) => {
                    return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                        format!(
                            "cancellation transport error {}: {}",
                            error.code, error.message
                        ),
                    ))
                }
                _ => {
                    return self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(
                        "inference cancellation",
                    ))
                }
            }
        }
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
        let usage = terminal.usage.as_ref();
        let measurement =
            usage.and_then(|value| InferenceUsageMeasurement::try_from(value.measurement).ok());
        let usage_valid = match (measurement, usage) {
            (Some(InferenceUsageMeasurement::Exact), Some(value)) => {
                value.input_tokens.is_some()
                    && value.output_tokens.is_some()
                    && value.total_tokens.is_some()
            }
            (Some(InferenceUsageMeasurement::Unknown), Some(value)) => {
                value.input_tokens.is_none()
                    && value.output_tokens.is_none()
                    && value.total_tokens.is_none()
            }
            _ => false,
        };
        if terminal.request_id != request.request_id
            || terminal.attempt_id != request.attempt_id
            || terminal.final_sequence != expected_final_sequence
            || InferenceFinishReason::try_from(terminal.finish_reason)
                != Ok(InferenceFinishReason::Cancelled)
            || !usage_valid
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "invalid cancellation terminal identity/sequence/finish/usage".to_owned(),
            ));
        }
        Ok(())
    }

    fn validate_stream_chunk(
        &mut self,
        chunk: &InferenceChunk,
        request: &InferenceRequest,
        expected_sequence: u64,
    ) -> Result<(), AdapterSupervisorError> {
        if let Err(error) = validate_contract_version(chunk.contract_version.as_ref()) {
            return self.fail_protocol(error.into());
        }
        if chunk.request_id != request.request_id
            || chunk.attempt_id != request.attempt_id
            || chunk.sequence != expected_sequence
            || chunk.text_delta.is_empty()
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(format!(
                "invalid streaming chunk identity/sequence/content: expected sequence {expected_sequence}"
            )));
        }
        Ok(())
    }

    fn validate_stream_terminal(
        &mut self,
        terminal: &InferenceTerminal,
        request: &InferenceRequest,
        expected_final_sequence: u64,
    ) -> Result<(), AdapterSupervisorError> {
        if let Err(error) = validate_contract_version(terminal.contract_version.as_ref()) {
            return self.fail_protocol(error.into());
        }
        let finish = InferenceFinishReason::try_from(terminal.finish_reason).ok();
        let usage = terminal.usage.as_ref();
        let measurement =
            usage.and_then(|value| InferenceUsageMeasurement::try_from(value.measurement).ok());
        let usage_valid = match (measurement, usage) {
            (Some(InferenceUsageMeasurement::Exact), Some(value)) => {
                value.input_tokens.is_some()
                    && value.output_tokens.is_some()
                    && value.total_tokens.is_some()
            }
            (Some(InferenceUsageMeasurement::Unknown), Some(value)) => {
                value.input_tokens.is_none()
                    && value.output_tokens.is_none()
                    && value.total_tokens.is_none()
            }
            _ => false,
        };
        if terminal.request_id != request.request_id
            || terminal.attempt_id != request.attempt_id
            || terminal.final_sequence != expected_final_sequence
            || !matches!(
                finish,
                Some(InferenceFinishReason::Unspecified)
                    | Some(InferenceFinishReason::Stop)
                    | Some(InferenceFinishReason::Length)
                    | Some(InferenceFinishReason::ContentFilter)
            )
            || !usage_valid
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "invalid streaming terminal identity/sequence/finish/usage".to_owned(),
            ));
        }
        Ok(())
    }

    fn validate_inference_outer(
        &mut self,
        frame: &AdapterFrame,
        request_frame_id: &str,
    ) -> Result<(), AdapterSupervisorError> {
        if frame.frame_id.trim().is_empty() || frame.correlation_id != request_frame_id {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "inference response correlation mismatch".to_owned(),
            ));
        }
        Ok(())
    }

    fn validate_inference_chunk(
        &mut self,
        chunk: &InferenceChunk,
        request: &InferenceRequest,
    ) -> Result<(), AdapterSupervisorError> {
        if let Err(error) = validate_contract_version(chunk.contract_version.as_ref()) {
            return self.fail_protocol(error.into());
        }
        if chunk.request_id != request.request_id
            || chunk.attempt_id != request.attempt_id
            || chunk.sequence != 1
            || chunk.text_delta.trim().is_empty()
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "invalid unary inference chunk identity/sequence/content".to_owned(),
            ));
        }
        Ok(())
    }

    fn validate_inference_terminal(
        &mut self,
        terminal: &InferenceTerminal,
        request: &InferenceRequest,
    ) -> Result<(), AdapterSupervisorError> {
        if let Err(error) = validate_contract_version(terminal.contract_version.as_ref()) {
            return self.fail_protocol(error.into());
        }
        let finish = InferenceFinishReason::try_from(terminal.finish_reason).ok();
        let usage = terminal.usage.as_ref();
        let measurement =
            usage.and_then(|value| InferenceUsageMeasurement::try_from(value.measurement).ok());
        if terminal.request_id != request.request_id
            || terminal.attempt_id != request.attempt_id
            || terminal.final_sequence != 1
            || !matches!(
                finish,
                Some(InferenceFinishReason::Stop)
                    | Some(InferenceFinishReason::Length)
                    | Some(InferenceFinishReason::ContentFilter)
            )
            || measurement != Some(InferenceUsageMeasurement::Exact)
            || usage.is_none_or(|value| {
                value.input_tokens.is_none()
                    || value.output_tokens.is_none()
                    || value.total_tokens.is_none()
            })
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "invalid unary inference terminal identity/finish/usage".to_owned(),
            ));
        }
        Ok(())
    }

    fn inference_failure<T>(
        &mut self,
        error: InferenceError,
        request: &InferenceRequest,
    ) -> Result<T, AdapterSupervisorError> {
        if error.request_id != request.request_id || error.attempt_id != request.attempt_id {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "inference error identity mismatch".to_owned(),
            ));
        }
        self.fail_protocol(AdapterSupervisorError::InferenceFailed {
            code: error.code,
            message: error.message,
            retryable: error.retryable,
        })
    }

    pub fn shutdown(
        mut self,
        reason: impl Into<String>,
    ) -> Result<RuntimeHealth, AdapterSupervisorError> {
        let response = self.exchange_control(
            adapter_frame::Body::Shutdown(AdapterShutdown {
                reason: reason.into(),
            }),
            "shutdown",
        )?;
        let health = self.extract_health(response, "shutdown")?;
        if health.status != RuntimeHealthStatus::Stopping as i32 {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "shutdown did not return STOPPING".to_owned(),
            ));
        }
        self.writer_sender.take();
        if !wait_child_bounded(
            &mut self.child,
            self.policy.shutdown_timeout,
            self.policy.termination_poll_interval,
        )? {
            self.terminate_bounded();
            return Err(AdapterSupervisorError::Timeout("shutdown exit"));
        }
        if !self.join_threads_bounded() {
            self.terminate_bounded();
            return Err(AdapterSupervisorError::Timeout("shutdown I/O drain"));
        }
        self.termination_complete = true;
        Ok(health)
    }

    fn validate_hello(
        &self,
        frame: &AdapterFrame,
    ) -> Result<(usize, BTreeSet<String>), AdapterSupervisorError> {
        validate_contract_version(frame.contract_version.as_ref())?;
        if frame.frame_id.trim().is_empty() || !frame.correlation_id.is_empty() {
            return Err(AdapterSupervisorError::InvalidHello(
                "invalid initial frame identity".to_owned(),
            ));
        }
        let hello = match frame.body.as_ref() {
            Some(adapter_frame::Body::Hello(hello)) => hello,
            _ => return Err(AdapterSupervisorError::UnexpectedFrame("handshake")),
        };
        validate_contract_version(hello.contract_version.as_ref())?;
        if hello.adapter_id != self.identity.adapter_id {
            return Err(AdapterSupervisorError::InvalidHello(format!(
                "adapter_id mismatch: {}",
                hello.adapter_id
            )));
        }
        if hello.upstream_repository != self.identity.upstream_repository {
            return Err(AdapterSupervisorError::InvalidHello(
                "upstream repository mismatch".to_owned(),
            ));
        }
        if hello.upstream_commit != self.identity.upstream_commit {
            return Err(AdapterSupervisorError::InvalidHello(
                "upstream commit mismatch".to_owned(),
            ));
        }
        let runtime = hello.runtime.as_ref().ok_or_else(|| {
            AdapterSupervisorError::InvalidHello("runtime descriptor missing".to_owned())
        })?;
        validate_contract_version(runtime.contract_version.as_ref())?;
        if runtime.runtime_id != self.identity.runtime_id {
            return Err(AdapterSupervisorError::InvalidHello(format!(
                "runtime_id mismatch: {}",
                runtime.runtime_id
            )));
        }
        if runtime.runtime_kind.trim().is_empty() {
            return Err(AdapterSupervisorError::InvalidHello(
                "runtime_kind is empty".to_owned(),
            ));
        }
        let peer_max = usize::try_from(hello.max_frame_bytes).map_err(|_| {
            AdapterSupervisorError::InvalidHello("peer frame limit does not fit usize".to_owned())
        })?;
        if peer_max == 0 {
            return Err(AdapterSupervisorError::InvalidHello(
                "peer frame limit is zero".to_owned(),
            ));
        }
        let advertised: BTreeSet<String> = hello.supported_features.iter().cloned().collect();
        for required in REQUIRED_FEATURES {
            if !advertised.contains(required) {
                return Err(AdapterSupervisorError::InvalidHello(format!(
                    "required feature missing: {required}"
                )));
            }
        }
        let mut negotiated: BTreeSet<String> = REQUIRED_FEATURES
            .iter()
            .map(|feature| (*feature).to_owned())
            .collect();
        for optional in OPTIONAL_FEATURES {
            if advertised.contains(optional) {
                negotiated.insert(optional.to_owned());
            }
        }
        Ok((peer_max.min(self.policy.max_frame_bytes), negotiated))
    }

    fn send_hello_ack(
        &mut self,
        correlation_id: &str,
        negotiated_features: BTreeSet<String>,
    ) -> Result<(), AdapterSupervisorError> {
        let frame = AdapterFrame {
            contract_version: Some(contract_version()),
            frame_id: "kernel-hello-ack".to_owned(),
            correlation_id: correlation_id.to_owned(),
            sent_at: Some(timestamp_at(SystemTime::now())),
            deadline_at: None,
            body: Some(adapter_frame::Body::HelloAck(AdapterHelloAck {
                contract_version: Some(contract_version()),
                adapter_id: self.identity.adapter_id.clone(),
                accepted: true,
                reason: String::new(),
                max_frame_bytes: self.negotiated_max_frame_bytes as u64,
                negotiated_features: negotiated_features.into_iter().collect(),
            })),
        };
        self.write_frame(&frame)
    }

    fn next_control_frame(&mut self, body: adapter_frame::Body, timeout: Duration) -> AdapterFrame {
        self.next_frame_sequence = self.next_frame_sequence.saturating_add(1);
        let frame_id = format!("kernel-frame-{}", self.next_frame_sequence);
        let now = SystemTime::now();
        AdapterFrame {
            contract_version: Some(contract_version()),
            frame_id,
            correlation_id: String::new(),
            sent_at: Some(timestamp_at(now)),
            deadline_at: Some(timestamp_at(now + timeout)),
            body: Some(body),
        }
    }

    fn write_frame(&mut self, frame: &AdapterFrame) -> Result<(), AdapterSupervisorError> {
        self.ensure_io_healthy()?;
        validate_contract_version(frame.contract_version.as_ref())?;
        if frame.body.is_none() {
            return Err(AdapterSupervisorError::UnexpectedFrame("outbound write"));
        }
        let payload = frame.encode_to_vec();
        if payload.is_empty() {
            return Err(AdapterSupervisorError::EmptyFrame);
        }
        if payload.len() > self.negotiated_max_frame_bytes {
            return Err(AdapterSupervisorError::FrameTooLarge(payload.len()));
        }
        let length = u32::try_from(payload.len())
            .map_err(|_| AdapterSupervisorError::FrameTooLarge(payload.len()))?;
        let mut bytes = Vec::with_capacity(payload.len().saturating_add(4));
        bytes.extend_from_slice(&length.to_be_bytes());
        bytes.extend_from_slice(&payload);
        let (completion, completed) = mpsc::sync_channel(1);
        let sender = self.writer_sender.as_ref().cloned().ok_or_else(|| {
            AdapterSupervisorError::SessionPoisoned("writer unavailable".to_owned())
        })?;
        match sender.try_send(WriterRequest { bytes, completion }) {
            Ok(()) => {}
            Err(TrySendError::Full(_)) => {
                self.poison_session("outbound writer queue full");
                return Err(AdapterSupervisorError::OutboundQueueFull);
            }
            Err(TrySendError::Disconnected(_)) => {
                self.poison_session("outbound writer disconnected");
                return Err(AdapterSupervisorError::ProcessExited);
            }
        }
        match completed.recv_timeout(self.policy.write_timeout) {
            Ok(Ok(())) => Ok(()),
            Ok(Err(error)) => {
                let reason = error.to_string();
                self.poison_session(reason);
                Err(error)
            }
            Err(RecvTimeoutError::Timeout) => {
                self.poison_session("outbound write timeout");
                Err(AdapterSupervisorError::Timeout("outbound write"))
            }
            Err(RecvTimeoutError::Disconnected) => {
                self.poison_session("outbound writer completion disconnected");
                Err(AdapterSupervisorError::ProcessExited)
            }
        }
    }

    fn ensure_io_healthy(&self) -> Result<(), AdapterSupervisorError> {
        if let Some(reason) = &self.session_poisoned {
            return Err(AdapterSupervisorError::SessionPoisoned(reason.clone()));
        }
        if let Some(error) = self.inbound_state.fatal() {
            return Err(error);
        }
        Ok(())
    }

    fn poison_session(&mut self, reason: impl Into<String>) {
        if self.session_poisoned.is_none() {
            self.session_poisoned = Some(reason.into());
        }
        self.terminate_bounded();
    }

    fn terminate_bounded(&mut self) {
        if self.termination_complete {
            return;
        }
        self.writer_sender.take();
        self.signal_process_group();
        let _ = self.child.kill();
        self.run_cleanup_bounded();
        let _ = wait_child_bounded(
            &mut self.child,
            self.policy.shutdown_timeout,
            self.policy.termination_poll_interval,
        );
        let _ = self.join_threads_bounded();
        self.termination_complete = true;
    }

    fn signal_process_group(&self) {
        #[cfg(unix)]
        if let Some(group_id) = self.process_group_id {
            let target = format!("-{group_id}");
            let mut command = Command::new("/bin/kill");
            command
                .env_clear()
                .args(["-KILL", "--", target.as_str()])
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null());
            if let Ok(mut killer) = command.spawn() {
                let _ = wait_child_bounded(
                    &mut killer,
                    self.policy.cleanup_timeout,
                    self.policy.termination_poll_interval,
                );
                let _ = killer.kill();
            }
        }
    }

    fn run_cleanup_bounded(&self) {
        let Some(cleanup) = &self.cleanup else {
            return;
        };
        let mut command = Command::new(&cleanup.program);
        command
            .args(&cleanup.args)
            .env_clear()
            .envs(&cleanup.env)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        let Ok(mut cleanup_process) = command.spawn() else {
            return;
        };
        match wait_child_bounded(
            &mut cleanup_process,
            self.policy.cleanup_timeout,
            self.policy.termination_poll_interval,
        ) {
            Ok(true) => {}
            _ => {
                let _ = cleanup_process.kill();
                let _ = wait_child_bounded(
                    &mut cleanup_process,
                    self.policy.thread_join_timeout,
                    self.policy.termination_poll_interval,
                );
            }
        }
    }

    fn join_threads_bounded(&mut self) -> bool {
        let reader_done = join_handle_bounded(
            &mut self.reader,
            self.policy.thread_join_timeout,
            self.policy.termination_poll_interval,
        );
        let writer_done = join_handle_bounded(
            &mut self.writer,
            self.policy.thread_join_timeout,
            self.policy.termination_poll_interval,
        );
        reader_done && writer_done
    }

    fn receive_frame(
        &self,
        timeout: Duration,
        stage: &'static str,
    ) -> Result<AdapterFrame, AdapterSupervisorError> {
        if let Some(error) = self.inbound_state.fatal() {
            return Err(error);
        }
        match self.receiver.recv_timeout(timeout) {
            Ok(Ok(queued)) => {
                self.inbound_state
                    .pending_bytes
                    .fetch_sub(queued.wire_bytes, Ordering::AcqRel);
                if let Some(error) = self.inbound_state.fatal() {
                    return Err(error);
                }
                let payload_bytes = queued.wire_bytes.saturating_sub(4);
                if payload_bytes > self.negotiated_max_frame_bytes {
                    return Err(AdapterSupervisorError::FrameTooLarge(payload_bytes));
                }
                Ok(queued.frame)
            }
            Ok(Err(error)) => Err(error),
            Err(RecvTimeoutError::Timeout) => Err(AdapterSupervisorError::Timeout(stage)),
            Err(RecvTimeoutError::Disconnected) => self
                .inbound_state
                .fatal()
                .map_or(Err(AdapterSupervisorError::ProcessExited), Err),
        }
    }

    fn extract_health(
        &mut self,
        response: AdapterFrame,
        stage: &'static str,
    ) -> Result<RuntimeHealth, AdapterSupervisorError> {
        let health = match response.body {
            Some(adapter_frame::Body::Health(health)) => health,
            _ => return self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(stage)),
        };
        if let Err(error) = validate_contract_version(health.contract_version.as_ref()) {
            return self.fail_protocol(error.into());
        }
        let status = RuntimeHealthStatus::try_from(health.status);
        if health.runtime_id != self.identity.runtime_id
            || status.is_err()
            || health.status == RuntimeHealthStatus::Unspecified as i32
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "invalid health identity/status".to_owned(),
            ));
        }
        if health.status == RuntimeHealthStatus::Ready as i32
            && (!health.degradation_reasons.is_empty()
                || health.dropped_event_count > 0
                || health.failed_action_count > 0)
        {
            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(
                "READY contradicts degradation or failure counters".to_owned(),
            ));
        }
        Ok(health)
    }
}

impl Drop for AdapterSupervisor {
    fn drop(&mut self) {
        if !self.termination_complete {
            self.terminate_bounded();
        }
    }
}

pub fn bridge_registry_snapshot(
    snapshot: &RegistrySnapshot,
    registry: &mut CapabilityRegistry,
    runtime_id: &str,
    adapter_id: &str,
    source_repo: &str,
    source_commit: &str,
) -> Result<Vec<String>, AdapterSupervisorError> {
    if snapshot.runtime_id != runtime_id || runtime_id.trim().is_empty() {
        return Err(AdapterSupervisorError::InvalidSnapshot(
            "snapshot runtime_id does not match expected runtime".to_owned(),
        ));
    }
    if adapter_id.trim().is_empty()
        || source_repo.trim().is_empty()
        || source_commit.trim().is_empty()
    {
        return Err(AdapterSupervisorError::InvalidSnapshot(
            "bridge provenance/adapter identity is incomplete".to_owned(),
        ));
    }
    let descriptors = snapshot
        .entries
        .iter()
        .map(|entry| {
            descriptor_from_registry_entry(
                entry,
                runtime_id,
                adapter_id,
                source_repo,
                source_commit,
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    registry.register_batch(descriptors).map_err(Into::into)
}

fn descriptor_from_registry_entry(
    entry: &NativeRegistryEntry,
    runtime_id: &str,
    adapter_id: &str,
    source_repo: &str,
    source_commit: &str,
) -> Result<CapabilityDescriptor, AdapterSupervisorError> {
    if entry.key.trim().is_empty() || entry.implementation.trim().is_empty() {
        return Err(AdapterSupervisorError::InvalidSnapshot(
            "registry entry key/implementation is empty".to_owned(),
        ));
    }
    let primitive = RegistryPrimitive::try_from(entry.primitive).map_err(|_| {
        AdapterSupervisorError::InvalidSnapshot(format!(
            "unknown registry primitive {}",
            entry.primitive
        ))
    })?;
    let primitive_slug = primitive_slug(primitive)?;
    let capability_id = format!(
        "openjarvis.registry.{primitive_slug}.{}",
        hex_key(&entry.key)
    );
    let mut extension_metadata = entry.metadata.clone();
    extension_metadata.retain(|key, _| !is_reserved_metadata_key(key));
    extension_metadata.insert("native_key".to_owned(), entry.key.clone());
    extension_metadata.insert(
        "native_implementation".to_owned(),
        entry.implementation.clone(),
    );
    extension_metadata.insert("native_type".to_owned(), entry.native_type.clone());
    extension_metadata.insert("registry_primitive".to_owned(), primitive_slug.to_owned());

    Ok(CapabilityDescriptor {
        contract_version: Some(contract_version()),
        capability_id,
        family: format!("openjarvis.registry.{primitive_slug}"),
        name: entry.key.clone(),
        owner: Some(RuntimeOwner {
            runtime_id: runtime_id.to_owned(),
            adapter_id: adapter_id.to_owned(),
            device_id: String::new(),
            process_id: String::new(),
        }),
        implementation_version: source_commit.to_owned(),
        interface_contract: "clever.v1.AdapterFrame/RegistrySnapshot".to_owned(),
        interface_version: format!("{WIRE_MAJOR}.{WIRE_MINOR}"),
        lifecycle_mode: LifecycleMode::Persistent as i32,
        permissions: Vec::new(),
        state_effects: Vec::new(),
        side_effects: Vec::new(),
        platform_constraints: entry
            .platform_constraints
            .iter()
            .map(|platform| PlatformConstraint {
                platform: platform.clone(),
                minimum_version: String::new(),
                required_features: Vec::new(),
            })
            .collect(),
        rollback_supported: false,
        provenance: vec![ProvenanceRef {
            source_repo: source_repo.to_owned(),
            source_commit: source_commit.to_owned(),
            source_path: String::new(),
            source_symbol: entry.implementation.clone(),
        }],
        evidence: Vec::new(),
        extension_metadata,
    })
}

fn primitive_slug(primitive: RegistryPrimitive) -> Result<&'static str, AdapterSupervisorError> {
    match primitive {
        RegistryPrimitive::Unspecified => Err(AdapterSupervisorError::InvalidSnapshot(
            "registry primitive is unspecified".to_owned(),
        )),
        RegistryPrimitive::Model => Ok("model"),
        RegistryPrimitive::Engine => Ok("engine"),
        RegistryPrimitive::Memory => Ok("memory"),
        RegistryPrimitive::FactStore => Ok("fact_store"),
        RegistryPrimitive::Agent => Ok("agent"),
        RegistryPrimitive::Tool => Ok("tool"),
        RegistryPrimitive::RouterPolicy => Ok("router_policy"),
        RegistryPrimitive::Benchmark => Ok("benchmark"),
        RegistryPrimitive::Channel => Ok("channel"),
        RegistryPrimitive::Learning => Ok("learning"),
        RegistryPrimitive::Skill => Ok("skill"),
        RegistryPrimitive::Speech => Ok("speech"),
        RegistryPrimitive::Compression => Ok("compression"),
        RegistryPrimitive::Tts => Ok("tts"),
        RegistryPrimitive::Connector => Ok("connector"),
        RegistryPrimitive::Miner => Ok("miner"),
    }
}

fn is_reserved_metadata_key(key: &str) -> bool {
    let normalized = key.to_ascii_lowercase();
    RESERVED_METADATA_TOKENS
        .iter()
        .any(|reserved| normalized.contains(reserved))
}

fn hex_key(value: &str) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let bytes = value.as_bytes();
    let mut encoded = String::with_capacity(bytes.len().saturating_mul(2));
    for byte in bytes {
        encoded.push(HEX[(byte >> 4) as usize] as char);
        encoded.push(HEX[(byte & 0x0f) as usize] as char);
    }
    encoded
}

fn contract_version() -> ContractVersion {
    ContractVersion {
        major: WIRE_MAJOR,
        minor: WIRE_MINOR,
    }
}

fn timestamp_at(time: SystemTime) -> prost_types::Timestamp {
    let duration = time.duration_since(UNIX_EPOCH).unwrap_or_default();
    prost_types::Timestamp {
        seconds: i64::try_from(duration.as_secs()).unwrap_or(i64::MAX),
        nanos: i32::try_from(duration.subsec_nanos()).unwrap_or(i32::MAX),
    }
}

fn wait_child_bounded(
    child: &mut Child,
    timeout: Duration,
    poll_interval: Duration,
) -> Result<bool, AdapterSupervisorError> {
    let deadline = Instant::now() + timeout;
    loop {
        match child
            .try_wait()
            .map_err(|error| AdapterSupervisorError::Io(error.to_string()))?
        {
            Some(_) => return Ok(true),
            None if Instant::now() >= deadline => return Ok(false),
            None => thread::sleep(poll_interval),
        }
    }
}

fn join_handle_bounded(
    handle: &mut Option<JoinHandle<()>>,
    timeout: Duration,
    poll_interval: Duration,
) -> bool {
    let Some(thread_handle) = handle.as_ref() else {
        return true;
    };
    let deadline = Instant::now() + timeout;
    while !thread_handle.is_finished() && Instant::now() < deadline {
        thread::sleep(poll_interval);
    }
    let finished = handle.as_ref().is_none_or(JoinHandle::is_finished);
    if finished {
        if let Some(thread_handle) = handle.take() {
            let _ = thread_handle.join();
        }
    } else {
        handle.take();
    }
    finished
}

fn reserve_inbound_bytes(
    pending_bytes: &AtomicUsize,
    wire_bytes: usize,
    max_pending_bytes: usize,
) -> Result<(), AdapterSupervisorError> {
    let mut current = pending_bytes.load(Ordering::Acquire);
    loop {
        let attempted = current.saturating_add(wire_bytes);
        if attempted > max_pending_bytes {
            return Err(AdapterSupervisorError::InboundBytesExceeded {
                attempted,
                max_bytes: max_pending_bytes,
            });
        }
        match pending_bytes.compare_exchange_weak(
            current,
            attempted,
            Ordering::AcqRel,
            Ordering::Acquire,
        ) {
            Ok(_) => return Ok(()),
            Err(actual) => current = actual,
        }
    }
}

fn read_framed_frame<R: Read>(
    reader: &mut R,
    max_frame_bytes: usize,
    max_pending_bytes: usize,
    pending_bytes: &AtomicUsize,
) -> Result<Option<QueuedInboundFrame>, AdapterSupervisorError> {
    let mut prefix = [0_u8; 4];
    let first = reader
        .read(&mut prefix)
        .map_err(|error| AdapterSupervisorError::Io(error.to_string()))?;
    if first == 0 {
        return Ok(None);
    }
    if first < prefix.len() {
        reader
            .read_exact(&mut prefix[first..])
            .map_err(|_| AdapterSupervisorError::TruncatedFrame)?;
    }
    let length = u32::from_be_bytes(prefix) as usize;
    if length == 0 {
        return Err(AdapterSupervisorError::EmptyFrame);
    }
    if length > max_frame_bytes {
        return Err(AdapterSupervisorError::FrameTooLarge(length));
    }
    let wire_bytes = length
        .checked_add(prefix.len())
        .ok_or(AdapterSupervisorError::FrameTooLarge(length))?;
    reserve_inbound_bytes(pending_bytes, wire_bytes, max_pending_bytes)?;

    let mut payload = vec![0_u8; length];
    if reader.read_exact(&mut payload).is_err() {
        pending_bytes.fetch_sub(wire_bytes, Ordering::AcqRel);
        return Err(AdapterSupervisorError::TruncatedFrame);
    }
    let frame = match AdapterFrame::decode(payload.as_slice()) {
        Ok(frame) => frame,
        Err(error) => {
            pending_bytes.fetch_sub(wire_bytes, Ordering::AcqRel);
            return Err(AdapterSupervisorError::Decode(error.to_string()));
        }
    };
    if let Err(error) = validate_contract_version(frame.contract_version.as_ref()) {
        pending_bytes.fetch_sub(wire_bytes, Ordering::AcqRel);
        return Err(error.into());
    }
    Ok(Some(QueuedInboundFrame { frame, wire_bytes }))
}
