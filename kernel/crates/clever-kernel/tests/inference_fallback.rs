use clever_kernel::inference_fallback::{
    decide_fallback, AttemptReceipt, FailureContext, FailureStage, FallbackCandidate,
    FallbackDecision, FallbackPolicy, FallbackStopReason, InferenceTargetClass,
};

fn local_policy() -> FallbackPolicy {
    FallbackPolicy {
        max_attempts: 3,
        max_cumulative_reserved_cost_microusd: 500,
        max_target_class: InferenceTargetClass::Local,
    }
}

fn receipt(
    attempt_id: &str,
    engine_id: &str,
    model_id: &str,
    emitted_chunks: u64,
    reserved_cost_microusd: u64,
    target_class: InferenceTargetClass,
) -> AttemptReceipt {
    AttemptReceipt {
        attempt_id: attempt_id.to_owned(),
        engine_id: engine_id.to_owned(),
        model_id: model_id.to_owned(),
        emitted_chunks,
        reserved_cost_microusd,
        target_class,
    }
}

fn failure(stage: FailureStage, retryable: bool) -> FailureContext {
    FailureContext { stage, retryable }
}

fn candidate(
    engine_id: &str,
    model_id: &str,
    target_class: InferenceTargetClass,
    reserved_cost_microusd: u64,
) -> FallbackCandidate {
    FallbackCandidate {
        engine_id: engine_id.to_owned(),
        model_id: model_id.to_owned(),
        target_class,
        reserved_cost_microusd,
    }
}

#[test]
fn failure_before_first_token_retries_with_fresh_attempt_and_cumulative_budget() {
    let prior = vec![receipt(
        "req-1:attempt:1",
        "engine-a",
        "model-a",
        0,
        120,
        InferenceTargetClass::Local,
    )];
    let next = candidate("engine-b", "model-b", InferenceTargetClass::Local, 80);

    let decision = decide_fallback(
        "req-1",
        &prior,
        failure(FailureStage::BeforeFirstToken, true),
        &next,
        &local_policy(),
    )
    .expect("valid bounded fallback history");

    assert_eq!(
        decision,
        FallbackDecision::Retry {
            next_attempt_id: "req-1:attempt:2".to_owned(),
            cumulative_reserved_cost_microusd: 200,
        }
    );
}

#[test]
fn failure_after_partial_output_never_retries_or_splices_streams() {
    let prior = vec![receipt(
        "req-2:attempt:1",
        "engine-a",
        "model-a",
        2,
        90,
        InferenceTargetClass::Local,
    )];
    let next = candidate("engine-b", "model-b", InferenceTargetClass::Local, 70);

    let decision = decide_fallback(
        "req-2",
        &prior,
        failure(FailureStage::AfterPartialOutput, true),
        &next,
        &local_policy(),
    )
    .expect("valid bounded fallback history");

    assert_eq!(
        decision,
        FallbackDecision::Stop {
            reason: FallbackStopReason::PartialOutput,
            cumulative_reserved_cost_microusd: 90,
        }
    );
}

#[test]
fn retry_budget_is_cumulative_and_fails_closed_before_new_cost() {
    let prior = vec![receipt(
        "req-3:attempt:1",
        "engine-a",
        "model-a",
        0,
        460,
        InferenceTargetClass::Local,
    )];
    let next = candidate("engine-b", "model-b", InferenceTargetClass::Local, 80);

    let decision = decide_fallback(
        "req-3",
        &prior,
        failure(FailureStage::BeforeFirstToken, true),
        &next,
        &local_policy(),
    )
    .expect("valid bounded fallback history");

    assert_eq!(
        decision,
        FallbackDecision::Stop {
            reason: FallbackStopReason::BudgetExceeded,
            cumulative_reserved_cost_microusd: 460,
        }
    );
}

