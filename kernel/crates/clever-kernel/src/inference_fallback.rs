use std::collections::BTreeSet;
use std::fmt;

/// Trust boundary for an inference attempt. A fallback may move only within the
/// class explicitly authorized by the caller's policy; it never grants egress.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum InferenceTargetClass {
    Local,
    ExternalApproved,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AttemptReceipt {
    pub attempt_id: String,
    pub engine_id: String,
    pub model_id: String,
    pub emitted_chunks: u64,
    pub reserved_cost_microusd: u64,
    pub target_class: InferenceTargetClass,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FailureStage {
    BeforeFirstToken,
    AfterPartialOutput,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FailureContext {
    pub stage: FailureStage,
    pub retryable: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FallbackCandidate {
    pub engine_id: String,
    pub model_id: String,
    pub target_class: InferenceTargetClass,
    pub reserved_cost_microusd: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FallbackPolicy {
    /// Total number of attempts including the original attempt.
    pub max_attempts: usize,
    /// Fail-closed cumulative reservation ceiling across all attempts.
    pub max_cumulative_reserved_cost_microusd: u64,
    /// Highest trust/egress class explicitly authorized outside this module.
    pub max_target_class: InferenceTargetClass,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FallbackStopReason {
    NonRetryable,
    PartialOutput,
    AttemptsExhausted,
    BudgetExceeded,
    TargetClassNotAuthorized,
    RepeatedTarget,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FallbackDecision {
    Retry {
        next_attempt_id: String,
        cumulative_reserved_cost_microusd: u64,
    },
    Stop {
        reason: FallbackStopReason,
        cumulative_reserved_cost_microusd: u64,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FallbackHistoryError {
    EmptyRequestId,
    EmptyHistory,
    EmptyAttemptIdentity,
    DuplicateAttemptId,
    StageHistoryMismatch,
    CostOverflow,
    InvalidPolicy,
}

impl fmt::Display for FallbackHistoryError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::EmptyRequestId => "fallback request_id is empty",
            Self::EmptyHistory => "fallback requires at least one prior attempt",
            Self::EmptyAttemptIdentity => "fallback history/candidate contains an empty identity",
            Self::DuplicateAttemptId => "fallback history contains a duplicate attempt_id",
            Self::StageHistoryMismatch => {
                "fallback failure stage disagrees with emitted-chunk history"
            }
            Self::CostOverflow => "fallback cumulative reserved cost overflowed",
            Self::InvalidPolicy => "fallback policy must allow at least one attempt",
        })
    }
}

impl std::error::Error for FallbackHistoryError {}

fn cumulative_cost(history: &[AttemptReceipt]) -> Result<u64, FallbackHistoryError> {
    history.iter().try_fold(0_u64, |total, receipt| {
        total
            .checked_add(receipt.reserved_cost_microusd)
            .ok_or(FallbackHistoryError::CostOverflow)
    })
}

fn validate_history(
    request_id: &str,
    history: &[AttemptReceipt],
    failure_stage: FailureStage,
    policy: &FallbackPolicy,
) -> Result<(), FallbackHistoryError> {
    if request_id.trim().is_empty() {
        return Err(FallbackHistoryError::EmptyRequestId);
    }
    if policy.max_attempts == 0 {
        return Err(FallbackHistoryError::InvalidPolicy);
    }
    if history.is_empty() {
        return Err(FallbackHistoryError::EmptyHistory);
    }

    let mut attempt_ids = BTreeSet::new();
    for receipt in history {
        if receipt.attempt_id.trim().is_empty()
            || receipt.engine_id.trim().is_empty()
            || receipt.model_id.trim().is_empty()
        {
            return Err(FallbackHistoryError::EmptyAttemptIdentity);
        }
        if !attempt_ids.insert(receipt.attempt_id.as_str()) {
            return Err(FallbackHistoryError::DuplicateAttemptId);
        }
    }

    let latest = history.last().expect("non-empty history was checked above");
    match failure_stage {
        FailureStage::BeforeFirstToken if latest.emitted_chunks != 0 => {
            return Err(FallbackHistoryError::StageHistoryMismatch);
        }
        FailureStage::AfterPartialOutput if latest.emitted_chunks == 0 => {
            return Err(FallbackHistoryError::StageHistoryMismatch);
        }
        FailureStage::BeforeFirstToken | FailureStage::AfterPartialOutput => {}
    }
    Ok(())
}

/// Decide whether a failed inference may start one additional attempt.
///
/// This function is deliberately authority-free: it consumes an already
/// authorized target class and a reservation ceiling but cannot grant provider
/// egress, execute a model, or splice model output. Once any output has been
/// emitted, the only valid decision is a partial stop.
pub fn decide_fallback(
    request_id: &str,
    history: &[AttemptReceipt],
    failure: FailureContext,
    candidate: &FallbackCandidate,
    policy: &FallbackPolicy,
) -> Result<FallbackDecision, FallbackHistoryError> {
    validate_history(request_id, history, failure.stage, policy)?;
    if candidate.engine_id.trim().is_empty() || candidate.model_id.trim().is_empty() {
        return Err(FallbackHistoryError::EmptyAttemptIdentity);
    }

    let spent = cumulative_cost(history)?;
    if matches!(failure.stage, FailureStage::AfterPartialOutput) {
        return Ok(FallbackDecision::Stop {
            reason: FallbackStopReason::PartialOutput,
            cumulative_reserved_cost_microusd: spent,
        });
    }
    if !failure.retryable {
        return Ok(FallbackDecision::Stop {
            reason: FallbackStopReason::NonRetryable,
            cumulative_reserved_cost_microusd: spent,
        });
    }
    if history.len() >= policy.max_attempts {
        return Ok(FallbackDecision::Stop {
            reason: FallbackStopReason::AttemptsExhausted,
            cumulative_reserved_cost_microusd: spent,
        });
    }
    if candidate.target_class > policy.max_target_class {
        return Ok(FallbackDecision::Stop {
            reason: FallbackStopReason::TargetClassNotAuthorized,
            cumulative_reserved_cost_microusd: spent,
        });
    }
    if history.iter().any(|receipt| {
        receipt.engine_id == candidate.engine_id
            && receipt.model_id == candidate.model_id
            && receipt.target_class == candidate.target_class
    }) {
        return Ok(FallbackDecision::Stop {
            reason: FallbackStopReason::RepeatedTarget,
            cumulative_reserved_cost_microusd: spent,
        });
    }

    let with_candidate = spent
        .checked_add(candidate.reserved_cost_microusd)
        .ok_or(FallbackHistoryError::CostOverflow)?;
    if with_candidate > policy.max_cumulative_reserved_cost_microusd {
        return Ok(FallbackDecision::Stop {
            reason: FallbackStopReason::BudgetExceeded,
            cumulative_reserved_cost_microusd: spent,
        });
    }

    Ok(FallbackDecision::Retry {
        next_attempt_id: format!("{request_id}:attempt:{}", history.len() + 1),
        cumulative_reserved_cost_microusd: with_candidate,
    })
}
