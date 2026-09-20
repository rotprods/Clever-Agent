from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "kernel/crates/clever-kernel/src/adapter.rs"
LEGACY_TEST = ROOT / "kernel/crates/clever-kernel/tests/lifecycle_legacy_regressions.rs"
LIFECYCLE_TEST = ROOT / "kernel/crates/clever-kernel/tests/adapter_lifecycle.rs"
PEER = ROOT / "kernel/crates/clever-kernel/tests/fixtures/lifecycle_peer.py"

MARKERS = (
    "pub struct AdapterCleanupCommand",
    "pub shutdown_timeout: Duration",
    "pub thread_join_timeout: Duration",
    "process.process_group(0)",
    "fn wait_child_bounded(",
    "fn terminate_bounded(",
    "fn join_threads_bounded(",
    "fn run_cleanup_bounded(",
)

PEER_SOURCE = r'''"""Lifecycle adversary for W02-04. Never loads an LLM or accesses the network."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time


def handshake() -> None:
    wire.write_frame(wire.hello())
    ack = wire.read_frame()
    if ack is None or ack.WhichOneof("body") != "hello_ack" or not ack.hello_ack.accepted:
        raise SystemExit(64)


def grandchild(pid_file: str) -> int:
    Path(pid_file).write_text(str(os.getpid()), encoding="utf-8")
    time.sleep(60)
    return 0


def cleanup_marker(path: str) -> int:
    Path(path).write_text("cleanup-ran\n", encoding="utf-8")
    return 0


def cleanup_hang(path: str) -> int:
    Path(path).write_text("cleanup-started\n", encoding="utf-8")
    time.sleep(60)
    return 0


def serve(mode: str) -> int:
    global wire
    import fake_adapter_sidecar as wire
    handshake()
    if mode == "spawn-grandchild":
        pid_file = os.environ["CLEVER_LIFECYCLE_PID_FILE"]
        subprocess.Popen(
            [sys.executable, __file__, "grandchild", pid_file],
            stdin=subprocess.DEVNULL,
            stdout=sys.stdout,
            stderr=sys.stderr,
            close_fds=True,
        )
    while True:
        request = wire.read_frame()
        if request is None:
            return 0
        body = request.WhichOneof("body")
        if body == "shutdown":
            response = wire.frame(
                f"shutdown:{request.frame_id}",
                "health",
                wire.health(wire.runtime_pb2.RUNTIME_HEALTH_STATUS_STOPPING),
                correlation_id=request.frame_id,
            )
            wire.write_frame(response)
            if mode == "stopping-hang":
                time.sleep(60)
            return 0
        if body == "health_request" or body == "cancel":
            wire.write_frame(
                wire.frame(
                    f"health:{request.frame_id}",
                    "health",
                    wire.health(wire.runtime_pb2.RUNTIME_HEALTH_STATUS_READY),
                    correlation_id=request.frame_id,
                )
            )
        else:
            error = wire.adapter_pb2.AdapterError(code="UNSUPPORTED", message=str(body), retryable=False)
            wire.write_frame(wire.frame(f"error:{request.frame_id}", "error", error, correlation_id=request.frame_id))


def main() -> int:
    mode = sys.argv[1]
    if mode == "grandchild":
        return grandchild(sys.argv[2])
    if mode == "cleanup-marker":
        return cleanup_marker(sys.argv[2])
    if mode == "cleanup-hang":
        return cleanup_hang(sys.argv[2])
    return serve(mode)


if __name__ == "__main__":
    raise SystemExit(main())
'''

