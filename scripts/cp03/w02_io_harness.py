from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "kernel/crates/clever-kernel/src/adapter.rs"
TESTS = ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs"
FIXTURE = ROOT / "kernel/crates/clever-kernel/tests/fixtures/fake_adapter_sidecar.py"

SENTINEL = "DEFAULT_MAX_INBOUND_FRAMES"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one source match, found {count}")
    return text.replace(old, new, 1)


def patch_adapter(text: str) -> str:
    if SENTINEL in text:
        return text

    text = replace_once(
        text,
        """use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::{Display, Formatter},
    io::{Read, Write},
    path::Path,
    process::{Child, ChildStdin, Command, Stdio},
    sync::mpsc::{self, Receiver, RecvTimeoutError},
    thread::{self, JoinHandle},
    time::{Duration, SystemTime, UNIX_EPOCH},
};
""",
        """use std::{
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
    time::{Duration, SystemTime, UNIX_EPOCH},
};
""",
        "imports",
    )
    text = replace_once(
        text,
        "pub const DEFAULT_MAX_FRAME_BYTES: usize = 4 * 1024 * 1024;\n",
        """pub const DEFAULT_MAX_FRAME_BYTES: usize = 4 * 1024 * 1024;
pub const DEFAULT_MAX_INBOUND_FRAMES: usize = 64;
pub const DEFAULT_MAX_INBOUND_BYTES: usize = 16 * 1024 * 1024;
""",
        "bounded-I/O constants",
    )
    text = replace_once(
        text,
        """    EmptyFrame,
    TruncatedFrame,
    Timeout(&'static str),
""",
        """    EmptyFrame,
    TruncatedFrame,
    InboundQueueFull { max_frames: usize },
    InboundBytesExceeded { attempted: usize, max_bytes: usize },
    OutboundQueueFull,
    SessionPoisoned(String),
    Timeout(&'static str),
""",
        "error variants",
    )
    text = replace_once(
        text,
        """            Self::EmptyFrame => write!(formatter, "adapter emitted a zero-length frame"),
            Self::TruncatedFrame => write!(formatter, "adapter emitted a truncated frame"),
            Self::Timeout(stage) => write!(formatter, "adapter timed out during {stage}"),
""",
        """            Self::EmptyFrame => write!(formatter, "adapter emitted a zero-length frame"),
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
""",
        "error display",
    )
    text = replace_once(
        text,
        """#[derive(Debug, Clone, PartialEq, Eq)]
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
            max_restarts: 2,
            restart_backoff: Duration::from_millis(50),
        }
    }
}

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
}
""",
        """#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SupervisorPolicy {
    pub max_frame_bytes: usize,
    pub max_inbound_frames: usize,
    pub max_inbound_bytes: usize,
    pub handshake_timeout: Duration,
    pub request_timeout: Duration,
    pub write_timeout: Duration,
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
}
""",
        "policy and supervisor state",
    )
    text = replace_once(
        text,
        """        if policy.max_frame_bytes == 0 {
            return Err(AdapterSupervisorError::InvalidCommand(
                "max_frame_bytes must be positive".to_owned(),
            ));
        }
""",
        """        if policy.max_frame_bytes == 0
            || policy.max_inbound_frames == 0
            || policy.max_inbound_bytes == 0
            || policy.write_timeout.is_zero()
        {
            return Err(AdapterSupervisorError::InvalidCommand(
                "frame, inbound queue/byte budgets, and write_timeout must be positive".to_owned(),
            ));
        }
""",
        "policy validation",
    )
    text = replace_once(
        text,
        """        let (sender, receiver) = mpsc::channel();
        let max_frame_bytes = policy.max_frame_bytes;
        let reader = thread::spawn(move || {
            let mut output = stdout;
            loop {
                match read_framed_frame(&mut output, max_frame_bytes) {
                    Ok(Some(frame)) => {
                        if sender.send(Ok(frame)).is_err() {
                            break;
                        }
                    }
                    Ok(None) => {
                        let _ = sender.send(Err(AdapterSupervisorError::ProcessExited));
                        break;
                    }
                    Err(error) => {
                        let _ = sender.send(Err(error));
                        break;
                    }
                }
            }
        });

        let mut supervisor = Self {
            child,
            stdin,
            receiver,
            reader: Some(reader),
            identity,
            policy,
            negotiated_max_frame_bytes: max_frame_bytes,
            negotiated_features: BTreeSet::new(),
            next_frame_sequence: 0,
        };
""",
        """        let max_frame_bytes = policy.max_frame_bytes;
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
                        if let Err(TrySendError::Full(_)) = sender.try_send(Err(error.clone())) {
                            reader_state.poison(error);
                        }
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
        };
""",
        "bounded reader and writer workers",
    )
    text = replace_once(
        text,
        """        supervisor.negotiated_max_frame_bytes = negotiated_max;
        supervisor.negotiated_features = features.clone();
""",
        """        supervisor.negotiated_max_frame_bytes = negotiated_max;
        supervisor
            .inbound_state
            .frame_limit
            .store(negotiated_max, Ordering::Release);
        supervisor.negotiated_features = features.clone();
""",
        "negotiated dynamic frame limit",
    )
    text = replace_once(
        text,
        """    #[must_use]
    pub fn negotiated_features(&self) -> &BTreeSet<String> {
        &self.negotiated_features
    }
""",
        """    #[must_use]
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
""",
        "I/O observability accessors",
    )
    text = replace_once(
        text,
        """    fn write_frame(&mut self, frame: &AdapterFrame) -> Result<(), AdapterSupervisorError> {
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
        self.stdin
            .write_all(&length.to_be_bytes())
            .and_then(|_| self.stdin.write_all(&payload))
            .and_then(|_| self.stdin.flush())
            .map_err(|error| AdapterSupervisorError::Io(error.to_string()))
    }

    fn receive_frame(
        &self,
        timeout: Duration,
        stage: &'static str,
    ) -> Result<AdapterFrame, AdapterSupervisorError> {
        match self.receiver.recv_timeout(timeout) {
            Ok(result) => result,
            Err(RecvTimeoutError::Timeout) => Err(AdapterSupervisorError::Timeout(stage)),
            Err(RecvTimeoutError::Disconnected) => Err(AdapterSupervisorError::ProcessExited),
        }
    }
""",
        """    fn write_frame(&mut self, frame: &AdapterFrame) -> Result<(), AdapterSupervisorError> {
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
        let sender = self
            .writer_sender
            .as_ref()
            .cloned()
            .ok_or_else(|| AdapterSupervisorError::SessionPoisoned("writer unavailable".to_owned()))?;
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
        self.writer_sender.take();
        let _ = self.child.kill();
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
            Err(RecvTimeoutError::Disconnected) => {
                self.inbound_state
                    .fatal()
                    .map_or(Err(AdapterSupervisorError::ProcessExited), Err)
            }
        }
    }
""",
        "bounded write completion and receive accounting",
    )
    text = replace_once(
        text,
        """impl Drop for AdapterSupervisor {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
        if let Some(reader) = self.reader.take() {
            let _ = reader.join();
        }
    }
}
""",
        """impl Drop for AdapterSupervisor {
    fn drop(&mut self) {
        self.writer_sender.take();
        let _ = self.child.kill();
        let _ = self.child.wait();
        if let Some(reader) = self.reader.take() {
            let _ = reader.join();
        }
        if let Some(writer) = self.writer.take() {
            let _ = writer.join();
        }
    }
}
""",
        "writer worker drop",
    )
    text = replace_once(
        text,
        """fn read_framed_frame<R: Read>(
    reader: &mut R,
    max_frame_bytes: usize,
) -> Result<Option<AdapterFrame>, AdapterSupervisorError> {
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
    let mut payload = vec![0_u8; length];
    reader
        .read_exact(&mut payload)
        .map_err(|_| AdapterSupervisorError::TruncatedFrame)?;
    let frame = AdapterFrame::decode(payload.as_slice())
        .map_err(|error| AdapterSupervisorError::Decode(error.to_string()))?;
    validate_contract_version(frame.contract_version.as_ref())?;
    Ok(Some(frame))
}
""",
        """fn reserve_inbound_bytes(
    pending_bytes: &AtomicUsize,
    wire_bytes: usize,
    max_pending_bytes: usize,
) -> Result<(), AdapterSupervisorError> {
    let mut current = pending_bytes.load(Ordering::Acquire);
    loop {
        let attempted = current.checked_add(wire_bytes).unwrap_or(usize::MAX);
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
""",
        "wire budget before protobuf decode",
    )
    return text


