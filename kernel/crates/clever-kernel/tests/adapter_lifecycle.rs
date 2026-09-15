use clever_kernel::adapter::{
    AdapterCleanupCommand, AdapterCommand, AdapterIdentity, AdapterSupervisor,
    AdapterSupervisorError, SupervisorPolicy,
};
use std::{
    env, fs,
    path::{Path, PathBuf},
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
        root()
            .join("contracts/sdk/python/gen")
            .display()
            .to_string(),
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
    assert!(matches!(
        result,
        Err(AdapterSupervisorError::Timeout("shutdown exit"))
    ));
    assert_eq!(
        fs::read_to_string(&marker).expect("cleanup marker"),
        "cleanup-ran\n"
    );
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
    assert!(matches!(
        result,
        Err(AdapterSupervisorError::Timeout("shutdown exit"))
    ));
    assert!(started.elapsed() < Duration::from_secs(3));
    assert_eq!(
        fs::read_to_string(&marker).expect("cleanup started marker"),
        "cleanup-started\n"
    );
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
