use clever_contracts::{
    ContractVersion, InferenceConfig, InferenceRequest, InferenceTerminal, InferenceUsage,
    InferenceUsageMeasurement, PrincipalRef,
};
use clever_kernel::inference_security::{
    authorize_inference_egress, validate_terminal_usage, EgressAuthorization,
    ExternalInferenceGrant, InferenceBudget, InferenceReservation, InferenceSecurityError,
    InferenceTarget, SecretHandle,
};

fn principal(user: &str) -> PrincipalRef {
    PrincipalRef {
        user_id: user.to_owned(),
        device_id: "device-a".to_owned(),
        channel_id: "desktop".to_owned(),
        tenant_id: "tenant-a".to_owned(),
    }
}

fn request(user: &str, session_id: &str, max_output_tokens: u64) -> InferenceRequest {
    InferenceRequest {
        contract_version: Some(ContractVersion { major: 1, minor: 2 }),
        request_id: "req-1".to_owned(),
        attempt_id: "attempt-1".to_owned(),
        principal: Some(principal(user)),
        session_id: session_id.to_owned(),
        engine_id: "engine-a".to_owned(),
        model_id: "model-a".to_owned(),
        inputs: Vec::new(),
        config: Some(InferenceConfig {
            max_output_tokens,
            temperature: None,
            top_p: None,
            stop_sequences: Vec::new(),
            stream: true,
        }),
        deadline_at: None,
        idempotency_key: "idem-1".to_owned(),
        response_schema_json: None,
    }
}

fn target(origin: &str) -> InferenceTarget {
    InferenceTarget {
        provider_id: "provider-a".to_owned(),
        origin: origin.to_owned(),
        external: true,
    }
}

fn budget() -> InferenceBudget {
    InferenceBudget {
        max_input_tokens: 1_000,
        max_output_tokens: 500,
        max_total_tokens: 1_500,
        max_cost_microusd: 250_000,
    }
}

fn reservation() -> InferenceReservation {
    InferenceReservation {
        estimated_input_tokens: 400,
        estimated_cost_microusd: 100_000,
    }
}

fn grant(secret: &str) -> ExternalInferenceGrant {
    ExternalInferenceGrant {
        grant_id: "grant-1".to_owned(),
        principal: principal("user-a"),
        session_id: "session-a".to_owned(),
        provider_id: "provider-a".to_owned(),
        origin: "https://api.provider.example".to_owned(),
        credential_handle: SecretHandle::new(secret).expect("secret handle"),
        budget: budget(),
        expires_at_unix_seconds: 2_000,
    }
}

#[test]
fn external_inference_is_deny_by_default_without_grant() {
    let error = authorize_inference_egress(
        &request("user-a", "session-a", 200),
        &target("https://api.provider.example"),
        None,
        &reservation(),
        1_000,
    )
    .expect_err("external inference without grant must fail");
    assert_eq!(error, InferenceSecurityError::ExternalGrantRequired);
}

#[test]
fn canonical_grant_allows_exact_principal_session_destination_and_budget() {
    let grant = grant("vault://provider-a/token");
    let (authorization, audit) = authorize_inference_egress(
        &request("user-a", "session-a", 200),
        &target("https://api.provider.example"),
        Some(&grant),
        &reservation(),
        1_000,
    )
    .expect("exact canonical grant should authorize");

    match authorization {
        EgressAuthorization::External(external) => {
            assert_eq!(external.grant_id, "grant-1");
            assert_eq!(external.provider_id, "provider-a");
            assert_eq!(external.origin, "https://api.provider.example");
            assert_eq!(
                external.credential_handle.expose_to_secret_store(),
                "vault://provider-a/token"
            );
        }
        EgressAuthorization::Local => panic!("external route returned local authorization"),
    }
    assert!(audit.external);
    assert!(audit.credential_handle_present);
    assert_eq!(audit.grant_id.as_deref(), Some("grant-1"));
}

#[test]
fn injected_or_noncanonical_external_origins_are_rejected() {
    let grant = grant("vault://provider-a/token");
    let request = request("user-a", "session-a", 200);

    let injected = target("https://api.provider.example@evil.example");
    assert_eq!(
        authorize_inference_egress(&request, &injected, Some(&grant), &reservation(), 1_000)
            .expect_err("userinfo-style origin injection must fail"),
        InferenceSecurityError::InvalidExternalOrigin
    );

    let path_injected = target("https://api.provider.example/v1?endpoint=https://evil.example");
    assert_eq!(
        authorize_inference_egress(
            &request,
            &path_injected,
            Some(&grant),
            &reservation(),
            1_000,
        )
        .expect_err("request-controlled path/query must not become origin authority"),
        InferenceSecurityError::InvalidExternalOrigin
    );

    let different_origin = target("https://other.provider.example");
    assert_eq!(
        authorize_inference_egress(
            &request,
            &different_origin,
            Some(&grant),
            &reservation(),
            1_000,
        )
        .expect_err("grant must bind exact origin"),
        InferenceSecurityError::OriginMismatch
    );
}