def patch_fixture(text: str) -> str:
    if 'mode == "flood"' in text:
        return text
    return replace_once(
        text,
        """    ack = read_frame()
    if ack is None or ack.WhichOneof("body") != "hello_ack" or not ack.hello_ack.accepted:
        return 64

    while True:
""",
        """    ack = read_frame()
    if ack is None or ack.WhichOneof("body") != "hello_ack" or not ack.hello_ack.accepted:
        return 64

    if mode == "flood":
        time.sleep(0.15)
        for index in range(64):
            write_frame(
                frame(
                    f"flood-{index}",
                    "health",
                    health(runtime_pb2.RUNTIME_HEALTH_STATUS_READY),
                )
            )
        time.sleep(2)
        return 0
    if mode == "byte-flood":
        time.sleep(0.15)
        error = adapter_pb2.AdapterError(
            code="BYTE_FLOOD",
            message="x" * 8192,
            retryable=False,
        )
        write_frame(frame("byte-flood", "error", error))
        time.sleep(2)
        return 0
    if mode == "no-read-after-hello":
        time.sleep(5)
        return 0

    while True:
""",
        "adversarial sidecar modes",
    )


def patch_tests(text: str) -> str:
    if "inbound_frame_queue_is_bounded_under_flood" in text:
        return text
    text = replace_once(
        text,
        "use std::{collections::BTreeMap, env, path::PathBuf, time::Duration};\n",
        "use std::{collections::BTreeMap, env, path::PathBuf, thread, time::{Duration, Instant}};\n",
        "test imports",
    )
    addition = r'''

#[test]
fn inbound_frame_queue_is_bounded_under_flood() {
    let command = fake_command("flood");
    let mut policy = fast_policy();
    policy.max_inbound_frames = 1;
    policy.max_inbound_bytes = 64 * 1024;
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), policy)
        .expect("connect flood sidecar before adversarial burst");
    thread::sleep(Duration::from_millis(300));
    let error = supervisor
        .request_health()
        .expect_err("flood must poison bounded inbound queue");
    assert_eq!(
        error,
        AdapterSupervisorError::InboundQueueFull { max_frames: 1 }
    );
    assert!(supervisor.is_poisoned());
}

#[test]
fn inbound_wire_byte_budget_is_enforced_before_decode() {
    let command = fake_command("byte-flood");
    let mut policy = fast_policy();
    policy.max_inbound_frames = 8;
    policy.max_inbound_bytes = 1024;
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), policy)
        .expect("connect byte-flood sidecar before adversarial burst");
    thread::sleep(Duration::from_millis(300));
    let error = supervisor
        .request_health()
        .expect_err("oversized aggregate wire budget must poison session");
    match error {
        AdapterSupervisorError::InboundBytesExceeded {
            attempted,
            max_bytes,
        } => {
            assert!(attempted > max_bytes);
            assert_eq!(max_bytes, 1024);
        }
        other => panic!("unexpected inbound-byte error: {other}"),
    }
    assert_eq!(supervisor.pending_inbound_bytes(), 0);
    assert!(supervisor.is_poisoned());
}

#[test]
fn outbound_write_timeout_poison_session_when_peer_stops_reading() {
    let command = fake_command("no-read-after-hello");
    let mut policy = fast_policy();
    policy.write_timeout = Duration::from_millis(80);
    policy.request_timeout = Duration::from_secs(1);
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), policy)
        .expect("connect no-read sidecar");
    let reason = "x".repeat(3 * 1024 * 1024);
    let started = Instant::now();
    let error = supervisor
        .cancel("blocked-write", reason)
        .expect_err("peer that stops reading must hit bounded write deadline");
    assert_eq!(error, AdapterSupervisorError::Timeout("outbound write"));
    assert!(started.elapsed() < Duration::from_secs(2));
    assert!(supervisor.is_poisoned());
    let follow_up = supervisor
        .request_health()
        .expect_err("poisoned writer session must fail closed");
    assert!(matches!(
        follow_up,
        AdapterSupervisorError::SessionPoisoned(_)
    ));
}
'''
    return text.rstrip() + addition + "\n"


