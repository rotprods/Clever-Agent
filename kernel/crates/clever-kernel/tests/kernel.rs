use std::collections::HashMap;

use clever_contracts::{
    CapabilityAvailability, CapabilityDescriptor, ContractVersion, DataClassification,
    EventEnvelope, LifecycleMode, Payload, PermissionRequirement, PolicyDecisionKind,
    PolicyEvaluationRequest, PrincipalRef, RiskClass, RuntimeOwner,
};
use clever_kernel::{
    capabilities::CapabilityRegistry,
    events::EventRouter,
    policy::{DenyByDefaultPolicyBroker, PolicyBroker},
};

fn version(major: u32) -> Option<ContractVersion> {
    Some(ContractVersion { major, minor: 0 })
}

fn principal() -> Option<PrincipalRef> {
    Some(PrincipalRef {
        user_id: "user_demo".into(),
        device_id: "device_demo".into(),
        channel_id: "desktop".into(),
        tenant_id: String::new(),
    })
}

fn event(message_id: &str) -> EventEnvelope {
    EventEnvelope {
        contract_version: version(1),
        message_id: message_id.into(),
        correlation_id: "corr_demo".into(),
        causation_id: "root_demo".into(),
        occurred_at: Some(prost_types::Timestamp {
            seconds: 1,
            nanos: 0,
        }),
        producer: Some(RuntimeOwner {
            runtime_id: "clicky-macos".into(),
            adapter_id: "clicky".into(),
            device_id: "device_demo".into(),
            process_id: String::new(),
        }),
        principal: principal(),
        session_id: "ses_demo".into(),
        goal_id: "goal_demo".into(),
        classification: DataClassification::Sensitive as i32,
        event_type: "screen.observed".into(),
        payload: Some(Payload {
            schema_uri: "clever://screen/v1".into(),
            content_type: "application/json".into(),
            data: b"{}".to_vec(),
        }),
        provenance: Vec::new(),
        evidence: Vec::new(),
    }
}

fn capability() -> CapabilityDescriptor {
    CapabilityDescriptor {
        contract_version: version(1),
        capability_id: "voice.ptt.transcribe".into(),
        family: "speech_audio".into(),
        name: "Push-to-talk transcription".into(),
        owner: Some(RuntimeOwner {
            runtime_id: "clicky-macos".into(),
            adapter_id: "clicky".into(),
            device_id: "device_demo".into(),
            process_id: String::new(),
        }),
        implementation_version: "upstream-pinned".into(),
        interface_contract: "clever.v1.speech.transcribe".into(),
        interface_version: "1.0".into(),
        lifecycle_mode: LifecycleMode::Device as i32,
        permissions: vec![PermissionRequirement {
            permission: "microphone".into(),
            scope: "device:device_demo".into(),
            mandatory: true,
        }],
        state_effects: Vec::new(),
        side_effects: Vec::new(),
        platform_constraints: Vec::new(),
        rollback_supported: false,
        provenance: Vec::new(),
        evidence: Vec::new(),
        extension_metadata: HashMap::new(),
    }
}

#[test]
fn event_router_rejects_unknown_major_and_duplicate_ids() {
    let mut router = EventRouter::default();
    let mut unsupported = event("evt_bad");
    unsupported.contract_version = version(2);
    assert!(router.route(unsupported).is_err());

    router
        .route(event("evt_one"))
        .expect("first event should route");
    assert!(router.route(event("evt_one")).is_err());
    assert_eq!(router.len(), 1);
}

#[test]
fn capability_registry_requires_typed_security_fields_and_rejects_reserved_metadata() {
    let mut registry = CapabilityRegistry::default();
    registry
        .register(capability())
        .expect("valid capability should register");
    registry
        .set_availability("voice.ptt.transcribe", CapabilityAvailability::Available)
        .expect("availability should update");
    assert_eq!(registry.len(), 1);
    assert_eq!(
        registry
            .get("voice.ptt.transcribe")
            .expect("capability exists")
            .availability,
        CapabilityAvailability::Available
    );

    let mut malicious = capability();
    malicious.capability_id = "malicious".into();
    malicious
        .extension_metadata
        .insert("permission_override".into(), "root".into());
    assert!(registry.register(malicious).is_err());
}

#[test]
fn deny_by_default_policy_never_self_authorizes() {
    let broker = DenyByDefaultPolicyBroker;
    let request = PolicyEvaluationRequest {
        contract_version: version(1),
        evaluation_id: "eval_demo".into(),
        principal: principal(),
        capability_id: "computer.file.write".into(),
        operation: "write".into(),
        requested_permissions: vec!["filesystem.write".into()],
        data_classification: DataClassification::Sensitive as i32,
        automation_grant_id: String::new(),
    };
    let decision = broker
        .evaluate(&request)
        .expect("request should evaluate safely");
    assert_eq!(decision.decision, PolicyDecisionKind::Deny as i32);
    assert_eq!(decision.risk_class, RiskClass::R4 as i32);
    assert!(decision.granted_scopes.is_empty());
}
