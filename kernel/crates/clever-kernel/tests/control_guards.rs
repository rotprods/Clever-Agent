use std::{env, path::PathBuf, thread, time::Duration};
use clever_contracts::{CapabilityAvailability, NativeRegistryEntry, RegistryPrimitive, RegistrySnapshot};
use clever_kernel::{adapter::{bridge_registry_snapshot, AdapterCommand, AdapterIdentity, AdapterSupervisor, SupervisorPolicy}, capabilities::CapabilityRegistry};

fn snapshot(entries: Vec<NativeRegistryEntry>) -> RegistrySnapshot {
    RegistrySnapshot { runtime_id: "fake-runtime".to_owned(), entries, ..Default::default() }
}
fn entry(key: &str) -> NativeRegistryEntry {
    NativeRegistryEntry { primitive: RegistryPrimitive::Engine as i32, key: key.to_owned(), implementation: "fake.module.Engine".to_owned(), ..Default::default() }
}
fn bridge(s: &RegistrySnapshot, registry: &mut CapabilityRegistry) -> Result<Vec<String>, clever_kernel::adapter::AdapterSupervisorError> {
    bridge_registry_snapshot(s, registry, "fake-runtime", "fake.adapter", "fake", "fake-commit")
}
fn connect(mode: &str) -> AdapterSupervisor {
    let python = env::var("CLEVER_TEST_PYTHON").expect("CLEVER_TEST_PYTHON is mandatory");
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).ancestors().nth(3).unwrap().to_path_buf();
    let mut command = AdapterCommand::new(python);
    command.args = vec![root.join("kernel/crates/clever-kernel/tests/fixtures/control_guard_peer.py").display().to_string(), mode.to_owned()];
    command.env.insert("PYTHONPATH".to_owned(), root.join("contracts/sdk/python/gen").display().to_string());
    let policy = SupervisorPolicy { handshake_timeout: Duration::from_secs(3), request_timeout: Duration::from_millis(100), max_restarts: 0, ..SupervisorPolicy::default() };
    AdapterSupervisor::start(command, AdapterIdentity::new("fake.adapter", "fake-runtime", "https://example.invalid/fake", "fake-commit"), policy).expect("fixture handshake")
}
#[test]
fn invalid_snapshot_is_atomic() {
    let mut registry = CapabilityRegistry::default();
    let mut invalid = entry("invalid");
    invalid.implementation.clear();
    assert!(bridge(&snapshot(vec![entry("valid"), invalid]), &mut registry).is_err());
    assert!(registry.is_empty(), "failed snapshot leaked a valid prefix");
}
#[test]
fn conflicting_snapshot_is_atomic() {
    let mut registry = CapabilityRegistry::default();
    let seed = snapshot(vec![entry("existing")]);
    let existing = bridge(&seed, &mut registry).unwrap();
    registry.set_availability(&existing[0], CapabilityAvailability::Available).unwrap();
    let mut conflict = entry("existing");
    conflict.implementation = "different.Engine".to_owned();
    assert!(bridge(&snapshot(vec![entry("new"), conflict]), &mut registry).is_err());
    assert_eq!(registry.len(), 1, "conflict leaked a new registration");
    assert_eq!(registry.get(&existing[0]).unwrap().availability, CapabilityAvailability::Available);
}
#[test]
fn duplicate_snapshot_keys_are_rejected_atomically() {
    let mut registry = CapabilityRegistry::default();
    assert!(bridge(&snapshot(vec![entry("same"), entry("same")]), &mut registry).is_err());
    assert!(registry.is_empty());
}
#[test]
fn idempotent_snapshot_preserves_availability() {
    let mut registry = CapabilityRegistry::default();
    let seed = snapshot(vec![entry("existing")]);
    let ids = bridge(&seed, &mut registry).unwrap();
    registry.set_availability(&ids[0], CapabilityAvailability::Available).unwrap();
    assert_eq!(bridge(&seed, &mut registry).unwrap(), ids);
    assert_eq!(registry.len(), 1);
    assert_eq!(registry.get(&ids[0]).unwrap().availability, CapabilityAvailability::Available);
}
#[test]
fn health_requires_request_correlation() { assert!(connect("wrong-correlation").request_health().is_err()); }
#[test]
fn cancel_requires_request_correlation() { assert!(connect("wrong-correlation").cancel("none", "fixture").is_err()); }
#[test]
fn shutdown_requires_request_correlation() { assert!(connect("wrong-correlation").shutdown("fixture").is_err()); }
#[test]
fn unspecified_health_is_not_accepted() { assert!(connect("unspecified").request_health().is_err()); }
#[test]
fn ready_with_loss_is_rejected() { assert!(connect("false-ready").request_health().is_err()); }
#[test]
fn ready_with_degradation_is_rejected() { assert!(connect("ready-with-reason").request_health().is_err()); }
#[test]
fn negotiated_receive_limit_is_enforced() {
    let mut peer = connect("negotiated-limit");
    assert_eq!(peer.negotiated_max_frame_bytes(), 512);
    assert!(peer.request_health().is_err());
}
#[test]
fn empty_response_identity_is_rejected() { assert!(connect("empty-frame-id").request_health().is_err()); }
#[test]
fn timeout_poisons_session_before_late_reply() {
    let mut peer = connect("late-health");
    assert!(peer.request_health().is_err());
    thread::sleep(Duration::from_millis(300));
    assert!(peer.request_health().is_err(), "late response was attributed to a new request");
}
#[test]
fn protocol_error_requires_reconnect() {
    let mut peer = connect("wrong-correlation");
    assert!(peer.request_health().is_err());
    let error = peer.request_health().unwrap_err().to_string();
    assert!(error.contains("unusable"), "failed session was reused: {error}");
}
#[test]
fn valid_control_exchange_remains_compatible() {
    let mut peer = connect("valid");
    assert!(peer.request_health().is_ok());
    assert!(peer.cancel("none", "fixture").is_ok());
    assert!(peer.shutdown("fixture").is_ok());
}