#[test]
fn fallback_cannot_silently_downgrade_local_privacy_to_external() {
    let prior = vec![receipt(
        "req-4:attempt:1",
        "engine-local",
        "model-local",
        0,
        20,
        InferenceTargetClass::Local,
    )];
    let next = candidate(
        "engine-cloud",
        "model-cloud",
        InferenceTargetClass::ExternalApproved,
        10,
    );

    let decision = decide_fallback(
        "req-4",
        &prior,
        failure(FailureStage::BeforeFirstToken, true),
        &next,
        &local_policy(),
    )
    .expect("valid bounded fallback history");

    assert_eq!(
        decision,
        FallbackDecision::Stop {
            reason: FallbackStopReason::TargetClassNotAuthorized,
            cumulative_reserved_cost_microusd: 20,
        }
    );
}

#[test]
fn fallback_cannot_loop_back_to_an_already_attempted_engine_model() {
    let prior = vec![
        receipt(
            "req-5:attempt:1",
            "engine-a",
            "model-a",
            0,
            20,
            InferenceTargetClass::Local,
        ),
        receipt(
            "req-5:attempt:2",
            "engine-b",
            "model-b",
            0,
            20,
            InferenceTargetClass::Local,
        ),
    ];
    let next = candidate("engine-a", "model-a", InferenceTargetClass::Local, 20);

    let decision = decide_fallback(
        "req-5",
        &prior,
        failure(FailureStage::BeforeFirstToken, true),
        &next,
        &local_policy(),
    )
    .expect("valid bounded fallback history");

    assert_eq!(
        decision,
        FallbackDecision::Stop {
            reason: FallbackStopReason::RepeatedTarget,
            cumulative_reserved_cost_microusd: 40,
        }
    );
}

#[test]
fn non_retryable_failure_and_attempt_limit_both_stop() {
    let first = vec![receipt(
        "req-6:attempt:1",
        "engine-a",
        "model-a",
        0,
        10,
        InferenceTargetClass::Local,
    )];
    let next = candidate("engine-b", "model-b", InferenceTargetClass::Local, 10);
    let non_retryable = decide_fallback(
        "req-6",
        &first,
        failure(FailureStage::BeforeFirstToken, false),
        &next,
        &local_policy(),
    )
    .expect("valid bounded fallback history");
    assert_eq!(
        non_retryable,
        FallbackDecision::Stop {
            reason: FallbackStopReason::NonRetryable,
            cumulative_reserved_cost_microusd: 10,
        }
    );

    let exhausted = vec![
        receipt(
            "req-7:attempt:1",
            "engine-a",
            "model-a",
            0,
            10,
            InferenceTargetClass::Local,
        ),
        receipt(
            "req-7:attempt:2",
            "engine-b",
            "model-b",
            0,
            10,
            InferenceTargetClass::Local,
        ),
        receipt(
            "req-7:attempt:3",
            "engine-c",
            "model-c",
            0,
            10,
            InferenceTargetClass::Local,
        ),
    ];
    let fourth = candidate("engine-d", "model-d", InferenceTargetClass::Local, 10);
    let at_limit = decide_fallback(
        "req-7",
        &exhausted,
        failure(FailureStage::BeforeFirstToken, true),
        &fourth,
        &local_policy(),
    )
    .expect("valid bounded fallback history");
    assert_eq!(
        at_limit,
        FallbackDecision::Stop {
            reason: FallbackStopReason::AttemptsExhausted,
            cumulative_reserved_cost_microusd: 30,
        }
    );
}

#[test]
fn malformed_history_is_rejected_instead_of_retried() {
    let duplicate = vec![
        receipt(
            "dup",
            "engine-a",
            "model-a",
            0,
            10,
            InferenceTargetClass::Local,
        ),
        receipt(
            "dup",
            "engine-b",
            "model-b",
            0,
            10,
            InferenceTargetClass::Local,
        ),
    ];
    let next = candidate("engine-c", "model-c", InferenceTargetClass::Local, 10);
    assert!(decide_fallback(
        "req-8",
        &duplicate,
        failure(FailureStage::BeforeFirstToken, true),
        &next,
        &local_policy(),
    )
    .is_err());
}
