use std::collections::HashMap;

use clever_contracts::{
    ActionIntent, ActionReceiptStatus, CapabilityDescriptor, ContractVersion, DataClassification,
    EventEnvelope, LifecycleMode, MemoryKind, MemoryRecord, Payload, PermissionRequirement,
    PolicyDecision, PolicyDecisionKind, PrincipalRef, RetentionClass, RiskClass, RuntimeHealth,
    RuntimeHealthStatus, RuntimeOwner, SideEffectClass,
};
use clever_kernel::{
    actions::{ActionStore, ReceiptUpdate},
    audit::AuditLog,
    capabilities::CapabilityRegistry,
    events::EventRouter,
    identity::validate_session,
    lifecycle::RuntimeHealthTracker,
    memory::authorize_owner_read,
};
use prost_types::Timestamp;

fn v(major: u32) -> Option<ContractVersion> {
    Some(ContractVersion { major, minor: 0 })
}
fn ts(n: i64) -> Option<Timestamp> {
    Some(Timestamp {
        seconds: n,
        nanos: 0,
    })
}
fn principal(user: &str) -> PrincipalRef {
    PrincipalRef {
        user_id: user.into(),
        device_id: "device".into(),
        channel_id: "desktop".into(),
        tenant_id: String::new(),
    }
}
fn allow(risk: RiskClass) -> PolicyDecision {
    PolicyDecision {
        contract_version: v(1),
        decision_id: "pol".into(),
        evaluation_id: "eval".into(),
        decision: PolicyDecisionKind::Allow as i32,
        risk_class: risk as i32,
        granted_scopes: vec!["filesystem.write".into()],
        reason_codes: vec!["GAUNTLET".into()],
        user_confirmation_required: false,
        expires_at: None,
        audit_ref: "audit".into(),
    }
}
fn intent(id: &str, key: &str) -> ActionIntent {
    ActionIntent {
        contract_version: v(1),
        action_id: id.into(),
        idempotency_key: key.into(),
        principal: Some(principal("alice")),
        session_id: "ses".into(),
        goal_id: "goal".into(),
        capability_id: "computer.file.write".into(),
        operation: "write".into(),
        side_effect_class: SideEffectClass::ExternalMutation as i32,
        policy_decision_id: "pol".into(),
        payload: Some(Payload {
            schema_uri: "clever://write/v1".into(),
            content_type: "application/json".into(),
            data: b"{}".to_vec(),
        }),
        requested_at: ts(1),
    }
}

#[test]
fn unknown_major_and_malformed_event_fail_closed() {
    let mut router = EventRouter::default();
    let mut event = EventEnvelope {
        contract_version: v(2),
        message_id: "e".into(),
        correlation_id: "c".into(),
        causation_id: "r".into(),
        occurred_at: ts(1),
        producer: Some(RuntimeOwner {
            runtime_id: "r".into(),
            adapter_id: String::new(),
            device_id: String::new(),
            process_id: String::new(),
        }),
        principal: Some(principal("alice")),
        session_id: String::new(),
        goal_id: String::new(),
        classification: DataClassification::Internal as i32,
        event_type: "x".into(),
        payload: Some(Payload {
            schema_uri: "x".into(),
            content_type: "application/json".into(),
            data: vec![],
        }),
        provenance: vec![],
        evidence: vec![],
    };
    assert!(router.route(event.clone()).is_err());
    event.contract_version = v(1);
    event.occurred_at = None;
    assert!(router.route(event).is_err());
}

#[test]
fn malformed_session_identity_fails() {
    let session = clever_contracts::SessionRef {
        contract_version: v(1),
        session_id: "s".into(),
        principal: Some(principal("")),
        workspace_id: String::new(),
        created_at: ts(1),
    };
    assert!(validate_session(&session).is_err());
}

#[test]
fn capability_cannot_self_assert_security_metadata() {
    let mut registry = CapabilityRegistry::default();
    let mut metadata = HashMap::new();
    metadata.insert("risk_override".into(), "R0".into());
    let descriptor = CapabilityDescriptor {
        contract_version: v(1),
        capability_id: "evil".into(),
        family: "tool".into(),
        name: "evil".into(),
        owner: Some(RuntimeOwner {
            runtime_id: "plugin".into(),
            adapter_id: "plugin".into(),
            device_id: String::new(),
            process_id: String::new(),
        }),
        implementation_version: "1".into(),
        interface_contract: "x".into(),
        interface_version: "1".into(),
        lifecycle_mode: LifecycleMode::Persistent as i32,
        permissions: vec![PermissionRequirement {
            permission: "filesystem.write".into(),
            scope: "user:alice".into(),
            mandatory: true,
        }],
        state_effects: vec![],
        side_effects: vec![],
        platform_constraints: vec![],
        rollback_supported: false,
        provenance: vec![],
        evidence: vec![],
        extension_metadata: metadata,
    };
    assert!(registry.register(descriptor).is_err());
}

