from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "kernel/crates/clever-kernel/src/adapter.rs"
CAPABILITIES = ROOT / "kernel/crates/clever-kernel/src/capabilities.rs"
TEST = ROOT / "kernel/crates/clever-kernel/tests/control_regressions.rs"
PEER = ROOT / "kernel/crates/clever-kernel/tests/fixtures/control_peer.py"

MARKERS = (
    "pub fn register_batch(",
    "fn exchange_control(",
    "registry.register_batch(descriptors)",
    "READY contradicts degradation or failure counters",
)

CONTROL_PEER = r'''"""Controlled adversarial peer for W02-05. It does not load an LLM."""
from __future__ import annotations
import sys
import time
import fake_adapter_sidecar as wire


def main() -> int:
    mode = sys.argv[1]
    hello = wire.hello()
    if mode == "peer-limit":
        hello.hello.max_frame_bytes = 512
    wire.write_frame(hello)
    ack = wire.read_frame()
    if ack is None or ack.WhichOneof("body") != "hello_ack" or not ack.hello_ack.accepted:
        return 64
    count = 0
    while True:
        request = wire.read_frame()
        if request is None:
            return 0
        count += 1
        kind = request.WhichOneof("body")
        stopping = kind == "shutdown"
        status = wire.runtime_pb2.RUNTIME_HEALTH_STATUS_STOPPING if stopping else wire.runtime_pb2.RUNTIME_HEALTH_STATUS_READY
        health = wire.health(status)
        if mode == "late" and count == 1:
            time.sleep(0.3)
        if mode == "unspecified":
            health.status = 0
        if mode == "false-green":
            health.dropped_event_count = 1
        if mode == "wrong-runtime":
            health.runtime_id = "other-principal-runtime"
        if mode == "peer-limit":
            health.status = wire.runtime_pb2.RUNTIME_HEALTH_STATUS_DEGRADED
            health.degradation_reasons.append("x" * 2048)
        correlation = request.frame_id
        if mode == "mismatch" or (mode == "mismatch-once" and count == 1):
            correlation = "unrelated-request"
        response = wire.frame(f"reply:{request.frame_id}", "health", health, correlation_id=correlation)
        if mode == "no-body":
            response.ClearField("health")
        wire.write_frame(response)
        if stopping:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

CONTROL_TEST = r'''use clever_contracts::{
    CapabilityAvailability, NativeRegistryEntry, RegistryPrimitive, RegistrySnapshot,
};
use clever_kernel::{
    adapter::{
        bridge_registry_snapshot, AdapterCommand, AdapterIdentity, AdapterSupervisor,
        SupervisorPolicy,
    },
    capabilities::CapabilityRegistry,
};
use std::{env, path::PathBuf, thread, time::Duration};

fn start(mode: &str) -> AdapterSupervisor {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .expect("repository root")
        .to_path_buf();
    let python = env::var("CLEVER_TEST_PYTHON")
        .expect("MANDATORY: set CLEVER_TEST_PYTHON; never skip control regressions");
    let mut command = AdapterCommand::new(python);
    command.args = vec![
        root.join("kernel/crates/clever-kernel/tests/fixtures/control_peer.py")
            .display()
            .to_string(),
        mode.to_owned(),
    ];
    command.env.insert(
        "PYTHONPATH".into(),
        root.join("contracts/sdk/python/gen").display().to_string(),
    );
    let policy = SupervisorPolicy {
        handshake_timeout: Duration::from_secs(3),
        request_timeout: Duration::from_millis(120),
        ..SupervisorPolicy::default()
    };
    AdapterSupervisor::start(
        command,
        AdapterIdentity::new(
            "fake.adapter",
            "fake-runtime",
            "https://example.invalid/fake",
            "fake-commit",
        ),
        policy,
    )
    .expect("controlled peer handshake")
}

fn entry(key: &str) -> NativeRegistryEntry {
    NativeRegistryEntry {
        primitive: RegistryPrimitive::Engine as i32,
        key: key.into(),
        implementation: format!("fake.{key}"),
        ..NativeRegistryEntry::default()
    }
}

fn bridge(
    entries: Vec<NativeRegistryEntry>,
    registry: &mut CapabilityRegistry,
) -> Result<Vec<String>, String> {
    bridge_registry_snapshot(
        &RegistrySnapshot {
            runtime_id: "fake-runtime".into(),
            entries,
            ..RegistrySnapshot::default()
        },
        registry,
        "fake-runtime",
        "fake.adapter",
        "fake",
        "pin",
    )
    .map_err(|error| error.to_string())
}

#[test]
fn unrelated_health_is_rejected() {
    let mut peer = start("mismatch");
    assert!(peer.request_health().is_err());
    assert!(peer.is_poisoned());
}

