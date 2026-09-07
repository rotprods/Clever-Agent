use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::{Display, Formatter},
    io::{Read, Write},
    path::Path,
    process::{Child, ChildStdin, Command, Stdio},
    sync::mpsc::{self, Receiver, RecvTimeoutError},
    thread::{self, JoinHandle},
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use clever_contracts::{
    adapter_frame, AdapterCancel, AdapterFrame, AdapterHealthRequest, AdapterHelloAck,
    AdapterShutdown, CapabilityDescriptor, ContractVersion, LifecycleMode, NativeRegistryEntry,
    PlatformConstraint, ProvenanceRef, RegistryPrimitive, RegistrySnapshot, RegistrySnapshotRequest,
    RuntimeHealth, RuntimeHealthStatus, RuntimeOwner,
};
use prost::Message;

use crate::{
    capabilities::CapabilityRegistry, error::KernelError, version::validate_contract_version,
};

pub const DEFAULT_MAX_FRAME_BYTES: usize = 4 * 1024 * 1024;
const WIRE_MAJOR: u32 = 1;
const WIRE_MINOR: u32 = 1;
const REQUIRED_FEATURES: [&str; 5] = [
    "be32-length-prefix", "registry-snapshot", "runtime-health", "cancel", "shutdown",
];
const RESERVED_METADATA_TOKENS: [&str; 6] = [
    "permission", "scope", "risk", "policy", "authorization", "authz",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AdapterSupervisorError {
    Io(String),
    Decode(String),
    InvalidCommand(String),
    FrameTooLarge(usize),
    EmptyFrame,
    TruncatedFrame,
    Timeout(&'static str),
    ProcessExited,
    UnexpectedFrame(&'static str),
    InvalidHello(String),
    InvalidSnapshot(String),
    InvalidRuntimeResponse(String),
    ProtocolPoisoned,
    RestartBudgetExhausted { attempts: u32, last_error: String },
    Kernel(KernelError),
}

impl Display for AdapterSupervisorError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(message) => write!(formatter, "adapter I/O error: {message}"),
            Self::Decode(message) => write!(formatter, "adapter protobuf decode error: {message}"),
            Self::InvalidCommand(message) => write!(formatter, "invalid adapter command: {message}"),
            Self::FrameTooLarge(size) => write!(formatter, "adapter frame exceeds limit: {size} bytes"),
            Self::EmptyFrame => write!(formatter, "adapter emitted a zero-length frame"),
            Self::TruncatedFrame => write!(formatter, "adapter emitted a truncated frame"),
            Self::Timeout(stage) => write!(formatter, "adapter timed out during {stage}"),
            Self::ProcessExited => write!(formatter, "adapter exited before completing protocol"),
            Self::UnexpectedFrame(stage) => write!(formatter, "unexpected adapter frame during {stage}"),
            Self::InvalidHello(message) => write!(formatter, "invalid adapter hello: {message}"),
            Self::InvalidSnapshot(message) => write!(formatter, "invalid registry snapshot: {message}"),
            Self::InvalidRuntimeResponse(message) => write!(formatter, "invalid runtime response: {message}"),
            Self::ProtocolPoisoned => write!(formatter, "adapter protocol is poisoned; reconnect before reuse"),
            Self::RestartBudgetExhausted { attempts, last_error } => write!(
                formatter, "adapter restart budget exhausted after {attempts} attempts: {last_error}"
            ),
            Self::Kernel(error) => Display::fmt(error, formatter),
        }
    }
}
impl std::error::Error for AdapterSupervisorError {}
impl From<KernelError> for AdapterSupervisorError {
    fn from(value: KernelError) -> Self { Self::Kernel(value) }
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
        adapter_id: impl Into<String>, runtime_id: impl Into<String>,
        upstream_repository: impl Into<String>, upstream_commit: impl Into<String>,
    ) -> Self {
        Self {
            adapter_id: adapter_id.into(), runtime_id: runtime_id.into(),
            upstream_repository: upstream_repository.into(), upstream_commit: upstream_commit.into(),
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdapterCommand {
    pub program: String,
    pub args: Vec<String>,
    pub env: BTreeMap<String, String>,
}
impl AdapterCommand {
    #[must_use]
    pub fn new(program: impl Into<String>) -> Self {
        Self { program: program.into(), args: Vec::new(), env: BTreeMap::new() }
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SupervisorPolicy {
    pub max_frame_bytes: usize,
    pub handshake_timeout: Duration,
    pub request_timeout: Duration,
    pub max_restarts: u32,
    pub restart_backoff: Duration,
}
impl Default for SupervisorPolicy {
    fn default() -> Self {
        Self {
            max_frame_bytes: DEFAULT_MAX_FRAME_BYTES,
            handshake_timeout: Duration::from_secs(10),
            request_timeout: Duration::from_secs(5),
            max_restarts: 2, restart_backoff: Duration::from_millis(50),
        }
    }
}

/// Single-flight control-plane client. This is NOT an inference streaming executor.
/// W02-03/04 still own aggregate queue bounds, write deadlines and descendant cleanup.
pub struct AdapterSupervisor {
    child: Child,
    stdin: ChildStdin,
    receiver: Receiver<Result<AdapterFrame, AdapterSupervisorError>>,
    reader: Option<JoinHandle<()>>,
    identity: AdapterIdentity,
    policy: SupervisorPolicy,
    negotiated_max_frame_bytes: usize,
    negotiated_features: BTreeSet<String>,
    next_frame_sequence: u64,
    poisoned: bool,
}
impl AdapterSupervisor {
    pub fn connect_with_restarts(
        command: AdapterCommand, identity: AdapterIdentity, policy: SupervisorPolicy,
    ) -> Result<Self, AdapterSupervisorError> {
        let attempts = policy.max_restarts.saturating_add(1);
        let mut last_error = String::from("adapter did not start");
        for attempt in 0..attempts {
            match Self::start(command.clone(), identity.clone(), policy.clone()) {
                Ok(supervisor) => return Ok(supervisor),
                Err(error) => {
                    last_error = error.to_string();
                    if attempt.saturating_add(1) < attempts { thread::sleep(policy.restart_backoff); }
                }
            }
        }
        Err(AdapterSupervisorError::RestartBudgetExhausted { attempts, last_error })
    }
    pub fn start(
        command: AdapterCommand, identity: AdapterIdentity, policy: SupervisorPolicy,
    ) -> Result<Self, AdapterSupervisorError> {
        if command.program.trim().is_empty() || !Path::new(&command.program).is_absolute() {
            return Err(AdapterSupervisorError::InvalidCommand(
                "program must be a non-empty absolute path".to_owned(),
            ));
        }
        if policy.max_frame_bytes == 0 {
            return Err(AdapterSupervisorError::InvalidCommand("max_frame_bytes must be positive".to_owned()));
        }
        let mut process = Command::new(&command.program);
        process.args(&command.args).env_clear().envs(&command.env);
        process.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::inherit());
        let mut child = process.spawn().map_err(|error| AdapterSupervisorError::Io(error.to_string()))?;
        let stdin = child.stdin.take().ok_or(AdapterSupervisorError::UnexpectedFrame("stdin setup"))?;
        let stdout = child.stdout.take().ok_or(AdapterSupervisorError::UnexpectedFrame("stdout setup"))?;
        let (sender, receiver) = mpsc::channel();
        let max_frame_bytes = policy.max_frame_bytes;
        let reader = thread::spawn(move || {
            let mut output = stdout;
            loop {
                match read_framed_frame(&mut output, max_frame_bytes) {
                    Ok(Some(frame)) => { if sender.send(Ok(frame)).is_err() { break; } }
                    Ok(None) => { let _ = sender.send(Err(AdapterSupervisorError::ProcessExited)); break; }
                    Err(error) => { let _ = sender.send(Err(error)); break; }
                }
            }
        });
        let mut supervisor = Self {
            child, stdin, receiver, reader: Some(reader), identity, policy,
            negotiated_max_frame_bytes: max_frame_bytes,
            negotiated_features: BTreeSet::new(), next_frame_sequence: 0, poisoned: false,
        };
        let hello_frame = supervisor.receive_frame(supervisor.policy.handshake_timeout, "handshake")?;
        let (negotiated_max, features) = supervisor.validate_hello(&hello_frame)?;
        supervisor.negotiated_max_frame_bytes = negotiated_max;
        supervisor.negotiated_features = features.clone();
        supervisor.send_hello_ack(&hello_frame.frame_id, features)?;
        Ok(supervisor)
    }
    #[must_use]
    pub fn negotiated_max_frame_bytes(&self) -> usize { self.negotiated_max_frame_bytes }
    #[must_use]
    pub fn negotiated_features(&self) -> &BTreeSet<String> { &self.negotiated_features }

    fn fail<T>(&mut self, error: AdapterSupervisorError) -> Result<T, AdapterSupervisorError> {
        self.poisoned = true;
        Err(error)
    }
    /// A timeout or malformed reply makes stream position ambiguous. Never reuse it.
    fn exchange(
        &mut self, body: adapter_frame::Body, stage: &'static str,
    ) -> Result<AdapterFrame, AdapterSupervisorError> {
        if self.poisoned { return Err(AdapterSupervisorError::ProtocolPoisoned); }
        let request = self.next_control_frame(body, self.policy.request_timeout);
        let result = self.write_frame(&request).and_then(|()| {
            self.receive_frame(self.policy.request_timeout, stage)
        });
        let response = match result {
            Ok(frame) => frame,
            Err(error) => return self.fail(error),
        };
        if response.frame_id.trim().is_empty() || response.correlation_id != request.frame_id {
            return self.fail(AdapterSupervisorError::InvalidRuntimeResponse(
                "response frame_id is empty or correlation_id does not match the active request".to_owned(),
            ));
        }
        Ok(response)
    }
    pub fn request_registry_snapshot(&mut self) -> Result<RegistrySnapshot, AdapterSupervisorError> {
        let response = self.exchange(
            adapter_frame::Body::RegistrySnapshotRequest(RegistrySnapshotRequest {}), "registry snapshot",
        )?;
        match response.body {
            Some(adapter_frame::Body::RegistrySnapshot(snapshot)) if snapshot.runtime_id == self.identity.runtime_id => Ok(snapshot),
            Some(adapter_frame::Body::RegistrySnapshot(_)) => self.fail(AdapterSupervisorError::InvalidSnapshot("runtime mismatch".to_owned())),
            _ => self.fail(AdapterSupervisorError::UnexpectedFrame("registry snapshot")),
        }
    }
    pub fn request_health(&mut self) -> Result<RuntimeHealth, AdapterSupervisorError> {
        let response = self.exchange(adapter_frame::Body::HealthRequest(AdapterHealthRequest {}), "health request")?;
        self.extract_health(response, "health request")
    }
    pub fn cancel(
        &mut self, target_request_id: impl Into<String>, reason: impl Into<String>,
    ) -> Result<RuntimeHealth, AdapterSupervisorError> {
        let response = self.exchange(adapter_frame::Body::Cancel(AdapterCancel {
            target_request_id: target_request_id.into(), reason: reason.into(),
        }), "cancel")?;
        self.extract_health(response, "cancel")
    }
    pub fn shutdown(mut self, reason: impl Into<String>) -> Result<RuntimeHealth, AdapterSupervisorError> {
        let response = self.exchange(adapter_frame::Body::Shutdown(AdapterShutdown { reason: reason.into() }), "shutdown")?;
        let health = self.extract_health(response, "shutdown")?;
        if health.status != RuntimeHealthStatus::Stopping as i32 {
            return self.fail(AdapterSupervisorError::InvalidRuntimeResponse("shutdown did not return STOPPING".to_owned()));
        }
        self.child.wait().map_err(|error| AdapterSupervisorError::Io(error.to_string()))?;
        Ok(health)
    }
    fn validate_hello(&self, frame: &AdapterFrame) -> Result<(usize, BTreeSet<String>), AdapterSupervisorError> {
        validate_contract_version(frame.contract_version.as_ref())?;
        if frame.frame_id.trim().is_empty() || !frame.correlation_id.is_empty() {
            return Err(AdapterSupervisorError::InvalidHello("invalid initial frame identity".to_owned()));
        }
        let hello = match frame.body.as_ref() {
            Some(adapter_frame::Body::Hello(hello)) => hello,
            _ => return Err(AdapterSupervisorError::UnexpectedFrame("handshake")),
        };
        validate_contract_version(hello.contract_version.as_ref())?;
        if hello.adapter_id != self.identity.adapter_id || hello.upstream_repository != self.identity.upstream_repository || hello.upstream_commit != self.identity.upstream_commit {
            return Err(AdapterSupervisorError::InvalidHello("adapter or pinned upstream identity mismatch".to_owned()));
        }
        let runtime = hello.runtime.as_ref().ok_or_else(|| AdapterSupervisorError::InvalidHello("runtime descriptor missing".to_owned()))?;
        validate_contract_version(runtime.contract_version.as_ref())?;
        if runtime.runtime_id != self.identity.runtime_id || runtime.runtime_kind.trim().is_empty() {
            return Err(AdapterSupervisorError::InvalidHello("runtime identity/kind mismatch".to_owned()));
        }
        let peer_max = usize::try_from(hello.max_frame_bytes).map_err(|_| AdapterSupervisorError::InvalidHello("peer frame limit does not fit usize".to_owned()))?;
        if peer_max == 0 { return Err(AdapterSupervisorError::InvalidHello("peer frame limit is zero".to_owned())); }
        let advertised: BTreeSet<String> = hello.supported_features.iter().cloned().collect();
        for required in REQUIRED_FEATURES {
            if !advertised.contains(required) {
                return Err(AdapterSupervisorError::InvalidHello(format!("required feature missing: {required}")));
            }
        }
        Ok((peer_max.min(self.policy.max_frame_bytes), REQUIRED_FEATURES.iter().map(|s| (*s).to_owned()).collect()))
    }
    fn send_hello_ack(&mut self, correlation_id: &str, features: BTreeSet<String>) -> Result<(), AdapterSupervisorError> {
        self.write_frame(&AdapterFrame {
            contract_version: Some(contract_version()), frame_id: "kernel-hello-ack".to_owned(),
            correlation_id: correlation_id.to_owned(), sent_at: Some(timestamp_at(SystemTime::now())), deadline_at: None,
            body: Some(adapter_frame::Body::HelloAck(AdapterHelloAck {
                contract_version: Some(contract_version()), adapter_id: self.identity.adapter_id.clone(),
                accepted: true, reason: String::new(), max_frame_bytes: self.negotiated_max_frame_bytes as u64,
                negotiated_features: features.into_iter().collect(),
            })),
        })
    }
    fn next_control_frame(&mut self, body: adapter_frame::Body, timeout: Duration) -> AdapterFrame {
        self.next_frame_sequence = self.next_frame_sequence.saturating_add(1);
        let now = SystemTime::now();
        AdapterFrame {
            contract_version: Some(contract_version()), frame_id: format!("kernel-frame-{}", self.next_frame_sequence),
            correlation_id: String::new(), sent_at: Some(timestamp_at(now)), deadline_at: Some(timestamp_at(now + timeout)), body: Some(body),
        }
    }
    fn write_frame(&mut self, frame: &AdapterFrame) -> Result<(), AdapterSupervisorError> {
        validate_contract_version(frame.contract_version.as_ref())?;
        if frame.body.is_none() { return Err(AdapterSupervisorError::UnexpectedFrame("outbound write")); }
        // Check before allocating the serialized payload.
        let size = frame.encoded_len();
        if size == 0 { return Err(AdapterSupervisorError::EmptyFrame); }
        if size > self.negotiated_max_frame_bytes { return Err(AdapterSupervisorError::FrameTooLarge(size)); }
        let payload = frame.encode_to_vec();
        let length = u32::try_from(size).map_err(|_| AdapterSupervisorError::FrameTooLarge(size))?;
        self.stdin.write_all(&length.to_be_bytes())
            .and_then(|()| self.stdin.write_all(&payload)).and_then(|()| self.stdin.flush())
            .map_err(|error| AdapterSupervisorError::Io(error.to_string()))
    }
    fn receive_frame(&self, timeout: Duration, stage: &'static str) -> Result<AdapterFrame, AdapterSupervisorError> {
        let frame = match self.receiver.recv_timeout(timeout) {
            Ok(result) => result?,
            Err(RecvTimeoutError::Timeout) => return Err(AdapterSupervisorError::Timeout(stage)),
            Err(RecvTimeoutError::Disconnected) => return Err(AdapterSupervisorError::ProcessExited),
        };
        // Reader still allocates under the local ceiling; preallocation negotiation is W02-03.
        if frame.encoded_len() > self.negotiated_max_frame_bytes {
            return Err(AdapterSupervisorError::FrameTooLarge(frame.encoded_len()));
        }
        if frame.body.is_none() { return Err(AdapterSupervisorError::UnexpectedFrame(stage)); }
        Ok(frame)
    }
    fn extract_health(&mut self, response: AdapterFrame, stage: &'static str) -> Result<RuntimeHealth, AdapterSupervisorError> {
        let health = match response.body {
            Some(adapter_frame::Body::Health(health)) => health,
            _ => return self.fail(AdapterSupervisorError::UnexpectedFrame(stage)),
        };
        if let Err(error) = validate_contract_version(health.contract_version.as_ref()) { return self.fail(error.into()); }
        let status = RuntimeHealthStatus::try_from(health.status);
        if health.runtime_id != self.identity.runtime_id || status.is_err() || health.status == 0 {
            return self.fail(AdapterSupervisorError::InvalidRuntimeResponse("invalid health identity/status".to_owned()));
        }
        if health.status == RuntimeHealthStatus::Ready as i32 && (!health.degradation_reasons.is_empty() || health.dropped_event_count > 0 || health.failed_action_count > 0) {
            return self.fail(AdapterSupervisorError::InvalidRuntimeResponse("READY contradicts degradation or failure counters".to_owned()));
        }
        Ok(health)
    }
}
impl Drop for AdapterSupervisor {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
        if let Some(reader) = self.reader.take() { let _ = reader.join(); }
    }
}

pub fn bridge_registry_snapshot(
    snapshot: &RegistrySnapshot, registry: &mut CapabilityRegistry, runtime_id: &str,
    adapter_id: &str, source_repo: &str, source_commit: &str,
) -> Result<Vec<String>, AdapterSupervisorError> {
    if snapshot.runtime_id != runtime_id || runtime_id.trim().is_empty() {
        return Err(AdapterSupervisorError::InvalidSnapshot("snapshot runtime_id does not match expected runtime".to_owned()));
    }
    if adapter_id.trim().is_empty() || source_repo.trim().is_empty() || source_commit.trim().is_empty() {
        return Err(AdapterSupervisorError::InvalidSnapshot("bridge provenance/adapter identity is incomplete".to_owned()));
    }
    let descriptors = snapshot.entries.iter().map(|entry| {
        descriptor_from_registry_entry(entry, runtime_id, adapter_id, source_repo, source_commit)
    }).collect::<Result<Vec<_>, _>>()?;
    registry.register_batch(descriptors).map_err(Into::into)
}
fn descriptor_from_registry_entry(
    entry: &NativeRegistryEntry, runtime_id: &str, adapter_id: &str, source_repo: &str, source_commit: &str,
) -> Result<CapabilityDescriptor, AdapterSupervisorError> {
    if entry.key.trim().is_empty() || entry.implementation.trim().is_empty() {
        return Err(AdapterSupervisorError::InvalidSnapshot("registry entry key/implementation is empty".to_owned()));
    }
    let primitive = RegistryPrimitive::try_from(entry.primitive).map_err(|_| AdapterSupervisorError::InvalidSnapshot(format!("unknown registry primitive {}", entry.primitive)))?;
    let primitive_slug = primitive_slug(primitive)?;
    let capability_id = format!("openjarvis.registry.{primitive_slug}.{}", hex_key(&entry.key));
    let mut extension_metadata = entry.metadata.clone();
    extension_metadata.retain(|key, _| !is_reserved_metadata_key(key));
    extension_metadata.insert("native_key".to_owned(), entry.key.clone());
    extension_metadata.insert("native_implementation".to_owned(), entry.implementation.clone());
    extension_metadata.insert("native_type".to_owned(), entry.native_type.clone());
    extension_metadata.insert("registry_primitive".to_owned(), primitive_slug.to_owned());
    Ok(CapabilityDescriptor {
        contract_version: Some(contract_version()), capability_id,
        family: format!("openjarvis.registry.{primitive_slug}"), name: entry.key.clone(),
        owner: Some(RuntimeOwner { runtime_id: runtime_id.to_owned(), adapter_id: adapter_id.to_owned(), device_id: String::new(), process_id: String::new() }),
        implementation_version: source_commit.to_owned(), interface_contract: "clever.v1.AdapterFrame/RegistrySnapshot".to_owned(),
        interface_version: format!("{WIRE_MAJOR}.{WIRE_MINOR}"), lifecycle_mode: LifecycleMode::Persistent as i32,
        permissions: Vec::new(), state_effects: Vec::new(), side_effects: Vec::new(),
        platform_constraints: entry.platform_constraints.iter().map(|platform| PlatformConstraint { platform: platform.clone(), minimum_version: String::new(), required_features: Vec::new() }).collect(),
        rollback_supported: false,
        provenance: vec![ProvenanceRef { source_repo: source_repo.to_owned(), source_commit: source_commit.to_owned(), source_path: String::new(), source_symbol: entry.implementation.clone() }],
        evidence: Vec::new(), extension_metadata,
    })
}
fn primitive_slug(primitive: RegistryPrimitive) -> Result<&'static str, AdapterSupervisorError> {
    match primitive {
        RegistryPrimitive::Unspecified => Err(AdapterSupervisorError::InvalidSnapshot("registry primitive is unspecified".to_owned())),
        RegistryPrimitive::Model => Ok("model"), RegistryPrimitive::Engine => Ok("engine"),
        RegistryPrimitive::Memory => Ok("memory"), RegistryPrimitive::FactStore => Ok("fact_store"),
        RegistryPrimitive::Agent => Ok("agent"), RegistryPrimitive::Tool => Ok("tool"),
        RegistryPrimitive::RouterPolicy => Ok("router_policy"), RegistryPrimitive::Benchmark => Ok("benchmark"),
        RegistryPrimitive::Channel => Ok("channel"), RegistryPrimitive::Learning => Ok("learning"),
        RegistryPrimitive::Skill => Ok("skill"), RegistryPrimitive::Speech => Ok("speech"),
        RegistryPrimitive::Compression => Ok("compression"), RegistryPrimitive::Tts => Ok("tts"),
        RegistryPrimitive::Connector => Ok("connector"), RegistryPrimitive::Miner => Ok("miner"),
    }
}
fn is_reserved_metadata_key(key: &str) -> bool {
    let normalized = key.to_ascii_lowercase();
    RESERVED_METADATA_TOKENS.iter().any(|reserved| normalized.contains(reserved))
}
fn hex_key(value: &str) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut encoded = String::with_capacity(value.len().saturating_mul(2));
    for byte in value.as_bytes() { encoded.push(HEX[(byte >> 4) as usize] as char); encoded.push(HEX[(byte & 0x0f) as usize] as char); }
    encoded
}
fn contract_version() -> ContractVersion { ContractVersion { major: WIRE_MAJOR, minor: WIRE_MINOR } }
fn timestamp_at(time: SystemTime) -> prost_types::Timestamp {
    let duration = time.duration_since(UNIX_EPOCH).unwrap_or_default();
    prost_types::Timestamp { seconds: i64::try_from(duration.as_secs()).unwrap_or(i64::MAX), nanos: i32::try_from(duration.subsec_nanos()).unwrap_or(i32::MAX) }
}
fn read_framed_frame<R: Read>(reader: &mut R, max_frame_bytes: usize) -> Result<Option<AdapterFrame>, AdapterSupervisorError> {
    let mut prefix = [0_u8; 4];
    let first = reader.read(&mut prefix).map_err(|error| AdapterSupervisorError::Io(error.to_string()))?;
    if first == 0 { return Ok(None); }
    if first < prefix.len() { reader.read_exact(&mut prefix[first..]).map_err(|_| AdapterSupervisorError::TruncatedFrame)?; }
    let length = u32::from_be_bytes(prefix) as usize;
    if length == 0 { return Err(AdapterSupervisorError::EmptyFrame); }
    if length > max_frame_bytes { return Err(AdapterSupervisorError::FrameTooLarge(length)); }
    let mut payload = vec![0_u8; length];
    reader.read_exact(&mut payload).map_err(|_| AdapterSupervisorError::TruncatedFrame)?;
    let frame = AdapterFrame::decode(payload.as_slice()).map_err(|error| AdapterSupervisorError::Decode(error.to_string()))?;
    validate_contract_version(frame.contract_version.as_ref())?;
    Ok(Some(frame))
}