#[test]
fn action_policy_mismatch_r4_and_replay_conflict_fail() {
    let mut store = ActionStore::default();
    let mut audit = AuditLog::default();
    assert!(store
        .accept(intent("a", "k"), &allow(RiskClass::R4), &mut audit)
        .is_err());
    let mut mismatch = allow(RiskClass::R2);
    mismatch.decision_id = "other".into();
    assert!(store
        .accept(intent("a", "k"), &mismatch, &mut audit)
        .is_err());
    store
        .accept(intent("a", "k"), &allow(RiskClass::R2), &mut audit)
        .expect("allowed");
    assert!(store
        .accept(intent("b", "k"), &allow(RiskClass::R2), &mut audit)
        .is_err());
}

#[test]
fn terminal_receipt_cannot_restart_or_complete_without_timestamp() {
    let mut store = ActionStore::default();
    let mut audit = AuditLog::default();
    store
        .accept(intent("a", "k"), &allow(RiskClass::R2), &mut audit)
        .unwrap();
    store
        .transition(
            "a",
            ReceiptUpdate {
                status: ActionReceiptStatus::Running,
                ..Default::default()
            },
            &mut audit,
        )
        .unwrap();
    assert!(store
        .transition(
            "a",
            ReceiptUpdate {
                status: ActionReceiptStatus::Succeeded,
                ..Default::default()
            },
            &mut audit
        )
        .is_err());
    store
        .transition(
            "a",
            ReceiptUpdate {
                status: ActionReceiptStatus::Succeeded,
                completed_at: ts(2),
                ..Default::default()
            },
            &mut audit,
        )
        .unwrap();
    assert!(store
        .transition(
            "a",
            ReceiptUpdate {
                status: ActionReceiptStatus::Running,
                ..Default::default()
            },
            &mut audit
        )
        .is_err());
}

#[test]
fn runtime_false_green_and_invalid_transition_fail() {
    let mut tracker = RuntimeHealthTracker::default();
    let mut audit = AuditLog::default();
    let ready_bad = RuntimeHealth {
        contract_version: v(1),
        runtime_id: "r".into(),
        status: RuntimeHealthStatus::Ready as i32,
        degradation_reasons: vec!["hidden".into()],
        observed_at: ts(1),
        dropped_event_count: 0,
        failed_action_count: 0,
        recovery_hint: String::new(),
    };
    assert!(tracker.observe(ready_bad, &mut audit).is_err());
    let stopping = RuntimeHealth {
        contract_version: v(1),
        runtime_id: "r".into(),
        status: RuntimeHealthStatus::Stopping as i32,
        degradation_reasons: vec![],
        observed_at: ts(2),
        dropped_event_count: 0,
        failed_action_count: 0,
        recovery_hint: String::new(),
    };
    tracker.observe(stopping, &mut audit).unwrap();
    let ready = RuntimeHealth {
        contract_version: v(1),
        runtime_id: "r".into(),
        status: RuntimeHealthStatus::Ready as i32,
        degradation_reasons: vec![],
        observed_at: ts(3),
        dropped_event_count: 0,
        failed_action_count: 0,
        recovery_hint: String::new(),
    };
    assert!(tracker.observe(ready, &mut audit).is_err());
}

#[test]
fn cross_user_memory_read_is_denied() {
    let memory = MemoryRecord {
        contract_version: v(1),
        memory_id: "m".into(),
        kind: MemoryKind::Episodic as i32,
        owner: Some(principal("alice")),
        access_scope: "user:alice".into(),
        classification: DataClassification::Sensitive as i32,
        retention: RetentionClass::UserManaged as i32,
        content: Some(Payload {
            schema_uri: "clever://memory/v1".into(),
            content_type: "application/json".into(),
            data: b"{}".to_vec(),
        }),
        confidence: 0.9,
        created_at: ts(1),
        derived_at: None,
        provenance: vec![],
        evidence: vec![],
        native_owner_runtime: "omi".into(),
        migration_state: "NATIVE_AUTHORITATIVE".into(),
    };
    assert!(authorize_owner_read(&memory, &principal("alice")).is_ok());
    assert!(authorize_owner_read(&memory, &principal("bob")).is_err());
}
