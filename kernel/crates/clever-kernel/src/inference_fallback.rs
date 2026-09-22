use clever_contracts::{InferenceChunk, InferenceRequest, InferenceTerminal};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FallbackCandidate {
    pub engine_id: String,
    pub model_id: String,
    pub estimated_cost_microusd: u64,
    /// W02-14 is deliberately local-only. A later checkpoint may authorize
    /// external candidates through the kernel egress/grant path, but this core
    /// must not silently weaken privacy while retrying.
    pub external: bool,
}

impl FallbackCandidate {
    #[must_use]
    pub fn local(
        engine_id: impl Into<String>,
        model_id: impl Into<String>,
        estimated_cost_microusd: u64,
    ) -> Self {
        Self {
            engine_id: engine_id.into(),
            model_id: model_id.into(),
            estimated_cost_microusd,
            external: false,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FallbackPolicy {
    pub max_attempts: usize,
    pub max_total_cost_microusd: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AttemptDisposition {
    Succeeded,
    RetryableFailureBeforeOutput,
    TerminalFailureBeforeOutput,
    PartialFailureAfterOutput,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AttemptReceipt {
    pub request_id: String,
    pub attempt_id: String,
    pub engine_id: String,
    pub model_id: String,
    pub estimated_cost_microusd: u64,
    pub cumulative_cost_microusd: u64,
    pub emitted_chunks: usize,
    pub disposition: AttemptDisposition,
}

#[derive(Debug, Clone, PartialEq)]
pub enum AttemptStreamResult<E> {
    Complete {
        chunks: Vec<InferenceChunk>,
        text: String,
        terminal: InferenceTerminal,
    },
    FailedBeforeOutput {
        error: E,
        retryable: bool,
    },
    FailedAfterOutput {
        chunks: Vec<InferenceChunk>,
        text: String,
        error: E,
    },
}

#[derive(Debug, Clone, PartialEq)]
pub enum FallbackOutcome<E> {
    Complete {
        chunks: Vec<InferenceChunk>,
        text: String,
        terminal: InferenceTerminal,
        receipts: Vec<AttemptReceipt>,
    },
    Partial {
        chunks: Vec<InferenceChunk>,
        text: String,
        error: E,
        receipts: Vec<AttemptReceipt>,
    },
    Failed {
        error: E,
        receipts: Vec<AttemptReceipt>,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FallbackPolicyError {
    EmptyPlan,
    ZeroAttemptBudget,
    InvalidBaseAttemptId,
    InvalidCandidate { index: usize },
    PrimaryCandidateMismatch,
    PrivacyDowngrade { index: usize },
    CostOverflow,
    CostBudgetExceeded {
        attempted: u64,
        maximum: u64,
        candidate_index: usize,
    },
    InvalidCompletedStream { reason: &'static str },
    InvalidPartialStream { reason: &'static str },
}

fn retry_attempt_id(base_attempt_id: &str, ordinal: usize) -> String {
    if ordinal == 0 {
        return base_attempt_id.to_owned();
    }
    format!("{base_attempt_id}.retry.{ordinal}")
}

fn validate_plan(
    base_request: &InferenceRequest,
    candidates: &[FallbackCandidate],
    policy: FallbackPolicy,
) -> Result<(), FallbackPolicyError> {
    if candidates.is_empty() {
        return Err(FallbackPolicyError::EmptyPlan);
    }
    if policy.max_attempts == 0 {
        return Err(FallbackPolicyError::ZeroAttemptBudget);
    }
    if base_request.attempt_id.trim().is_empty() {
        return Err(FallbackPolicyError::InvalidBaseAttemptId);
    }
    for (index, candidate) in candidates.iter().enumerate() {
        if candidate.engine_id.trim().is_empty() || candidate.model_id.trim().is_empty() {
            return Err(FallbackPolicyError::InvalidCandidate { index });
        }
        if candidate.external {
            return Err(FallbackPolicyError::PrivacyDowngrade { index });
        }
    }
    if candidates[0].engine_id != base_request.engine_id
        || candidates[0].model_id != base_request.model_id
    {
        return Err(FallbackPolicyError::PrimaryCandidateMismatch);
    }
    Ok(())
}

fn validate_complete(
    request: &InferenceRequest,
    chunks: &[InferenceChunk],
    terminal: &InferenceTerminal,
) -> Result<(), FallbackPolicyError> {
    if chunks.is_empty() {
        return Err(FallbackPolicyError::InvalidCompletedStream {
            reason: "completed fallback attempt has no content chunks",
        });
    }
    let mut expected = 1_u64;
    for chunk in chunks {
        if chunk.request_id != request.request_id
            || chunk.attempt_id != request.attempt_id
            || chunk.sequence != expected
            || chunk.text_delta.is_empty()
        {
            return Err(FallbackPolicyError::InvalidCompletedStream {
                reason: "chunk identity/sequence/content mismatch",
            });
        }
        expected = expected.saturating_add(1);
    }
    if terminal.request_id != request.request_id
        || terminal.attempt_id != request.attempt_id
        || terminal.final_sequence != expected.saturating_sub(1)
    {
        return Err(FallbackPolicyError::InvalidCompletedStream {
            reason: "terminal identity/final_sequence mismatch",
        });
    }
    Ok(())
}

fn validate_partial(
    request: &InferenceRequest,
    chunks: &[InferenceChunk],
    text: &str,
) -> Result<(), FallbackPolicyError> {
    if chunks.is_empty() || text.is_empty() {
        return Err(FallbackPolicyError::InvalidPartialStream {
            reason: "after-output failure must preserve non-empty partial output",
        });
    }
    let mut expected = 1_u64;
    let mut rebuilt = String::new();
    for chunk in chunks {
        if chunk.request_id != request.request_id
            || chunk.attempt_id != request.attempt_id
            || chunk.sequence != expected
            || chunk.text_delta.is_empty()
        {
            return Err(FallbackPolicyError::InvalidPartialStream {
                reason: "partial chunk identity/sequence/content mismatch",
            });
        }
        rebuilt.push_str(&chunk.text_delta);
        expected = expected.saturating_add(1);
    }
    if rebuilt != text {
        return Err(FallbackPolicyError::InvalidPartialStream {
            reason: "partial text does not equal the emitted chunk stream",
        });
    }
    Ok(())
}

/// Execute a bounded local-only fallback plan without ever splicing streams.
///
/// The base request is cloned for every attempt. Only `attempt_id`, `engine_id`
/// and `model_id` may change. Therefore principal/session/input/config/deadline,
/// idempotency and structured-output policy remain byte-for-byte inherited from
/// the caller. A retry is allowed only for an explicitly retryable failure that
/// happened before the first output chunk. Once any chunk has been emitted, the
/// failure is returned truthfully as `Partial` and no later candidate is run.
pub fn execute_streaming_fallback<E, F>(
    base_request: &InferenceRequest,
    candidates: &[FallbackCandidate],
    policy: FallbackPolicy,
    mut execute_attempt: F,
) -> Result<FallbackOutcome<E>, FallbackPolicyError>
where
    F: FnMut(&InferenceRequest) -> AttemptStreamResult<E>,
{
    validate_plan(base_request, candidates, policy)?;

    let attempt_limit = policy.max_attempts.min(candidates.len());
    let mut receipts = Vec::with_capacity(attempt_limit);
    let mut cumulative_cost_microusd = 0_u64;

    for (index, candidate) in candidates.iter().take(attempt_limit).enumerate() {
        cumulative_cost_microusd = cumulative_cost_microusd
            .checked_add(candidate.estimated_cost_microusd)
            .ok_or(FallbackPolicyError::CostOverflow)?;
        if cumulative_cost_microusd > policy.max_total_cost_microusd {
            return Err(FallbackPolicyError::CostBudgetExceeded {
                attempted: cumulative_cost_microusd,
                maximum: policy.max_total_cost_microusd,
                candidate_index: index,
            });
        }

        let mut request = base_request.clone();
        request.attempt_id = retry_attempt_id(&base_request.attempt_id, index);
        request.engine_id.clone_from(&candidate.engine_id);
        request.model_id.clone_from(&candidate.model_id);

        match execute_attempt(&request) {
            AttemptStreamResult::Complete {
                chunks,
                text,
                terminal,
            } => {
                validate_complete(&request, &chunks, &terminal)?;
                let rebuilt = chunks
                    .iter()
                    .map(|chunk| chunk.text_delta.as_str())
                    .collect::<String>();
                if rebuilt != text {
                    return Err(FallbackPolicyError::InvalidCompletedStream {
                        reason: "completed text does not equal the emitted chunk stream",
                    });
                }
                receipts.push(AttemptReceipt {
                    request_id: request.request_id.clone(),
                    attempt_id: request.attempt_id.clone(),
                    engine_id: request.engine_id.clone(),
                    model_id: request.model_id.clone(),
                    estimated_cost_microusd: candidate.estimated_cost_microusd,
                    cumulative_cost_microusd,
                    emitted_chunks: chunks.len(),
                    disposition: AttemptDisposition::Succeeded,
                });
                return Ok(FallbackOutcome::Complete {
                    chunks,
                    text,
                    terminal,
                    receipts,
                });
            }
            AttemptStreamResult::FailedBeforeOutput { error, retryable } => {
                receipts.push(AttemptReceipt {
                    request_id: request.request_id.clone(),
                    attempt_id: request.attempt_id.clone(),
                    engine_id: request.engine_id.clone(),
                    model_id: request.model_id.clone(),
                    estimated_cost_microusd: candidate.estimated_cost_microusd,
                    cumulative_cost_microusd,
                    emitted_chunks: 0,
                    disposition: if retryable {
                        AttemptDisposition::RetryableFailureBeforeOutput
                    } else {
                        AttemptDisposition::TerminalFailureBeforeOutput
                    },
                });
                let has_next = index.saturating_add(1) < attempt_limit;
                if retryable && has_next {
                    continue;
                }
                return Ok(FallbackOutcome::Failed { error, receipts });
            }
            AttemptStreamResult::FailedAfterOutput {
                chunks,
                text,
                error,
            } => {
                validate_partial(&request, &chunks, &text)?;
                receipts.push(AttemptReceipt {
                    request_id: request.request_id.clone(),
                    attempt_id: request.attempt_id.clone(),
                    engine_id: request.engine_id.clone(),
                    model_id: request.model_id.clone(),
                    estimated_cost_microusd: candidate.estimated_cost_microusd,
                    cumulative_cost_microusd,
                    emitted_chunks: chunks.len(),
                    disposition: AttemptDisposition::PartialFailureAfterOutput,
                });
                return Ok(FallbackOutcome::Partial {
                    chunks,
                    text,
                    error,
                    receipts,
                });
            }
        }
    }

    unreachable!("validated non-empty fallback plan always returns from the bounded loop")
}

#[cfg(test)]
mod tests {
    use super::*;
    use clever_contracts::{
        ContractVersion, InferenceConfig, InferenceFinishReason, InferenceInput, InferenceRole,
        PrincipalRef,
    };

    fn base_request() -> InferenceRequest {
        InferenceRequest {
            contract_version: Some(ContractVersion { major: 1, minor: 2 }),
            request_id: "request-1".to_owned(),
            attempt_id: "attempt-1".to_owned(),
            principal: Some(PrincipalRef {
                user_id: "local-user".to_owned(),
                device_id: "device".to_owned(),
                channel_id: "channel".to_owned(),
                tenant_id: "tenant".to_owned(),
            }),
            session_id: "session-1".to_owned(),
            engine_id: "engine-a".to_owned(),
            model_id: "model-a".to_owned(),
            inputs: vec![InferenceInput {
                role: InferenceRole::User as i32,
                content: "hello".to_owned(),
                name: String::new(),
            }],
            config: Some(InferenceConfig {
                max_output_tokens: 16,
                temperature: Some(0.0),
                top_p: None,
                stop_sequences: Vec::new(),
                stream: true,
            }),
            deadline_at: None,
            idempotency_key: "idem-1".to_owned(),
            response_schema_json: Some("{\"type\":\"object\"}".to_owned()),
        }
    }

    fn chunk(request: &InferenceRequest, sequence: u64, text: &str) -> InferenceChunk {
        InferenceChunk {
            contract_version: Some(ContractVersion { major: 1, minor: 2 }),
            request_id: request.request_id.clone(),
            attempt_id: request.attempt_id.clone(),
            sequence,
            text_delta: text.to_owned(),
        }
    }

    fn terminal(request: &InferenceRequest, final_sequence: u64) -> InferenceTerminal {
        InferenceTerminal {
            contract_version: Some(ContractVersion { major: 1, minor: 2 }),
            request_id: request.request_id.clone(),
            attempt_id: request.attempt_id.clone(),
            final_sequence,
            finish_reason: InferenceFinishReason::Stop as i32,
            usage: None,
        }
    }

    #[test]
    fn retry_before_first_token_uses_fresh_attempt_and_preserves_request_scope() {
        let base = base_request();
        let candidates = vec![
            FallbackCandidate::local("engine-a", "model-a", 3),
            FallbackCandidate::local("engine-b", "model-b", 5),
        ];
        let mut seen = Vec::new();
        let outcome = execute_streaming_fallback(
            &base,
            &candidates,
            FallbackPolicy {
                max_attempts: 2,
                max_total_cost_microusd: 8,
            },
            |request| {
                seen.push(request.clone());
                if request.engine_id == "engine-a" {
                    AttemptStreamResult::FailedBeforeOutput {
                        error: "engine unavailable",
                        retryable: true,
                    }
                } else {
                    AttemptStreamResult::Complete {
                        chunks: vec![chunk(request, 1, "ok")],
                        text: "ok".to_owned(),
                        terminal: terminal(request, 1),
                    }
                }
            },
        )
        .expect("fallback policy accepted");

        assert_eq!(seen.len(), 2);
        assert_eq!(seen[0].attempt_id, "attempt-1");
        assert_eq!(seen[1].attempt_id, "attempt-1.retry.1");
        assert_eq!(seen[0].request_id, seen[1].request_id);
        assert_eq!(seen[0].principal, seen[1].principal);
        assert_eq!(seen[0].session_id, seen[1].session_id);
        assert_eq!(seen[0].inputs, seen[1].inputs);
        assert_eq!(seen[0].config, seen[1].config);
        assert_eq!(seen[0].deadline_at, seen[1].deadline_at);
        assert_eq!(seen[0].idempotency_key, seen[1].idempotency_key);
        assert_eq!(seen[0].response_schema_json, seen[1].response_schema_json);
        match outcome {
            FallbackOutcome::Complete { text, receipts, .. } => {
                assert_eq!(text, "ok");
                assert_eq!(receipts.len(), 2);
                assert_eq!(receipts[0].emitted_chunks, 0);
                assert_eq!(receipts[1].cumulative_cost_microusd, 8);
                assert_eq!(receipts[1].attempt_id, "attempt-1.retry.1");
            }
            other => panic!("unexpected outcome: {other:?}"),
        }
    }

    #[test]
    fn failure_after_first_token_is_partial_and_never_retries() {
        let base = base_request();
        let candidates = vec![
            FallbackCandidate::local("engine-a", "model-a", 1),
            FallbackCandidate::local("engine-b", "model-b", 1),
        ];
        let mut calls = 0_usize;
        let outcome = execute_streaming_fallback(
            &base,
            &candidates,
            FallbackPolicy {
                max_attempts: 2,
                max_total_cost_microusd: 2,
            },
            |request| {
                calls += 1;
                AttemptStreamResult::FailedAfterOutput {
                    chunks: vec![chunk(request, 1, "partial")],
                    text: "partial".to_owned(),
                    error: "late failure",
                }
            },
        )
        .expect("partial outcome must remain truthful");
        assert_eq!(calls, 1);
        match outcome {
            FallbackOutcome::Partial {
                text,
                error,
                receipts,
                ..
            } => {
                assert_eq!(text, "partial");
                assert_eq!(error, "late failure");
                assert_eq!(receipts.len(), 1);
                assert_eq!(
                    receipts[0].disposition,
                    AttemptDisposition::PartialFailureAfterOutput
                );
            }
            other => panic!("unexpected outcome: {other:?}"),
        }
    }

    #[test]
    fn non_retryable_failure_does_not_run_fallback() {
        let base = base_request();
        let candidates = vec![
            FallbackCandidate::local("engine-a", "model-a", 0),
            FallbackCandidate::local("engine-b", "model-b", 0),
        ];
        let mut calls = 0_usize;
        let outcome = execute_streaming_fallback(
            &base,
            &candidates,
            FallbackPolicy {
                max_attempts: 2,
                max_total_cost_microusd: 0,
            },
            |_| {
                calls += 1;
                AttemptStreamResult::FailedBeforeOutput {
                    error: "invalid request",
                    retryable: false,
                }
            },
        )
        .expect("non-retryable failure is an outcome, not a policy error");
        assert_eq!(calls, 1);
        assert!(matches!(outcome, FallbackOutcome::Failed { .. }));
    }

    #[test]
    fn external_candidate_is_rejected_before_any_attempt() {
        let base = base_request();
        let mut external = FallbackCandidate::local("engine-b", "model-b", 0);
        external.external = true;
        let candidates = vec![FallbackCandidate::local("engine-a", "model-a", 0), external];
        let mut calls = 0_usize;
        let error = execute_streaming_fallback::<(), _>(
            &base,
            &candidates,
            FallbackPolicy {
                max_attempts: 2,
                max_total_cost_microusd: 0,
            },
            |_| {
                calls += 1;
                unreachable!("privacy-invalid plan must fail before execution")
            },
        )
        .expect_err("external fallback must fail closed");
        assert_eq!(calls, 0);
        assert_eq!(error, FallbackPolicyError::PrivacyDowngrade { index: 1 });
    }

    #[test]
    fn cumulative_cost_budget_blocks_next_attempt_without_hidden_execution() {
        let base = base_request();
        let candidates = vec![
            FallbackCandidate::local("engine-a", "model-a", 4),
            FallbackCandidate::local("engine-b", "model-b", 7),
        ];
        let mut calls = 0_usize;
        let error = execute_streaming_fallback(
            &base,
            &candidates,
            FallbackPolicy {
                max_attempts: 2,
                max_total_cost_microusd: 10,
            },
            |_| {
                calls += 1;
                AttemptStreamResult::FailedBeforeOutput {
                    error: "retry me",
                    retryable: true,
                }
            },
        )
        .expect_err("second reservation exceeds cumulative budget");
        assert_eq!(calls, 1);
        assert_eq!(
            error,
            FallbackPolicyError::CostBudgetExceeded {
                attempted: 11,
                maximum: 10,
                candidate_index: 1,
            }
        );
    }

    #[test]
    fn max_attempts_bounds_retry_loop() {
        let base = base_request();
        let candidates = vec![
            FallbackCandidate::local("engine-a", "model-a", 0),
            FallbackCandidate::local("engine-b", "model-b", 0),
            FallbackCandidate::local("engine-c", "model-c", 0),
        ];
        let mut calls = 0_usize;
        let outcome = execute_streaming_fallback(
            &base,
            &candidates,
            FallbackPolicy {
                max_attempts: 2,
                max_total_cost_microusd: 0,
            },
            |_| {
                calls += 1;
                AttemptStreamResult::FailedBeforeOutput {
                    error: "retryable",
                    retryable: true,
                }
            },
        )
        .expect("bounded retries are a valid failed outcome");
        assert_eq!(calls, 2);
        match outcome {
            FallbackOutcome::Failed { receipts, .. } => assert_eq!(receipts.len(), 2),
            other => panic!("unexpected outcome: {other:?}"),
        }
    }
}