#[test]
fn unrelated_cancel_is_rejected() {
    let mut peer = start("mismatch");
    assert!(peer.cancel("not-running", "test").is_err());
    assert!(peer.is_poisoned());
}

#[test]
fn unrelated_shutdown_is_rejected() {
    let peer = start("mismatch");
    assert!(peer.shutdown("test").is_err());
}

#[test]
fn unspecified_health_is_rejected() {
    let mut peer = start("unspecified");
    assert!(peer.request_health().is_err());
    assert!(peer.is_poisoned());
}

#[test]
fn false_green_health_is_rejected() {
    let mut peer = start("false-green");
    assert!(peer.request_health().is_err());
    assert!(peer.is_poisoned());
}

#[test]
fn peer_frame_limit_is_enforced() {
    let mut peer = start("peer-limit");
    assert!(peer.request_health().is_err());
    assert!(peer.is_poisoned());
}

#[test]
fn timeout_prevents_stale_connection_reuse() {
    let mut peer = start("late");
    assert!(peer.request_health().is_err());
    assert!(peer.is_poisoned());
    thread::sleep(Duration::from_millis(450));
    assert!(peer.request_health().is_err());
}

#[test]
fn protocol_failure_prevents_reuse() {
    let mut peer = start("mismatch-once");
    assert!(peer.request_health().is_err());
    assert!(peer.is_poisoned());
    assert!(peer.request_health().is_err());
}

#[test]
fn malformed_body_is_rejected() {
    let mut peer = start("no-body");
    assert!(peer.request_health().is_err());
    assert!(peer.is_poisoned());
}

#[test]
fn wrong_runtime_is_rejected() {
    let mut peer = start("wrong-runtime");
    assert!(peer.request_health().is_err());
    assert!(peer.is_poisoned());
}

#[test]
fn registry_invalid_tail_is_atomic() {
    let mut registry = CapabilityRegistry::default();
    let mut invalid = entry("bad");
    invalid.primitive = 999;
    assert!(bridge(vec![entry("new"), invalid], &mut registry).is_err());
    assert!(registry.is_empty());
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
    bridge(vec![entry("old")], &mut registry).expect("initial registry");
    let mut conflict = entry("old");
    conflict.implementation = "changed.Owner".into();
    assert!(bridge(vec![entry("new"), conflict], &mut registry).is_err());
    assert_eq!(registry.len(), 1);
}

#[test]
fn registry_replay_preserves_availability() {
    let mut registry = CapabilityRegistry::default();
    let ids = bridge(vec![entry("old")], &mut registry).expect("initial registry");
    registry
        .set_availability(&ids[0], CapabilityAvailability::Available)
        .expect("availability");
    let replay = bridge(vec![entry("old"), entry("new")], &mut registry).expect("replay");
    assert_eq!(registry.len(), 2);
    assert_eq!(
        registry.get(&replay[0]).expect("old").availability,
        CapabilityAvailability::Available
    );
    assert_eq!(
        registry.get(&replay[1]).expect("new").availability,
        CapabilityAvailability::Unavailable
    );
}

#[test]
fn valid_control_roundtrip_still_works() {
    let mut peer = start("valid");
    assert!(peer.request_health().is_ok());
    assert!(peer.cancel("none", "control-only").is_ok());
    assert!(peer.shutdown("complete").is_ok());
}
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source anchor, found {count}")
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


def patch_capabilities(text: str) -> str:
    text = replace_once(
        text,
        "use std::collections::BTreeMap;",
        "use std::collections::{BTreeMap, BTreeSet};",
        "BTreeSet import",
    )
    batch = '''    /// Validate the entire batch before mutating the registry. Identical existing\n    /// descriptors are idempotent replays and preserve their availability.\n    pub fn register_batch(\n        &mut self,\n        descriptors: Vec<CapabilityDescriptor>,\n    ) -> Result<Vec<String>, KernelError> {\n        let mut seen = BTreeSet::new();\n        let mut ids = Vec::with_capacity(descriptors.len());\n        for descriptor in &descriptors {\n            validate_descriptor(descriptor)?;\n            if !seen.insert(descriptor.capability_id.clone())\n                || self\n                    .capabilities\n                    .get(&descriptor.capability_id)\n                    .is_some_and(|existing| existing.descriptor != *descriptor)\n            {\n                return Err(KernelError::DuplicateId {\n                    kind: "capability",\n                    id: descriptor.capability_id.clone(),\n                });\n            }\n            ids.push(descriptor.capability_id.clone());\n        }\n        for descriptor in descriptors {\n            self.capabilities\n                .entry(descriptor.capability_id.clone())\n                .or_insert(CapabilityState {\n                    descriptor,\n                    availability: CapabilityAvailability::Unavailable,\n                });\n        }\n        Ok(ids)\n    }\n\n'''
    anchor = "    pub fn set_availability(\n"
    if "pub fn register_batch(" not in text:
        if anchor not in text:
            raise RuntimeError("register_batch insertion anchor missing")
        text = text.replace(anchor, batch + anchor, 1)
    return text


