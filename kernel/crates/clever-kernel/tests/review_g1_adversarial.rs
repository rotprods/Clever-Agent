use clever_kernel::adapter::{
    AdapterCleanupCommand, AdapterCommand, AdapterIdentity, AdapterSupervisor,
    AdapterSupervisorError, SupervisorPolicy,
};
use std::{env, path::PathBuf, time::Duration};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .expect("repository root")
        .to_path_buf()
}

fn python() -> String {
    env::var("CLEVER_TEST_PYTHON")
        .expect("MANDATORY: CLEVER_TEST_PYTHON is required for G1 review")
}

fn identity() -> AdapterIdentity {
    AdapterIdentity::new(
        "fake.adapter",
        "fake-runtime",
        "https://example.invalid/fake",
        "fake-commit",
    )
}

fn stopping_peer() -> AdapterCommand {
    let mut command = AdapterCommand::new(python());
    command.args = vec![
        root()
            .join("kernel/crates/clever-kernel/tests/fixtures/lifecycle_peer.py")
            .display()
            .to_string(),
        "stopping-hang".to_owned(),
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

fn policy() -> SupervisorPolicy {
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
fn documents_cleanup_failure_observability_gap() {
    let false_program = ["/usr/bin/false", "/bin/false"]
        .into_iter()
        .find(|path| std::path::Path::new(path).exists())
        .expect("system false executable");
    let mut command = stopping_peer();
    command.cleanup = Some(AdapterCleanupCommand::new(false_program));
    let supervisor =
        AdapterSupervisor::start(command, identity(), policy()).expect("peer handshake");
    let result = supervisor.shutdown("review cleanup failure");
    // Current API collapses cleanup failure into the primary shutdown timeout.
    // This test intentionally characterizes the limitation so the review cannot
    // claim that external cleanup success is verified.
    assert!(matches!(
        result,
        Err(AdapterSupervisorError::Timeout("shutdown exit"))
    ));
}