def validate() -> None:
    adapter = ADAPTER.read_text(encoding="utf-8")
    tests = TESTS.read_text(encoding="utf-8")
    fixture = FIXTURE.read_text(encoding="utf-8")
    required = [
        "DEFAULT_MAX_INBOUND_FRAMES",
        "mpsc::sync_channel(max_inbound_frames)",
        "reserve_inbound_bytes",
        "write_timeout",
        "Timeout(\"outbound write\")",
        "InboundQueueFull",
        "InboundBytesExceeded",
        "SessionPoisoned",
    ]
    missing = [token for token in required if token not in adapter]
    if missing:
        raise RuntimeError(f"adapter missing W02-03 tokens: {missing}")
    if "let (sender, receiver) = mpsc::channel();" in adapter:
        raise RuntimeError("unbounded inbound mpsc channel remains")
    for token in [
        "inbound_frame_queue_is_bounded_under_flood",
        "inbound_wire_byte_budget_is_enforced_before_decode",
        "outbound_write_timeout_poison_session_when_peer_stops_reading",
    ]:
        if token not in tests:
            raise RuntimeError(f"test missing: {token}")
    for mode in ['mode == "flood"', 'mode == "byte-flood"', 'mode == "no-read-after-hello"']:
        if mode not in fixture:
            raise RuntimeError(f"fixture mode missing: {mode}")


def apply() -> None:
    ADAPTER.write_text(patch_adapter(ADAPTER.read_text(encoding="utf-8")), encoding="utf-8")
    FIXTURE.write_text(patch_fixture(FIXTURE.read_text(encoding="utf-8")), encoding="utf-8")
    TESTS.write_text(patch_tests(TESTS.read_text(encoding="utf-8")), encoding="utf-8")
    validate()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.apply:
        apply()
    if args.check or not args.apply:
        validate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
