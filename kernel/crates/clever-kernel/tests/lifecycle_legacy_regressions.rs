use clever_kernel::adapter::{
    AdapterCommand, AdapterIdentity, AdapterSupervisor, AdapterSupervisorError, SupervisorPolicy,
};
use std::{
    env, fs,
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
        root()
            .join("contracts/sdk/python/gen")
            .display()
            .to_string(),
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
    assert!(
        path.exists(),
        "lifecycle peer did not publish descendant pid"
    );
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
    assert!(matches!(
        result,
        Err(AdapterSupervisorError::Timeout("shutdown exit"))
    ));
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
    assert!(
        wait_process_gone(pid),
        "descendant survived supervisor drop: {pid}"
    );
    let _ = fs::remove_file(pid_file);
}