LEGACY_TEST_SOURCE = r'''use clever_kernel::adapter::{
    AdapterCommand, AdapterIdentity, AdapterSupervisor, AdapterSupervisorError, SupervisorPolicy,
};
use std::{
    env,
    fs,
    path::{Path, PathBuf},
    thread,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .expect("repository root")
        .to_path_buf()
}

fn unique_path(label: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    env::temp_dir().join(format!("clever-{label}-{}-{nonce}", std::process::id()))
}

fn command(mode: &str, pid_file: Option<&Path>) -> AdapterCommand {
    let python = env::var("CLEVER_TEST_PYTHON")
        .expect("MANDATORY: CLEVER_TEST_PYTHON is required for lifecycle regressions");
    let mut command = AdapterCommand::new(python);
    command.args = vec![
        root()
            .join("kernel/crates/clever-kernel/tests/fixtures/lifecycle_peer.py")
            .display()
            .to_string(),
        mode.to_owned(),
    ];
    command.env.insert(
        "PYTHONPATH".to_owned(),
        root().join("contracts/sdk/python/gen").display().to_string(),
    );
    if let Some(path) = pid_file {
        command.env.insert(
            "CLEVER_LIFECYCLE_PID_FILE".to_owned(),
            path.display().to_string(),
        );
    }
    command
}

fn identity() -> AdapterIdentity {
    AdapterIdentity::new(
        "fake.adapter",
        "fake-runtime",
        "https://example.invalid/fake",
        "fake-commit",
    )
}

fn policy() -> SupervisorPolicy {
    SupervisorPolicy {
        handshake_timeout: Duration::from_secs(2),
        request_timeout: Duration::from_secs(2),
        ..SupervisorPolicy::default()
    }
}

fn wait_for_file(path: &Path) {
    let deadline = Instant::now() + Duration::from_secs(2);
    while !path.exists() && Instant::now() < deadline {
        thread::sleep(Duration::from_millis(10));
    }
    assert!(path.exists(), "lifecycle peer did not publish descendant pid");
}

#[cfg(target_os = "linux")]
fn process_exists(pid: u32) -> bool {
    Path::new(&format!("/proc/{pid}")).exists()
}

#[cfg(not(target_os = "linux"))]
fn process_exists(pid: u32) -> bool {
    std::process::Command::new("/bin/kill")
        .args(["-0", &pid.to_string()])
        .status()
        .is_ok_and(|status| status.success())
}

fn wait_process_gone(pid: u32) -> bool {
    let deadline = Instant::now() + Duration::from_secs(3);
    while process_exists(pid) && Instant::now() < deadline {
        thread::sleep(Duration::from_millis(10));
    }
    !process_exists(pid)
}

#[test]
fn shutdown_stopping_without_exit_is_bounded_and_forced() {
    let supervisor = AdapterSupervisor::start(command("stopping-hang", None), identity(), policy())
        .expect("lifecycle peer handshake");
    let started = Instant::now();
    let result = supervisor.shutdown("bounded shutdown proof");
    assert!(matches!(result, Err(AdapterSupervisorError::Timeout("shutdown exit"))));
    assert!(started.elapsed() < Duration::from_secs(5));
}

#[test]
fn drop_kills_descendant_retaining_stdout_pipe() {
    let pid_file = env::var("CLEVER_LIFECYCLE_PID_FILE")
        .map(PathBuf::from)
        .unwrap_or_else(|_| unique_path("grandchild.pid"));
    let _ = fs::remove_file(&pid_file);
    let supervisor = AdapterSupervisor::start(
        command("spawn-grandchild", Some(&pid_file)),
        identity(),
        policy(),
    )
    .expect("descendant peer handshake");
    wait_for_file(&pid_file);
    let pid: u32 = fs::read_to_string(&pid_file)
        .expect("pid file")
        .trim()
        .parse()
        .expect("pid");
    let started = Instant::now();
    drop(supervisor);
    assert!(started.elapsed() < Duration::from_secs(5));
    assert!(wait_process_gone(pid), "descendant survived supervisor drop: {pid}");
    let _ = fs::remove_file(pid_file);
}
'''

