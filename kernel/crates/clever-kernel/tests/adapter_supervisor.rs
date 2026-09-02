use std::{collections::BTreeMap, env, path::PathBuf, time::Duration};

use clever_contracts::{CapabilityAvailability, RuntimeHealthStatus};
use clever_kernel::{
    adapter::{
        bridge_registry_snapshot, AdapterCommand, AdapterIdentity, AdapterSupervisor,
        AdapterSupervisorError, SupervisorPolicy,
    },
    capabilities::CapabilityRegistry,
    error::KernelError,
};

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .expect("repository root")
        .to_path_buf()
}

fn fake_command(mode: &str) -> Option<AdapterCommand> {
    let python = env::var("CLEVER_TEST_PYTHON").ok()?;
    let root = repo_root();
    let script = root.join("kernel/crates/clever-kernel/tests/fixtures/fake_adapter_sidecar.py");
    let generated = root.join("contracts/sdk/python/gen");
    let mut command = AdapterCommand::new(python);
    command.args = vec![script.display().to_string(), mode.to_owned()];
    command
        .env
        .insert("PYTHONPATH".to_owned(), generated.display().to_string());
    Some(command)
}

fn fake_identity() -> AdapterIdentity {
    AdapterIdentity::new(
        "fake.adapter",
        "fake-runtime",
        "https://example.invalid/fake",
        "fake-commit",
    )
}

fn fast_policy() -> SupervisorPolicy {
    SupervisorPolicy {
        handshake_timeout: Duration::from_millis(300),
        request_timeout: Duration::from_millis(500),
        restart_backoff: Duration::from_millis(5),
        ..SupervisorPolicy::default()
    }
}

#[test]
fn rejects_relative_adapter_programs_before_spawn() {
    let command = AdapterCommand::new("python3");
    let error = match AdapterSupervisor::start(command, fake_identity(), fast_policy()) {
        Ok(_) => panic!("relative program unexpectedly accepted"),
        Err(error) => error,
    };
    assert!(matches!(error, AdapterSupervisorError::InvalidCommand(_)));
}

#[test]
fn rejects_unknown_contract_major() {
    let Some(command) = fake_command("unknown-major") else {
        return;
    };
    let error = match AdapterSupervisor::start(command, fake_identity(), fast_policy()) {
        Ok(_) => panic!("unknown major unexpectedly accepted"),
        Err(error) => error,
    };
    assert_eq!(
        error,
        AdapterSupervisorError::Kernel(KernelError::UnsupportedContractMajor(9))
    );
}

#[test]
fn rejects_oversized_and_truncated_frames() {
    let Some(oversized) = fake_command("oversized") else {
        return;
    };
    let error = match AdapterSupervisor::start(oversized, fake_identity(), fast_policy()) {
        Ok(_) => panic!("oversized frame unexpectedly accepted"),
        Err(error) => error,
    };
    assert!(matches!(error, AdapterSupervisorError::FrameTooLarge(_)));

    let Some(partial) = fake_command("partial") else {
        return;
    };
    let error = match AdapterSupervisor::start(partial, fake_identity(), fast_policy()) {
        Ok(_) => panic!("partial frame unexpectedly accepted"),
        Err(error) => error,
    };
    assert_eq!(error, AdapterSupervisorError::TruncatedFrame);
}

#[test]
fn handshake_timeout_is_bounded() {
    let Some(command) = fake_command("silent") else {
        return;
    };
    let mut policy = fast_policy();
    policy.handshake_timeout = Duration::from_millis(50);
    let error = match AdapterSupervisor::start(command, fake_identity(), policy) {
        Ok(_) => panic!("silent adapter unexpectedly connected"),
        Err(error) => error,
    };
    assert_eq!(error, AdapterSupervisorError::Timeout("handshake"));
}

#[test]
fn crash_restart_budget_is_bounded() {
    let Some(command) = fake_command("crash") else {
        return;
    };
    let mut policy = fast_policy();
    policy.max_restarts = 2;
    let error = match AdapterSupervisor::connect_with_restarts(command, fake_identity(), policy) {
        Ok(_) => panic!("crashing adapter unexpectedly connected"),
        Err(error) => error,
    };
    match error {
        AdapterSupervisorError::RestartBudgetExhausted { attempts, .. } => {
            assert_eq!(attempts, 3);
        }
        other => panic!("unexpected restart error: {other}"),
    }
}

