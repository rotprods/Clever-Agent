use std::time::{Duration, SystemTime, UNIX_EPOCH};

use clever_contracts::{
    ContractVersion, InferenceConfig, InferenceInput, InferenceRequest, InferenceRole, PrincipalRef,
};
use clever_kernel::inference_policy::{
    authorize_inference, InferenceAdmissionError, InferenceEgressMode, InferenceRoute,
    RemoteInferenceGrant, SecretHandle,
};

const DESTINATION: &str = "https://api.example.invalid/v1/inference";
const SECRET_CANARY: &str = "sk-canary-W02-07-never-log";
const PROMPT_CANARY: &str = "prompt-canary-W02-07-sensitive";

fn principal(user_id: &str) -> PrincipalRef {
    PrincipalRef {
        user_id: user_id.to_owned(),
        device_id: "device-a".to_owned(),
        channel_id: "desktop".to_owned(),
        tenant_id: "tenant-a".to_owned(),
    }
}

fn request(user_id: &str, session_id: &str, max_output_tokens: u64) -> InferenceRequest {
    InferenceRequest {
        contract_version: Some(ContractVersion { major: 1, minor: 2 }),
        request_id: "req-w02-07".to_owned(),
        attempt_id: "attempt-w02-07".to_owned(),
        principal: Some(principal(user_id)),
        session_id: session_id.to_owned(),
        engine_id: "openjarvis.engine.remote".to_owned(),
        model_id: "provider-model".to_owned(),
        inputs: vec![InferenceInput {
            role: InferenceRole::User as i32,
            content: PROMPT_CANARY.to_owned(),
            name: String::new(),
        }],
        config: Some(InferenceConfig {
            max_output_tokens,
            temperature: Some(0.2),
            top_p: Some(0.95),
            stop_sequences: Vec::new(),
            stream: true,
        }),
        deadline_at: None,
        idempotency_key: "idem-w02-07".to_owned(),
    }
}

fn secret_handle() -> SecretHandle {
    SecretHandle::new(SECRET_CANARY).expect("valid secret handle")
}

fn grant(
    user_id: &str,
    session_id: &str,
    now: SystemTime,
    max_input_tokens: u64,
    max_output_tokens: u64,
    max_total_tokens: u64,
    max_cost_microunits: u64,
) -> RemoteInferenceGrant {
    RemoteInferenceGrant::new(
        "grant-w02-07",
        principal(user_id),
        session_id,
        DESTINATION,
        max_input_tokens,
        max_output_tokens,
        max_total_tokens,
        max_cost_microunits,
        secret_handle(),
        now + Duration::from_secs(60),
    )
    .expect("valid remote inference grant")
}

fn remote_route(
    destination: &str,
    estimated_input_tokens: u64,
    estimated_cost_microunits: u64,
) -> InferenceRoute {
    InferenceRoute::Remote {
        destination: destination.to_owned(),
        secret_handle: secret_handle(),
        estimated_input_tokens,
        estimated_cost_microunits,
    }
}

#[test]
fn remote_inference_is_denied_without_grant() {
    let now = UNIX_EPOCH + Duration::from_secs(10_000);
    let error = authorize_inference(
        &request("user-a", "session-a", 64),
        &remote_route(DESTINATION, 32, 100),
        None,
        now,
    )
    .expect_err("remote egress without a grant must fail closed");
    assert_eq!(error, InferenceAdmissionError::RemoteGrantRequired);
}

#[test]
fn injected_or_ungranted_destination_is_rejected() {
    let now = UNIX_EPOCH + Duration::from_secs(10_000);
    let trusted = grant("user-a", "session-a", now, 128, 128, 256, 1_000);

    let injected = authorize_inference(
        &request("user-a", "session-a", 64),
        &remote_route("https://api.example.invalid@evil.invalid/v1", 32, 100),
        Some(&trusted),
        now,
    )
    .expect_err("userinfo-style authority injection must be rejected");
    assert_eq!(injected, InferenceAdmissionError::InvalidDestination);

    let other_host = authorize_inference(
        &request("user-a", "session-a", 64),
        &remote_route("https://evil.invalid/v1", 32, 100),
        Some(&trusted),
        now,
    )
    .expect_err("grant must bind the exact trusted destination");
    assert_eq!(other_host, InferenceAdmissionError::DestinationNotAllowed);
}