#[test]
fn grant_cannot_cross_principal_or_session_boundary() {
    let grant = grant("vault://provider-a/token");
    assert_eq!(
        authorize_inference_egress(
            &request("user-b", "session-a", 200),
            &target("https://api.provider.example"),
            Some(&grant),
            &reservation(),
            1_000,
        )
        .expect_err("grant must not cross principal"),
        InferenceSecurityError::PrincipalMismatch
    );
    assert_eq!(
        authorize_inference_egress(
            &request("user-a", "session-b", 200),
            &target("https://api.provider.example"),
            Some(&grant),
            &reservation(),
            1_000,
        )
        .expect_err("grant must not cross session"),
        InferenceSecurityError::SessionMismatch
    );
}

#[test]
fn token_and_cost_ceilings_fail_closed() {
    let grant = grant("vault://provider-a/token");
    let external = target("https://api.provider.example");

    assert_eq!(
        authorize_inference_egress(
            &request("user-a", "session-a", 501),
            &external,
            Some(&grant),
            &reservation(),
            1_000,
        )
        .expect_err("output ceiling must fail"),
        InferenceSecurityError::OutputBudgetExceeded
    );

    let too_many_input = InferenceReservation {
        estimated_input_tokens: 1_001,
        estimated_cost_microusd: 100_000,
    };
    assert_eq!(
        authorize_inference_egress(
            &request("user-a", "session-a", 200),
            &external,
            Some(&grant),
            &too_many_input,
            1_000,
        )
        .expect_err("input ceiling must fail"),
        InferenceSecurityError::InputBudgetExceeded
    );

    let too_expensive = InferenceReservation {
        estimated_input_tokens: 400,
        estimated_cost_microusd: 250_001,
    };
    assert_eq!(
        authorize_inference_egress(
            &request("user-a", "session-a", 200),
            &external,
            Some(&grant),
            &too_expensive,
            1_000,
        )
        .expect_err("cost ceiling must fail"),
        InferenceSecurityError::CostBudgetExceeded
    );
}

#[test]
fn secret_canary_is_redacted_from_debug_and_audit() {
    let canary = "CANARY-secret-token-should-never-log";
    let grant = grant(canary);
    let (authorization, audit) = authorize_inference_egress(
        &request("user-a", "session-a", 200),
        &target("https://api.provider.example"),
        Some(&grant),
        &reservation(),
        1_000,
    )
    .expect("grant should authorize");

    let rendered = format!("grant={grant:?} auth={authorization:?} audit={audit:?}");
    assert!(!rendered.contains(canary));
    assert!(rendered.contains("<redacted>"));
}

#[test]
fn expired_grant_is_rejected() {
    let grant = grant("vault://provider-a/token");
    assert_eq!(
        authorize_inference_egress(
            &request("user-a", "session-a", 200),
            &target("https://api.provider.example"),
            Some(&grant),
            &reservation(),
            2_000,
        )
        .expect_err("expired grant must fail"),
        InferenceSecurityError::GrantExpired
    );
}

#[test]
fn local_inference_does_not_require_external_grant_or_secret() {
    let local_target = InferenceTarget {
        provider_id: "local-engine".to_owned(),
        origin: "local://openjarvis".to_owned(),
        external: false,
    };
    let (authorization, audit) = authorize_inference_egress(
        &request("user-a", "session-a", 200),
        &local_target,
        None,
        &reservation(),
        1_000,
    )
    .expect("local route should not require external grant");
    assert_eq!(authorization, EgressAuthorization::Local);
    assert!(!audit.external);
    assert!(!audit.credential_handle_present);
}

#[test]
fn reported_usage_cannot_exceed_granted_token_budget() {
    let terminal = InferenceTerminal {
        contract_version: Some(ContractVersion { major: 1, minor: 2 }),
        request_id: "req-1".to_owned(),
        attempt_id: "attempt-1".to_owned(),
        final_sequence: 1,
        finish_reason: 1,
        usage: Some(InferenceUsage {
            measurement: InferenceUsageMeasurement::Exact as i32,
            input_tokens: Some(400),
            output_tokens: Some(501),
            total_tokens: Some(901),
        }),
    };
    assert_eq!(
        validate_terminal_usage(&terminal, &budget())
            .expect_err("reported over-budget output must fail"),
        InferenceSecurityError::UsageBudgetExceeded
    );
}