#[test]
fn inherited_secrets_are_stripped_and_registry_metadata_cannot_escalate() {
    let Some(command) = fake_command("valid") else {
        return;
    };
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())
        .expect("connect fake adapter");
    assert_eq!(supervisor.negotiated_max_frame_bytes(), 4 * 1024 * 1024);
    assert!(supervisor.negotiated_features().contains("registry-snapshot"));

    let snapshot = supervisor
        .request_registry_snapshot()
        .expect("request fake registry snapshot");
    assert_eq!(snapshot.entries.len(), 1);
    let entry = &snapshot.entries[0];
    assert_eq!(entry.metadata.get("secret_seen").map(String::as_str), Some("false"));
    assert_eq!(entry.metadata.get("policy_override").map(String::as_str), Some("allow"));

    let mut registry = CapabilityRegistry::default();
    let ids = bridge_registry_snapshot(
        &snapshot,
        &mut registry,
        "fake-runtime",
        "fake.adapter",
        "fake",
        "fake-commit",
    )
    .expect("bridge fake snapshot");
    assert_eq!(ids.len(), 1);
    assert_eq!(registry.len(), 1);
    let state = registry.get(&ids[0]).expect("bridged capability");
    assert_eq!(state.availability, CapabilityAvailability::Unavailable);
    assert!(!state.descriptor.extension_metadata.contains_key("policy_override"));
    assert_eq!(
        state
            .descriptor
            .extension_metadata
            .get("secret_seen")
            .map(String::as_str),
        Some("false")
    );

    let again = bridge_registry_snapshot(
        &snapshot,
        &mut registry,
        "fake-runtime",
        "fake.adapter",
        "fake",
        "fake-commit",
    )
    .expect("idempotent bridge");
    assert_eq!(again, ids);
    assert_eq!(registry.len(), 1);

    let health = supervisor.request_health().expect("health response");
    assert_eq!(health.status, RuntimeHealthStatus::Ready as i32);
    let cancelled = supervisor.cancel("none", "test").expect("cancel response");
    assert_eq!(cancelled.status, RuntimeHealthStatus::Ready as i32);
    let stopping = supervisor.shutdown("test complete").expect("shutdown response");
    assert_eq!(stopping.status, RuntimeHealthStatus::Stopping as i32);
}

#[test]
fn real_openjarvis_sidecar_is_supervised_and_bridged_without_promotion() {
    let (Ok(image), Ok(workspace), Ok(docker)) = (
        env::var("CLEVER_OPENJARVIS_IMAGE"),
        env::var("CLEVER_REPO_ROOT"),
        env::var("CLEVER_DOCKER_BIN"),
    ) else {
        return;
    };

    let mount = format!("{workspace}:/clever:ro");
    let mut command = AdapterCommand::new(docker);
    command.env = BTreeMap::from([("HOME".to_owned(), "/tmp".to_owned())]);
    command.args = vec![
        "run".to_owned(),
        "--rm".to_owned(),
        "-i".to_owned(),
        "--network".to_owned(),
        "none".to_owned(),
        "--read-only".to_owned(),
        "--cap-drop".to_owned(),
        "ALL".to_owned(),
        "--security-opt".to_owned(),
        "no-new-privileges".to_owned(),
        "--pids-limit".to_owned(),
        "256".to_owned(),
        "--memory".to_owned(),
        "2g".to_owned(),
        "--cpus".to_owned(),
        "2".to_owned(),
        "--tmpfs".to_owned(),
        "/tmp:rw,noexec,nosuid,size=256m".to_owned(),
        "-e".to_owned(),
        "HOME=/tmp/home".to_owned(),
        "-e".to_owned(),
        "XDG_CONFIG_HOME=/tmp/config".to_owned(),
        "-e".to_owned(),
        "XDG_DATA_HOME=/tmp/data".to_owned(),
        "-e".to_owned(),
        "PYTHONHASHSEED=0".to_owned(),
        "-e".to_owned(),
        "PYTHONPATH=/clever:/clever/contracts/sdk/python/gen:/src/src".to_owned(),
        "-v".to_owned(),
        mount,
        image,
        "exec /src/.venv/bin/python /clever/adapters/openjarvis/sidecar.py".to_owned(),
    ];

    let identity = AdapterIdentity::new(
        "openjarvis.cognition",
        "openjarvis",
        "https://github.com/open-jarvis/OpenJarvis.git",
        "72033b8ec288aa067ce4530ff9d96bf231e9c4e5",
    );
    let policy = SupervisorPolicy {
        handshake_timeout: Duration::from_secs(15),
        request_timeout: Duration::from_secs(8),
        max_restarts: 1,
        ..SupervisorPolicy::default()
    };
    let mut supervisor = AdapterSupervisor::connect_with_restarts(command, identity, policy)
        .expect("supervise real OpenJarvis sidecar");
    let snapshot = supervisor
        .request_registry_snapshot()
        .expect("real OpenJarvis registry snapshot");
    assert_eq!(snapshot.entries.len(), 230);

    let mut registry = CapabilityRegistry::default();
    let ids = bridge_registry_snapshot(
        &snapshot,
        &mut registry,
        "openjarvis",
        "openjarvis.cognition",
        "openjarvis",
        "72033b8ec288aa067ce4530ff9d96bf231e9c4e5",
    )
    .expect("bridge real OpenJarvis registry");
    assert_eq!(ids.len(), 230);
    assert_eq!(registry.len(), 230);
    assert!(ids.iter().all(|id| {
        registry
            .get(id)
            .is_some_and(|state| state.availability == CapabilityAvailability::Unavailable)
    }));

    let health = supervisor.request_health().expect("real OpenJarvis health");
    assert_eq!(health.status, RuntimeHealthStatus::Ready as i32);
    let stopping = supervisor.shutdown("W01 gate complete").expect("real shutdown");
    assert_eq!(stopping.status, RuntimeHealthStatus::Stopping as i32);
}
