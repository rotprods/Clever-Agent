use std::{env, path::PathBuf, thread, time::Duration};
use clever_contracts::{CapabilityAvailability, NativeRegistryEntry, RegistryPrimitive, RegistrySnapshot};
use clever_kernel::{adapter::{bridge_registry_snapshot, AdapterCommand, AdapterIdentity, AdapterSupervisor, SupervisorPolicy}, capabilities::CapabilityRegistry};

fn start(mode: &str) -> AdapterSupervisor {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).ancestors().nth(3).unwrap().to_path_buf();
    let python = env::var("CLEVER_TEST_PYTHON").expect("MANDATORY: set CLEVER_TEST_PYTHON; never skip control regressions");
    let mut command = AdapterCommand::new(python);
    command.args = vec![root.join("kernel/crates/clever-kernel/tests/fixtures/control_peer.py").display().to_string(), mode.to_owned()];
    command.env.insert("PYTHONPATH".into(), root.join("contracts/sdk/python/gen").display().to_string());
    let policy = SupervisorPolicy { handshake_timeout: Duration::from_secs(3), request_timeout: Duration::from_millis(120), ..SupervisorPolicy::default() };
    AdapterSupervisor::start(command, AdapterIdentity::new("fake.adapter", "fake-runtime", "https://example.invalid/fake", "fake-commit"), policy).expect("controlled peer handshake")
}
fn entry(key: &str) -> NativeRegistryEntry {
    NativeRegistryEntry { primitive: RegistryPrimitive::Engine as i32, key: key.into(), implementation: format!("fake.{key}"), ..NativeRegistryEntry::default() }
}
fn bridge(entries: Vec<NativeRegistryEntry>, registry: &mut CapabilityRegistry) -> Result<Vec<String>, String> {
    bridge_registry_snapshot(&RegistrySnapshot { runtime_id: "fake-runtime".into(), entries, ..RegistrySnapshot::default() }, registry, "fake-runtime", "fake.adapter", "fake", "pin").map_err(|e| e.to_string())
}

#[test]
fn unrelated_health_is_rejected() {
    let mut peer = start("mismatch");
    assert!(peer.request_health().is_err(), "assertion: unrelated health cannot satisfy a request");
}
#[test]
fn unrelated_cancel_is_rejected() {
    let mut peer = start("mismatch");
    assert!(peer.cancel("not-running", "test").is_err());
}
#[test]
fn unrelated_shutdown_is_rejected() {
    let peer = start("mismatch");
    assert!(peer.shutdown("test").is_err());
}
#[test]
fn unspecified_health_is_rejected() {
    assert!(start("unspecified").request_health().is_err());
}
#[test]
fn false_green_health_is_rejected() {
    assert!(start("false-green").request_health().is_err());
}
#[test]
fn peer_frame_limit_is_enforced() {
    assert!(start("peer-limit").request_health().is_err());
}
#[test]
fn timeout_prevents_stale_connection_reuse() {
    let mut peer = start("late");
    assert!(peer.request_health().is_err());
    thread::sleep(Duration::from_millis(450));
    assert!(peer.request_health().is_err(), "assertion: late health from expired request must not satisfy another request");
}
#[test]
fn protocol_failure_prevents_reuse() {
    let mut peer = start("mismatch-once");
    assert!(peer.request_health().is_err());
    assert!(peer.request_health().is_err(), "assertion: reconnect is required after protocol ambiguity");
}
#[test]
fn malformed_body_is_rejected() {
    assert!(start("no-body").request_health().is_err());
}
#[test]
fn wrong_runtime_is_rejected() {
    assert!(start("wrong-runtime").request_health().is_err());
}
#[test]
fn registry_invalid_tail_is_atomic() {
    let mut registry = CapabilityRegistry::default();
    let mut invalid = entry("bad");
    invalid.primitive = 999;
    assert!(bridge(vec![entry("new"), invalid], &mut registry).is_err());
    assert!(registry.is_empty(), "assertion: invalid tail must not leave the valid prefix registered");
}
#[test]
fn registry_duplicate_batch_is_rejected() {
    let mut registry = CapabilityRegistry::default();
    assert!(bridge(vec![entry("new"), entry("new")], &mut registry).is_err());
    assert!(registry.is_empty());
}
#[test]
fn registry_existing_conflict_is_atomic() {
    let mut registry = CapabilityRegistry::default();
    bridge(vec![entry("old")], &mut registry).unwrap();
    let mut conflict = entry("old");
    conflict.implementation = "changed.Owner".into();
    assert!(bridge(vec![entry("new"), conflict], &mut registry).is_err());
    assert_eq!(registry.len(), 1, "existing conflict must roll back the new prefix");
}
#[test]
fn registry_replay_preserves_availability() {
    let mut registry = CapabilityRegistry::default();
    let ids = bridge(vec![entry("old")], &mut registry).unwrap();
    registry.set_availability(&ids[0], CapabilityAvailability::Available).unwrap();
    let replay = bridge(vec![entry("old"), entry("new")], &mut registry).unwrap();
    assert_eq!(registry.len(), 2);
    assert_eq!(registry.get(&replay[0]).unwrap().availability, CapabilityAvailability::Available);
    assert_eq!(registry.get(&replay[1]).unwrap().availability, CapabilityAvailability::Unavailable);
}
#[test]
fn valid_control_roundtrip_still_works() {
    let mut peer = start("valid");
    assert!(peer.request_health().is_ok());
    assert!(peer.cancel("none", "control-only").is_ok());
    assert!(peer.shutdown("complete").is_ok());
}