LIFECYCLE_TEST_SOURCE = r'''use clever_kernel::adapter::{
    AdapterCleanupCommand, AdapterCommand, AdapterIdentity, AdapterSupervisor,
    AdapterSupervisorError, SupervisorPolicy,
};
use std::{env, fs, path::{Path, PathBuf}, time::{Duration, Instant, SystemTime, UNIX_EPOCH}};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .expect("repository root")
        .to_path_buf()
}

fn unique_path(label: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    env::temp_dir().join(format!("clever-{label}-{}-{nonce}", std::process::id()))
}

fn python() -> String {
    env::var("CLEVER_TEST_PYTHON")
        .expect("MANDATORY: CLEVER_TEST_PYTHON is required for lifecycle tests")
}

fn command(mode: &str) -> AdapterCommand {
    let mut command = AdapterCommand::new(python());
    command.args = vec![
        root()
            .join("kernel/crates/clever-kernel/tests/fixtures/lifecycle_peer.py")
            .display()
            .to_string(),
        mode.to_owned(),
    ];
    command.env.insert(
        "PYTHONPATH".to_owned(),
        root().join("contracts/sdk/python/gen").display().to_string(),
    );
    command
}

fn cleanup(mode: &str, marker: &Path) -> AdapterCleanupCommand {
    let mut cleanup = AdapterCleanupCommand::new(python());
    cleanup.args = vec![
        root()
            .join("kernel/crates/clever-kernel/tests/fixtures/lifecycle_peer.py")
            .display()
            .to_string(),
        mode.to_owned(),
        marker.display().to_string(),
    ];
    cleanup
}

fn identity() -> AdapterIdentity {
    AdapterIdentity::new(
        "fake.adapter",
        "fake-runtime",
        "https://example.invalid/fake",
        "fake-commit",
    )
}

fn fast_policy() -> SupervisorPolicy {
    SupervisorPolicy {
        handshake_timeout: Duration::from_secs(2),
        request_timeout: Duration::from_secs(2),
        shutdown_timeout: Duration::from_millis(120),
        thread_join_timeout: Duration::from_millis(120),
        cleanup_timeout: Duration::from_millis(120),
        termination_poll_interval: Duration::from_millis(5),
        ..SupervisorPolicy::default()
    }
}

#[test]
fn forced_shutdown_runs_external_cleanup_hook() {
    let marker = unique_path("cleanup.marker");
    let _ = fs::remove_file(&marker);
    let mut command = command("stopping-hang");
    command.cleanup = Some(cleanup("cleanup-marker", &marker));
    let supervisor = AdapterSupervisor::start(command, identity(), fast_policy())
        .expect("cleanup peer handshake");
    let result = supervisor.shutdown("force cleanup");
    assert!(matches!(result, Err(AdapterSupervisorError::Timeout("shutdown exit"))));
    assert_eq!(fs::read_to_string(&marker).expect("cleanup marker"), "cleanup-ran\n");
    let _ = fs::remove_file(marker);
}

#[test]
fn cleanup_hook_that_hangs_is_itself_bounded() {
    let marker = unique_path("cleanup-hang.marker");
    let _ = fs::remove_file(&marker);
    let mut command = command("stopping-hang");
    command.cleanup = Some(cleanup("cleanup-hang", &marker));
    let supervisor = AdapterSupervisor::start(command, identity(), fast_policy())
        .expect("cleanup-hang peer handshake");
    let started = Instant::now();
    let result = supervisor.shutdown("force bounded cleanup");
    assert!(matches!(result, Err(AdapterSupervisorError::Timeout("shutdown exit"))));
    assert!(started.elapsed() < Duration::from_secs(3));
    assert_eq!(fs::read_to_string(&marker).expect("cleanup started marker"), "cleanup-started\n");
    let _ = fs::remove_file(marker);
}

#[test]
fn cleanup_program_must_be_absolute() {
    let marker = unique_path("invalid-cleanup.marker");
    let mut command = command("stopping-hang");
    command.cleanup = Some(AdapterCleanupCommand::new("python3"));
    let error = AdapterSupervisor::start(command, identity(), fast_policy())
        .err()
        .expect("relative cleanup unexpectedly accepted");
    assert!(matches!(error, AdapterSupervisorError::InvalidCommand(_)));
    assert!(!marker.exists());
}
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def replace_region(text: str, start: str, end: str, replacement: str, label: str) -> str:
    if replacement.strip() in text:
        return text
    start_index = text.find(start)
    if start_index < 0:
        raise RuntimeError(f"{label}: start anchor missing")
    end_index = text.find(end, start_index)
    if end_index < 0:
        raise RuntimeError(f"{label}: end anchor missing")
    return text[:start_index] + replacement + text[end_index:]


def patch_adapter(text: str) -> str:
    text = replace_once(
        text,
        "    time::{Duration, SystemTime, UNIX_EPOCH},\n};\n",
        "    time::{Duration, Instant, SystemTime, UNIX_EPOCH},\n};\n\n#[cfg(unix)]\nuse std::os::unix::process::CommandExt;\n",
        "Instant/CommandExt import",
    )

    cleanup_struct = '''#[derive(Debug, Clone, PartialEq, Eq)]\npub struct AdapterCleanupCommand {\n    pub program: String,\n    pub args: Vec<String>,\n    pub env: BTreeMap<String, String>,\n}\n\nimpl AdapterCleanupCommand {\n    #[must_use]\n    pub fn new(program: impl Into<String>) -> Self {\n        Self {\n            program: program.into(),\n            args: Vec::new(),\n            env: BTreeMap::new(),\n        }\n    }\n}\n\n'''
    if "pub struct AdapterCleanupCommand" not in text:
        anchor = "#[derive(Debug, Clone, PartialEq, Eq)]\npub struct AdapterCommand {\n"
        if anchor not in text:
            raise RuntimeError("AdapterCommand anchor missing")
        text = text.replace(anchor, cleanup_struct + anchor, 1)

    text = replace_once(
        text,
        "pub struct AdapterCommand {\n    pub program: String,\n    pub args: Vec<String>,\n    pub env: BTreeMap<String, String>,\n}",
        "pub struct AdapterCommand {\n    pub program: String,\n    pub args: Vec<String>,\n    pub env: BTreeMap<String, String>,\n    pub cleanup: Option<AdapterCleanupCommand>,\n}",
        "AdapterCommand cleanup field",
    )
    text = replace_once(
        text,
        "            program: program.into(),\n            args: Vec::new(),\n            env: BTreeMap::new(),\n        }\n    }\n}\n\n#[derive(Debug, Clone, PartialEq, Eq)]\npub struct SupervisorPolicy",
        "            program: program.into(),\n            args: Vec::new(),\n            env: BTreeMap::new(),\n            cleanup: None,\n        }\n    }\n}\n\n#[derive(Debug, Clone, PartialEq, Eq)]\npub struct SupervisorPolicy",
        "AdapterCommand constructor",
    )

    text = replace_once(
        text,
        "    pub request_timeout: Duration,\n    pub write_timeout: Duration,\n    pub max_restarts: u32,",
        "    pub request_timeout: Duration,\n    pub write_timeout: Duration,\n    pub shutdown_timeout: Duration,\n    pub thread_join_timeout: Duration,\n    pub cleanup_timeout: Duration,\n    pub termination_poll_interval: Duration,\n    pub max_restarts: u32,",
        "SupervisorPolicy fields",
    )
    text = replace_once(
        text,
        "            request_timeout: Duration::from_secs(5),\n            write_timeout: Duration::from_secs(5),\n            max_restarts: 2,",
        "            request_timeout: Duration::from_secs(5),\n            write_timeout: Duration::from_secs(5),\n            shutdown_timeout: Duration::from_secs(2),\n            thread_join_timeout: Duration::from_millis(500),\n            cleanup_timeout: Duration::from_secs(2),\n            termination_poll_interval: Duration::from_millis(10),\n            max_restarts: 2,",
        "SupervisorPolicy defaults",
    )

    text = replace_once(
        text,
        "    next_frame_sequence: u64,\n    session_poisoned: Option<String>,\n}",
        "    next_frame_sequence: u64,\n    session_poisoned: Option<String>,\n    process_group_id: Option<u32>,\n    cleanup: Option<AdapterCleanupCommand>,\n    termination_complete: bool,\n}",
        "supervisor lifecycle fields",
    )

    text = replace_once(
        text,
        "            || policy.max_inbound_bytes == 0\n            || policy.write_timeout.is_zero()\n",
        "            || policy.max_inbound_bytes == 0\n            || policy.write_timeout.is_zero()\n            || policy.shutdown_timeout.is_zero()\n            || policy.thread_join_timeout.is_zero()\n            || policy.cleanup_timeout.is_zero()\n            || policy.termination_poll_interval.is_zero()\n",
        "policy lifecycle validation",
    )
    text = replace_once(
        text,
        '                "frame, inbound queue/byte budgets, and write_timeout must be positive".to_owned(),',
        '                "frame/queue budgets and all I/O/lifecycle timeouts must be positive".to_owned(),',
        "policy validation message",
    )

    validation_anchor = "        let mut process = Command::new(&command.program);\n"
    validation_block = '''        if let Some(cleanup) = &command.cleanup {\n            if cleanup.program.trim().is_empty() || !Path::new(&cleanup.program).is_absolute() {\n                return Err(AdapterSupervisorError::InvalidCommand(\n                    \"cleanup program must be a non-empty absolute path\".to_owned(),\n                ));\n            }\n        }\n\n        let cleanup = command.cleanup.clone();\n        let mut process = Command::new(&command.program);\n'''
    text = replace_once(text, validation_anchor, validation_block, "cleanup validation")

    text = replace_once(
        text,
        "        process.env_clear();\n        process.envs(&command.env);\n        process\n",
        "        process.env_clear();\n        process.envs(&command.env);\n        #[cfg(unix)]\n        {\n            process.process_group(0);\n        }\n        process\n",
        "process group setup",
    )

    text = replace_once(
        text,
        "        let stdin = child\n            .stdin\n",
        "        #[cfg(unix)]\n        let process_group_id = Some(child.id());\n        #[cfg(not(unix))]\n        let process_group_id = None;\n        let stdin = child\n            .stdin\n",
        "process group capture",
    )

    text = replace_once(
        text,
        "            next_frame_sequence: 0,\n            session_poisoned: None,\n        };",
        "            next_frame_sequence: 0,\n            session_poisoned: None,\n            process_group_id,\n            cleanup,\n            termination_complete: false,\n        };",
        "supervisor lifecycle construction",
    )

    shutdown = '''    pub fn shutdown(\n        mut self,\n        reason: impl Into<String>,\n    ) -> Result<RuntimeHealth, AdapterSupervisorError> {\n        let response = self.exchange_control(\n            adapter_frame::Body::Shutdown(AdapterShutdown {\n                reason: reason.into(),\n            }),\n            \"shutdown\",\n        )?;\n        let health = self.extract_health(response, \"shutdown\")?;\n        if health.status != RuntimeHealthStatus::Stopping as i32 {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                \"shutdown did not return STOPPING\".to_owned(),\n            ));\n        }\n        self.writer_sender.take();\n        if !wait_child_bounded(\n            &mut self.child,\n            self.policy.shutdown_timeout,\n            self.policy.termination_poll_interval,\n        )? {\n            self.terminate_bounded();\n            return Err(AdapterSupervisorError::Timeout(\"shutdown exit\"));\n        }\n        if !self.join_threads_bounded() {\n            self.terminate_bounded();\n            return Err(AdapterSupervisorError::Timeout(\"shutdown I/O drain\"));\n        }\n        self.termination_complete = true;\n        Ok(health)\n    }\n\n'''
    text = replace_region(text, "    pub fn shutdown(\n", "    fn validate_hello(\n", shutdown, "bounded shutdown")

    lifecycle_methods = '''    fn poison_session(&mut self, reason: impl Into<String>) {\n        if self.session_poisoned.is_none() {\n            self.session_poisoned = Some(reason.into());\n        }\n        self.terminate_bounded();\n    }\n\n    fn terminate_bounded(&mut self) {\n        if self.termination_complete {\n            return;\n        }\n        self.writer_sender.take();\n        self.signal_process_group();\n        let _ = self.child.kill();\n        self.run_cleanup_bounded();\n        let _ = wait_child_bounded(\n            &mut self.child,\n            self.policy.shutdown_timeout,\n            self.policy.termination_poll_interval,\n        );\n        let _ = self.join_threads_bounded();\n        self.termination_complete = true;\n    }\n\n    fn signal_process_group(&self) {\n        #[cfg(unix)]\n        if let Some(group_id) = self.process_group_id {\n            let target = format!(\"-{group_id}\");\n            let mut command = Command::new(\"/bin/kill\");\n            command\n                .env_clear()\n                .args([\"-KILL\", \"--\", target.as_str()])\n                .stdin(Stdio::null())\n                .stdout(Stdio::null())\n                .stderr(Stdio::null());\n            if let Ok(mut killer) = command.spawn() {\n                let _ = wait_child_bounded(\n                    &mut killer,\n                    self.policy.cleanup_timeout,\n                    self.policy.termination_poll_interval,\n                );\n                let _ = killer.kill();\n            }\n        }\n    }\n\n    fn run_cleanup_bounded(&self) {\n        let Some(cleanup) = &self.cleanup else {\n            return;\n        };\n        let mut command = Command::new(&cleanup.program);\n        command\n            .args(&cleanup.args)\n            .env_clear()\n            .envs(&cleanup.env)\n            .stdin(Stdio::null())\n            .stdout(Stdio::null())\n            .stderr(Stdio::null());\n        let Ok(mut cleanup_process) = command.spawn() else {\n            return;\n        };\n        match wait_child_bounded(\n            &mut cleanup_process,\n            self.policy.cleanup_timeout,\n            self.policy.termination_poll_interval,\n        ) {\n            Ok(true) => {}\n            _ => {\n                let _ = cleanup_process.kill();\n                let _ = wait_child_bounded(\n                    &mut cleanup_process,\n                    self.policy.thread_join_timeout,\n                    self.policy.termination_poll_interval,\n                );\n            }\n        }\n    }\n\n    fn join_threads_bounded(&mut self) -> bool {\n        let reader_done = join_handle_bounded(\n            &mut self.reader,\n            self.policy.thread_join_timeout,\n            self.policy.termination_poll_interval,\n        );\n        let writer_done = join_handle_bounded(\n            &mut self.writer,\n            self.policy.thread_join_timeout,\n            self.policy.termination_poll_interval,\n        );\n        reader_done && writer_done\n    }\n\n'''
    text = replace_region(
        text,
        "    fn poison_session(&mut self, reason: impl Into<String>) {\n",
        "    fn receive_frame(\n",
        lifecycle_methods,
        "bounded terminate helpers",
    )

    drop_impl = '''impl Drop for AdapterSupervisor {\n    fn drop(&mut self) {\n        if !self.termination_complete {\n            self.terminate_bounded();\n        }\n    }\n}\n\n'''
    text = replace_region(
        text,
        "impl Drop for AdapterSupervisor {\n",
        "pub fn bridge_registry_snapshot(\n",
        drop_impl,
        "bounded Drop",
    )

    helpers = '''fn wait_child_bounded(\n    child: &mut Child,\n    timeout: Duration,\n    poll_interval: Duration,\n) -> Result<bool, AdapterSupervisorError> {\n    let deadline = Instant::now() + timeout;\n    loop {\n        match child\n            .try_wait()\n            .map_err(|error| AdapterSupervisorError::Io(error.to_string()))?\n        {\n            Some(_) => return Ok(true),\n            None if Instant::now() >= deadline => return Ok(false),\n            None => thread::sleep(poll_interval),\n        }\n    }\n}\n\nfn join_handle_bounded(\n    handle: &mut Option<JoinHandle<()>>,\n    timeout: Duration,\n    poll_interval: Duration,\n) -> bool {\n    let Some(thread_handle) = handle.as_ref() else {\n        return true;\n    };\n    let deadline = Instant::now() + timeout;\n    while !thread_handle.is_finished() && Instant::now() < deadline {\n        thread::sleep(poll_interval);\n    }\n    let finished = handle.as_ref().is_none_or(JoinHandle::is_finished);\n    if finished {\n        if let Some(thread_handle) = handle.take() {\n            let _ = thread_handle.join();\n        }\n    } else {\n        handle.take();\n    }\n    finished\n}\n\n'''
    if "fn wait_child_bounded(" not in text:
        anchor = "fn reserve_inbound_bytes(\n"
        if anchor not in text:
            raise RuntimeError("helper insertion anchor missing")
        text = text.replace(anchor, helpers + anchor, 1)

    return text


def apply() -> None:
    ADAPTER.write_text(patch_adapter(ADAPTER.read_text(encoding="utf-8")), encoding="utf-8")
    LEGACY_TEST.write_text(LEGACY_TEST_SOURCE, encoding="utf-8")
    LIFECYCLE_TEST.write_text(LIFECYCLE_TEST_SOURCE, encoding="utf-8")
    PEER.write_text(PEER_SOURCE, encoding="utf-8")


def check() -> None:
    adapter = ADAPTER.read_text(encoding="utf-8")
    missing = [marker for marker in MARKERS if marker not in adapter]
    if missing:
        raise RuntimeError(f"W02-04 markers missing: {missing}")
    forbidden = ("self.child.wait()", "reader.join()", "writer.join()")
    stale = [needle for needle in forbidden if needle in adapter]
    if stale:
        raise RuntimeError(f"unbounded lifecycle calls remain: {stale}")
    if not all(path.is_file() for path in (LEGACY_TEST, LIFECYCLE_TEST, PEER)):
        raise RuntimeError("W02-04 lifecycle test fixtures missing")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.apply:
        apply()
    if args.check or args.apply:
        check()
    else:
        parser.error("one of --apply/--check is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