def patch_adapter(text: str) -> str:
    hello_old = "        validate_contract_version(frame.contract_version.as_ref())?;\n        let hello = match frame.body.as_ref() {\n"
    hello_new = "        validate_contract_version(frame.contract_version.as_ref())?;\n        if frame.frame_id.trim().is_empty() || !frame.correlation_id.is_empty() {\n            return Err(AdapterSupervisorError::InvalidHello(\n                \"invalid initial frame identity\".to_owned(),\n            ));\n        }\n        let hello = match frame.body.as_ref() {\n"
    text = replace_once(text, hello_old, hello_new, "hello identity")

    helpers = '''    fn fail_protocol<T>(\n        &mut self,\n        error: AdapterSupervisorError,\n    ) -> Result<T, AdapterSupervisorError> {\n        self.poison_session(error.to_string());\n        Err(error)\n    }\n\n    fn exchange_control(\n        &mut self,\n        body: adapter_frame::Body,\n        stage: &'static str,\n    ) -> Result<AdapterFrame, AdapterSupervisorError> {\n        self.ensure_io_healthy()?;\n        let request = self.next_control_frame(body, self.policy.request_timeout);\n        let request_id = request.frame_id.clone();\n        if let Err(error) = self.write_frame(&request) {\n            return self.fail_protocol(error);\n        }\n        let response = match self.receive_frame(self.policy.request_timeout, stage) {\n            Ok(response) => response,\n            Err(error) => return self.fail_protocol(error),\n        };\n        if response.frame_id.trim().is_empty() || response.correlation_id != request_id {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                \"response frame_id is empty or correlation_id does not match active request\"\n                    .to_owned(),\n            ));\n        }\n        Ok(response)\n    }\n\n'''
    if "fn exchange_control(" not in text:
        anchor = "    pub fn request_registry_snapshot(\n"
        if anchor not in text:
            raise RuntimeError("exchange insertion anchor missing")
        text = text.replace(anchor, helpers + anchor, 1)

    registry_fn = '''    pub fn request_registry_snapshot(\n        &mut self,\n    ) -> Result<RegistrySnapshot, AdapterSupervisorError> {\n        let response = self.exchange_control(\n            adapter_frame::Body::RegistrySnapshotRequest(RegistrySnapshotRequest {}),\n            \"registry snapshot\",\n        )?;\n        match response.body {\n            Some(adapter_frame::Body::RegistrySnapshot(snapshot))\n                if snapshot.runtime_id == self.identity.runtime_id =>\n            {\n                Ok(snapshot)\n            }\n            Some(adapter_frame::Body::RegistrySnapshot(_)) => self.fail_protocol(\n                AdapterSupervisorError::InvalidSnapshot(\"runtime mismatch\".to_owned()),\n            ),\n            _ => self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(\"registry snapshot\")),\n        }\n    }\n\n'''
    text = replace_region(
        text,
        "    pub fn request_registry_snapshot(\n",
        "    pub fn request_health(",
        registry_fn,
        "registry request",
    )

    health_fn = '''    pub fn request_health(&mut self) -> Result<RuntimeHealth, AdapterSupervisorError> {\n        let response = self.exchange_control(\n            adapter_frame::Body::HealthRequest(AdapterHealthRequest {}),\n            \"health request\",\n        )?;\n        self.extract_health(response, \"health request\")\n    }\n\n'''
    text = replace_region(
        text,
        "    pub fn request_health(",
        "    pub fn cancel(",
        health_fn,
        "health request",
    )

    cancel_fn = '''    pub fn cancel(\n        &mut self,\n        target_request_id: impl Into<String>,\n        reason: impl Into<String>,\n    ) -> Result<RuntimeHealth, AdapterSupervisorError> {\n        let response = self.exchange_control(\n            adapter_frame::Body::Cancel(AdapterCancel {\n                target_request_id: target_request_id.into(),\n                reason: reason.into(),\n            }),\n            \"cancel\",\n        )?;\n        self.extract_health(response, \"cancel\")\n    }\n\n'''
    text = replace_region(text, "    pub fn cancel(\n", "    pub fn shutdown(\n", cancel_fn, "cancel")

    shutdown_fn = '''    pub fn shutdown(\n        mut self,\n        reason: impl Into<String>,\n    ) -> Result<RuntimeHealth, AdapterSupervisorError> {\n        let response = self.exchange_control(\n            adapter_frame::Body::Shutdown(AdapterShutdown {\n                reason: reason.into(),\n            }),\n            \"shutdown\",\n        )?;\n        let health = self.extract_health(response, \"shutdown\")?;\n        if health.status != RuntimeHealthStatus::Stopping as i32 {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                \"shutdown did not return STOPPING\".to_owned(),\n            ));\n        }\n        self.child\n            .wait()\n            .map_err(|error| AdapterSupervisorError::Io(error.to_string()))?;\n        Ok(health)\n    }\n\n'''
    text = replace_region(text, "    pub fn shutdown(\n", "    fn validate_hello(\n", shutdown_fn, "shutdown")

    extract_fn = '''    fn extract_health(\n        &mut self,\n        response: AdapterFrame,\n        stage: &'static str,\n    ) -> Result<RuntimeHealth, AdapterSupervisorError> {\n        let health = match response.body {\n            Some(adapter_frame::Body::Health(health)) => health,\n            _ => return self.fail_protocol(AdapterSupervisorError::UnexpectedFrame(stage)),\n        };\n        if let Err(error) = validate_contract_version(health.contract_version.as_ref()) {\n            return self.fail_protocol(error.into());\n        }\n        let status = RuntimeHealthStatus::try_from(health.status);\n        if health.runtime_id != self.identity.runtime_id\n            || status.is_err()\n            || health.status == RuntimeHealthStatus::Unspecified as i32\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                \"invalid health identity/status\".to_owned(),\n            ));\n        }\n        if health.status == RuntimeHealthStatus::Ready as i32\n            && (!health.degradation_reasons.is_empty()\n                || health.dropped_event_count > 0\n                || health.failed_action_count > 0)\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(\n                \"READY contradicts degradation or failure counters\".to_owned(),\n            ));\n        }\n        Ok(health)\n    }\n'''
    pattern = re.compile(r"    fn extract_health\([\s\S]*?\n    \}\n\}\n\nimpl Drop")
    if "READY contradicts degradation or failure counters" not in text:
        match = pattern.search(text)
        if not match:
            raise RuntimeError("extract_health region missing")
        text = text[: match.start()] + extract_fn + "}\n\nimpl Drop" + text[match.end() :]

    bridge_new = '''pub fn bridge_registry_snapshot(\n    snapshot: &RegistrySnapshot,\n    registry: &mut CapabilityRegistry,\n    runtime_id: &str,\n    adapter_id: &str,\n    source_repo: &str,\n    source_commit: &str,\n) -> Result<Vec<String>, AdapterSupervisorError> {\n    if snapshot.runtime_id != runtime_id || runtime_id.trim().is_empty() {\n        return Err(AdapterSupervisorError::InvalidSnapshot(\n            \"snapshot runtime_id does not match expected runtime\".to_owned(),\n        ));\n    }\n    if adapter_id.trim().is_empty()\n        || source_repo.trim().is_empty()\n        || source_commit.trim().is_empty()\n    {\n        return Err(AdapterSupervisorError::InvalidSnapshot(\n            \"bridge provenance/adapter identity is incomplete\".to_owned(),\n        ));\n    }\n    let descriptors = snapshot\n        .entries\n        .iter()\n        .map(|entry| {\n            descriptor_from_registry_entry(\n                entry,\n                runtime_id,\n                adapter_id,\n                source_repo,\n                source_commit,\n            )\n        })\n        .collect::<Result<Vec<_>, _>>()?;\n    registry.register_batch(descriptors).map_err(Into::into)\n}\n\n'''
    text = replace_region(
        text,
        "pub fn bridge_registry_snapshot(\n",
        "fn descriptor_from_registry_entry(\n",
        bridge_new,
        "registry bridge",
    )
    return text


def apply() -> None:
    capabilities = patch_capabilities(CAPABILITIES.read_text(encoding="utf-8"))
    adapter = patch_adapter(ADAPTER.read_text(encoding="utf-8"))
    CAPABILITIES.write_text(capabilities, encoding="utf-8")
    ADAPTER.write_text(adapter, encoding="utf-8")
    TEST.write_text(CONTROL_TEST, encoding="utf-8")
    PEER.write_text(CONTROL_PEER, encoding="utf-8")


def check() -> None:
    adapter = ADAPTER.read_text(encoding="utf-8")
    capabilities = CAPABILITIES.read_text(encoding="utf-8")
    combined = adapter + "\n" + capabilities
    missing = [marker for marker in MARKERS if marker not in combined]
    if missing:
        raise RuntimeError(f"W02-05 markers missing: {missing}")
    if "mpsc::channel()" in adapter:
        raise RuntimeError("W02-03 bounded inbound queue regressed")
    if not TEST.exists() or not PEER.exists():
        raise RuntimeError("W02-05 regression fixtures missing")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("--apply", "--check"))
    args = parser.parse_args()
    if args.mode == "--apply":
        apply()
    check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
