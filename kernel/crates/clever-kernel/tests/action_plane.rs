use clever_contracts::{
    ActionIntent, ActionReceiptStatus, ContractVersion, DataClassification, Payload,
    PolicyDecision, PolicyDecisionKind, PrincipalRef, RiskClass, RuntimeHealth,
    RuntimeHealthStatus, SideEffectClass,
};
use clever_kernel::{
    actions::{ActionStore, ReceiptUpdate},
    audit::AuditLog,
    lifecycle::RuntimeHealthTracker,
};
use prost_types::Timestamp;

fn version() -> Option<ContractVersion> {
    Some(ContractVersion { major: 1, minor: 0 })
}

fn timestamp(seconds: i64) -> Option<Timestamp> {
    Some(Timestamp { seconds, nanos: 0 })
}

fn principal() -> Option<PrincipalRef> {
    Some(PrincipalRef {
        user_id: "user_demo".into(),
        device_id: "device_demo".into(),
        channel_id: "desktop".into(),
        tenant_id: String::new(),
    })
}

fn allow_policy() -> PolicyDecision {
    PolicyDecision {
        contract_version: version(),
        decision_id: "pol_allow".into(),
        evaluation_id: "eval_allow".into(),
        decision: PolicyDecisionKind::Allow as i32,
        risk_class: RiskClass::R2 as i32,
        granted_scopes: vec!["filesystem.write".into()],
        reason_codes: vec!["PREAUTHORIZED_TEST".into()],
        user_confirmation_required: false,
        expires_at: None,
        audit_ref: "audit_policy".into(),
    }
}

fn action(action_id: &str, key: &str) -> ActionIntent {
    ActionIntent {
        contract_version: version(),
        action_id: action_id.into(),
        idempotency_key: key.into(),
        principal: principal(),
        session_id: "ses_demo".into(),
        goal_id: "goal_demo".into(),
        capability_id: "computer.file.write".into(),
        operation: "write".into(),
        side_effect_class: SideEffectClass::ExternalMutation as i32,
        policy_decision_id: "pol_allow".into(),
        payload: Some(Payload {
            schema_uri: "clever://actions/file-write/v1".into(),
            content_type: "application/json".into(),
            data: b"{}".to_vec(),
        }),
        requested_at: timestamp(1),
    }
}

#[test]
fn exact_replay_is_duplicate_without_second_action() {
    let mut store = ActionStore::default();
    let mut audit = AuditLog::default();
    let intent = action("act_1", "idem_1");
    store
        .accept(intent.clone(), &allow_policy(), &mut audit)
        .expect("first acceptance");
    let duplicate = store
        .accept(intent, &allow_policy(), &mut audit)
        .expect("exact replay should be safe");
    assert_eq!(duplicate.status, ActionReceiptStatus::Duplicate as i32);
    assert_eq!(store.len(), 1);
    assert!(audit.verify().is_ok());
}

#[test]
fn same_idempotency_key_with_different_action_is_conflict() {
    let mut store = ActionStore::default();
    let mut audit = AuditLog::default();
    store
        .accept(action("act_1", "idem_shared"), &allow_policy(), &mut audit)
        .expect("first acceptance");
    assert!(store
        .accept(action("act_2", "idem_shared"), &allow_policy(), &mut audit)
        .is_err());
    assert_eq!(store.len(), 1);
}

#[test]
fn receipt_state_machine_rejects_invalid_transition_then_accepts_valid_flow() {
    let mut store = ActionStore::default();
    let mut audit = AuditLog::default();
    store
        .accept(action("act_1", "idem_1"), &allow_policy(), &mut audit)
        .expect("accept");
    assert!(store
        .transition(
            "act_1",
            ReceiptUpdate {
                status: ActionReceiptStatus::Succeeded,
                completed_at: timestamp(2),
                ..ReceiptUpdate::default()
            },
            &mut audit,
        )
        .is_err());
    store
        .transition(
            "act_1",
            ReceiptUpdate {
                status: ActionReceiptStatus::Running,
                ..ReceiptUpdate::default()
            },
            &mut audit,
        )
        .expect("accepted -> running");
    let done = store
        .transition(
            "act_1",
            ReceiptUpdate {
                status: ActionReceiptStatus::Succeeded,
                completed_at: timestamp(3),
                result: Some(Payload {
                    schema_uri: "clever://actions/result/v1".into(),
                    content_type: "application/json".into(),
                    data: b"{\"ok\":true}".to_vec(),
                }),
                ..ReceiptUpdate::default()
            },
            &mut audit,
        )
        .expect("running -> succeeded");
    assert_eq!(done.status, ActionReceiptStatus::Succeeded as i32);
    assert!(audit.verify().is_ok());
}

#[test]
fn deny_policy_cannot_enter_action_store() {
    let mut store = ActionStore::default();
    let mut audit = AuditLog::default();
    let mut denied = allow_policy();
    denied.decision = PolicyDecisionKind::Deny as i32;
    denied.risk_class = RiskClass::R4 as i32;
    assert!(store
        .accept(action("act_1", "idem_1"), &denied, &mut audit)
        .is_err());
    assert!(store.is_empty());
}

#[test]
fn false_green_runtime_health_is_rejected() {
    let mut tracker = RuntimeHealthTracker::default();
    let mut audit = AuditLog::default();
    let false_green = RuntimeHealth {
        contract_version: version(),
        runtime_id: "openjarvis-cognition".into(),
        status: RuntimeHealthStatus::Ready as i32,
        degradation_reasons: Vec::new(),
        observed_at: timestamp(1),
        dropped_event_count: 1,
        failed_action_count: 0,
        recovery_hint: String::new(),
    };
    assert!(tracker.observe(false_green, &mut audit).is_err());

    tracker
        .observe(
            RuntimeHealth {
                contract_version: version(),
                runtime_id: "openjarvis-cognition".into(),
                status: RuntimeHealthStatus::Starting as i32,
                degradation_reasons: Vec::new(),
                observed_at: timestamp(2),
                dropped_event_count: 0,
                failed_action_count: 0,
                recovery_hint: String::new(),
            },
            &mut audit,
        )
        .expect("starting");
    tracker
        .observe(
            RuntimeHealth {
                contract_version: version(),
                runtime_id: "openjarvis-cognition".into(),
                status: RuntimeHealthStatus::Ready as i32,
                degradation_reasons: Vec::new(),
                observed_at: timestamp(3),
                dropped_event_count: 0,
                failed_action_count: 0,
                recovery_hint: String::new(),
            },
            &mut audit,
        )
        .expect("ready");
    assert!(tracker.is_ready("openjarvis-cognition"));
    assert!(audit.verify().is_ok());
}

#[test]
fn classification_is_still_explicit_on_actions_context() {
    assert_eq!(DataClassification::Sensitive as i32, 3);
}