#[test]
fn grant_is_bound_to_exact_principal_and_session() {
    let now = UNIX_EPOCH + Duration::from_secs(10_000);
    let trusted = grant("user-a", "session-a", now, 128, 128, 256, 1_000);

    let principal_error = authorize_inference(
        &request("user-b", "session-a", 64),
        &remote_route(DESTINATION, 32, 100),
        Some(&trusted),
        now,
    )
    .expect_err("another principal must not reuse the grant");
    assert_eq!(
        principal_error,
        InferenceAdmissionError::GrantPrincipalMismatch
    );
    assert!(!principal_error.to_string().contains("user-a"));
    assert!(!principal_error.to_string().contains("user-b"));

    let session_error = authorize_inference(
        &request("user-a", "session-b", 64),
        &remote_route(DESTINATION, 32, 100),
        Some(&trusted),
        now,
    )
    .expect_err("another session must not reuse the grant");
    assert_eq!(session_error, InferenceAdmissionError::GrantSessionMismatch);
    assert!(!session_error.to_string().contains("session-a"));
    assert!(!session_error.to_string().contains("session-b"));
}

#[test]
fn token_and_cost_budgets_are_hard_ceilings() {
    let now = UNIX_EPOCH + Duration::from_secs(10_000);

    let input_limited = grant("user-a", "session-a", now, 31, 128, 256, 1_000);
    assert_eq!(
        authorize_inference(
            &request("user-a", "session-a", 64),
            &remote_route(DESTINATION, 32, 100),
            Some(&input_limited),
            now,
        )
        .expect_err("input budget must be enforced"),
        InferenceAdmissionError::InputTokenBudgetExceeded
    );

    let output_limited = grant("user-a", "session-a", now, 128, 63, 256, 1_000);
    assert_eq!(
        authorize_inference(
            &request("user-a", "session-a", 64),
            &remote_route(DESTINATION, 32, 100),
            Some(&output_limited),
            now,
        )
        .expect_err("output budget must be enforced"),
        InferenceAdmissionError::OutputTokenBudgetExceeded
    );

    let total_limited = grant("user-a", "session-a", now, 128, 128, 95, 1_000);
    assert_eq!(
        authorize_inference(
            &request("user-a", "session-a", 64),
            &remote_route(DESTINATION, 32, 100),
            Some(&total_limited),
            now,
        )
        .expect_err("aggregate token budget must be enforced"),
        InferenceAdmissionError::TotalTokenBudgetExceeded
    );

    let cost_limited = grant("user-a", "session-a", now, 128, 128, 256, 99);
    assert_eq!(
        authorize_inference(
            &request("user-a", "session-a", 64),
            &remote_route(DESTINATION, 32, 100),
            Some(&cost_limited),
            now,
        )
        .expect_err("cost budget must be enforced"),
        InferenceAdmissionError::CostBudgetExceeded
    );
}

#[test]
fn secret_and_prompt_canaries_do_not_appear_in_admission_or_grant_debug() {
    let now = UNIX_EPOCH + Duration::from_secs(10_000);
    let request = request("user-a", "session-a", 64);
    let trusted = grant("user-a", "session-a", now, 128, 128, 256, 1_000);
    let admission = authorize_inference(
        &request,
        &remote_route(DESTINATION, 32, 100),
        Some(&trusted),
        now,
    )
    .expect("bounded trusted route should be admitted");

    let admission_debug = format!("{admission:?}");
    let grant_debug = format!("{trusted:?}");
    let secret_debug = format!("{:?}", secret_handle());
    for rendered in [&admission_debug, &grant_debug, &secret_debug] {
        assert!(!rendered.contains(SECRET_CANARY));
        assert!(!rendered.contains(PROMPT_CANARY));
    }
    assert!(secret_debug.contains("<redacted>"));
    assert!(admission.audit.secret_handle_used);
    assert_eq!(admission.audit.user_id, "user-a");
    assert_eq!(admission.audit.session_id, "session-a");
    assert_eq!(admission.audit.destination.as_deref(), Some(DESTINATION));
}

#[test]
fn expired_grant_fails_closed() {
    let now = UNIX_EPOCH + Duration::from_secs(10_000);
    let expired = RemoteInferenceGrant::new(
        "grant-expired",
        principal("user-a"),
        "session-a",
        DESTINATION,
        128,
        128,
        256,
        1_000,
        secret_handle(),
        now - Duration::from_secs(1),
    )
    .expect("structurally valid expired grant");

    assert_eq!(
        authorize_inference(
            &request("user-a", "session-a", 64),
            &remote_route(DESTINATION, 32, 100),
            Some(&expired),
            now,
        )
        .expect_err("expired grant must fail closed"),
        InferenceAdmissionError::GrantExpired
    );
}

#[test]
fn local_inference_needs_no_remote_grant_and_emits_no_egress_metadata() {
    let now = UNIX_EPOCH + Duration::from_secs(10_000);
    let admission = authorize_inference(
        &request("user-a", "session-a", 64),
        &InferenceRoute::Local,
        None,
        now,
    )
    .expect("local inference admission should not require remote authority");

    assert_eq!(admission.mode, InferenceEgressMode::Local);
    assert_eq!(admission.reservation.cost_microunits, 0);
    assert_eq!(admission.audit.grant_id, None);
    assert_eq!(admission.audit.destination, None);
    assert!(!admission.audit.secret_handle_used);
}
