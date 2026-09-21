use std::fmt::{Debug, Display, Formatter};

use clever_contracts::{InferenceRequest, InferenceTerminal, PrincipalRef};

use crate::{identity::validate_principal, version::validate_contract_version};

#[derive(Clone, PartialEq, Eq)]
pub struct SecretHandle(String);

impl SecretHandle {
    pub fn new(value: impl Into<String>) -> Result<Self, InferenceSecurityError> {
        let value = value.into();
        if value.trim().is_empty() {
            return Err(InferenceSecurityError::InvalidSecretHandle);
        }
        Ok(Self(value))
    }

    /// Deliberate escape hatch for a trusted secret-store boundary only.
    /// Callers must never place this value in model payloads, logs, traces or evidence.
    #[must_use]
    pub fn expose_to_secret_store(&self) -> &str {
        &self.0
    }
}

impl Debug for SecretHandle {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("SecretHandle(<redacted>)")
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InferenceBudget {
    pub max_input_tokens: u64,
    pub max_output_tokens: u64,
    pub max_total_tokens: u64,
    pub max_cost_microusd: u64,
}

impl InferenceBudget {
    fn validate(&self) -> Result<(), InferenceSecurityError> {
        if self.max_input_tokens == 0
            || self.max_output_tokens == 0
            || self.max_total_tokens == 0
            || self.max_cost_microusd == 0
        {
            return Err(InferenceSecurityError::InvalidBudget);
        }
        if self.max_input_tokens > self.max_total_tokens
            || self.max_output_tokens > self.max_total_tokens
        {
            return Err(InferenceSecurityError::InvalidBudget);
        }
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InferenceReservation {
    pub estimated_input_tokens: u64,
    pub estimated_cost_microusd: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InferenceTarget {
    pub provider_id: String,
    pub origin: String,
    pub external: bool,
}

#[derive(Clone, PartialEq)]
pub struct ExternalInferenceGrant {
    pub grant_id: String,
    pub principal: PrincipalRef,
    pub session_id: String,
    pub provider_id: String,
    pub origin: String,
    pub credential_handle: SecretHandle,
    pub budget: InferenceBudget,
    pub expires_at_unix_seconds: u64,
}

impl Debug for ExternalInferenceGrant {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("ExternalInferenceGrant")
            .field("grant_id", &self.grant_id)
            .field("principal", &self.principal)
            .field("session_id", &self.session_id)
            .field("provider_id", &self.provider_id)
            .field("origin", &self.origin)
            .field("credential_handle", &self.credential_handle)
            .field("budget", &self.budget)
            .field("expires_at_unix_seconds", &self.expires_at_unix_seconds)
            .finish()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EgressAuthorization {
    Local,
    External(ExternalAuthorization),
}

#[derive(Clone, PartialEq, Eq)]
pub struct ExternalAuthorization {
    pub grant_id: String,
    pub provider_id: String,
    pub origin: String,
    pub credential_handle: SecretHandle,
    pub budget: InferenceBudget,
}

impl Debug for ExternalAuthorization {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("ExternalAuthorization")
            .field("grant_id", &self.grant_id)
            .field("provider_id", &self.provider_id)
            .field("origin", &self.origin)
            .field("credential_handle", &self.credential_handle)
            .field("budget", &self.budget)
            .finish()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InferenceEgressAudit {
    pub request_id: String,
    pub attempt_id: String,
    pub grant_id: Option<String>,
    pub provider_id: String,
    pub origin: String,
    pub external: bool,
    pub credential_handle_present: bool,
    pub reserved_input_tokens: u64,
    pub requested_max_output_tokens: u64,
    pub reserved_cost_microusd: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InferenceSecurityError {
    InvalidRequest,
    InvalidTarget,
    InvalidExternalOrigin,
    InvalidGrant,
    InvalidSecretHandle,
    InvalidBudget,
    ExternalGrantRequired,
    GrantExpired,
    PrincipalMismatch,
    SessionMismatch,
    ProviderMismatch,
    OriginMismatch,
    InputBudgetExceeded,
    OutputBudgetExceeded,
    TotalBudgetExceeded,
    CostBudgetExceeded,
    UsageBudgetExceeded,
}

impl Display for InferenceSecurityError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        let message = match self {
            Self::InvalidRequest => "invalid inference request",
            Self::InvalidTarget => "invalid inference target",
            Self::InvalidExternalOrigin => "external inference origin is not canonical HTTPS",
            Self::InvalidGrant => "invalid external inference grant",
            Self::InvalidSecretHandle => "invalid opaque secret handle",
            Self::InvalidBudget => "invalid inference budget",
            Self::ExternalGrantRequired => "external inference requires a canonical grant",
            Self::GrantExpired => "external inference grant expired",
            Self::PrincipalMismatch => "external inference grant principal mismatch",
            Self::SessionMismatch => "external inference grant session mismatch",
            Self::ProviderMismatch => "external inference grant provider mismatch",
            Self::OriginMismatch => "external inference grant origin mismatch",
            Self::InputBudgetExceeded => "inference input token budget exceeded",
            Self::OutputBudgetExceeded => "inference output token budget exceeded",
            Self::TotalBudgetExceeded => "inference total token budget exceeded",
            Self::CostBudgetExceeded => "inference cost budget exceeded",
            Self::UsageBudgetExceeded => "reported inference usage exceeded reserved budget",
        };
        formatter.write_str(message)
    }
}

impl std::error::Error for InferenceSecurityError {}

pub fn authorize_inference_egress(
    request: &InferenceRequest,
    target: &InferenceTarget,
    grant: Option<&ExternalInferenceGrant>,
    reservation: &InferenceReservation,
    now_unix_seconds: u64,
) -> Result<(EgressAuthorization, InferenceEgressAudit), InferenceSecurityError> {
    validate_contract_version(request.contract_version.as_ref())
        .map_err(|_| InferenceSecurityError::InvalidRequest)?;
    validate_principal(request.principal.as_ref())
        .map_err(|_| InferenceSecurityError::InvalidRequest)?;
    if request.request_id.trim().is_empty()
        || request.attempt_id.trim().is_empty()
        || request.session_id.trim().is_empty()
        || request.engine_id.trim().is_empty()
        || request.model_id.trim().is_empty()
    {
        return Err(InferenceSecurityError::InvalidRequest);
    }
    let config = request
        .config
        .as_ref()
        .ok_or(InferenceSecurityError::InvalidRequest)?;
    if config.max_output_tokens == 0 {
        return Err(InferenceSecurityError::InvalidRequest);
    }
    validate_target(target)?;

    if !target.external {
        return Ok((
            EgressAuthorization::Local,
            InferenceEgressAudit {
                request_id: request.request_id.clone(),
                attempt_id: request.attempt_id.clone(),
                grant_id: None,
                provider_id: target.provider_id.clone(),
                origin: target.origin.clone(),
                external: false,
                credential_handle_present: false,
                reserved_input_tokens: reservation.estimated_input_tokens,
                requested_max_output_tokens: config.max_output_tokens,
                reserved_cost_microusd: reservation.estimated_cost_microusd,
            },
        ));
    }

    validate_external_origin(&target.origin)?;
    let grant = grant.ok_or(InferenceSecurityError::ExternalGrantRequired)?;
    validate_grant(grant)?;
    if grant.expires_at_unix_seconds <= now_unix_seconds {
        return Err(InferenceSecurityError::GrantExpired);
    }
    if request.principal.as_ref() != Some(&grant.principal) {
        return Err(InferenceSecurityError::PrincipalMismatch);
    }
    if request.session_id != grant.session_id {
        return Err(InferenceSecurityError::SessionMismatch);
    }
    if target.provider_id != grant.provider_id {
        return Err(InferenceSecurityError::ProviderMismatch);
    }
    if target.origin != grant.origin {
        return Err(InferenceSecurityError::OriginMismatch);
    }

    enforce_budget(config.max_output_tokens, reservation, &grant.budget)?;

    let authorization = ExternalAuthorization {
        grant_id: grant.grant_id.clone(),
        provider_id: grant.provider_id.clone(),
        origin: grant.origin.clone(),
        credential_handle: grant.credential_handle.clone(),
        budget: grant.budget.clone(),
    };
    let audit = InferenceEgressAudit {
        request_id: request.request_id.clone(),
        attempt_id: request.attempt_id.clone(),
        grant_id: Some(grant.grant_id.clone()),
        provider_id: target.provider_id.clone(),
        origin: target.origin.clone(),
        external: true,
        credential_handle_present: true,
        reserved_input_tokens: reservation.estimated_input_tokens,
        requested_max_output_tokens: config.max_output_tokens,
        reserved_cost_microusd: reservation.estimated_cost_microusd,
    };
    Ok((EgressAuthorization::External(authorization), audit))
}

pub fn validate_terminal_usage(
    terminal: &InferenceTerminal,
    budget: &InferenceBudget,
) -> Result<(), InferenceSecurityError> {
    budget.validate()?;
    let usage = terminal
        .usage
        .as_ref()
        .ok_or(InferenceSecurityError::UsageBudgetExceeded)?;
    if usage
        .input_tokens
        .is_some_and(|value| value > budget.max_input_tokens)
        || usage
            .output_tokens
            .is_some_and(|value| value > budget.max_output_tokens)
        || usage
            .total_tokens
            .is_some_and(|value| value > budget.max_total_tokens)
    {
        return Err(InferenceSecurityError::UsageBudgetExceeded);
    }
    Ok(())
}

fn validate_target(target: &InferenceTarget) -> Result<(), InferenceSecurityError> {
    if target.provider_id.trim().is_empty() || target.origin.trim().is_empty() {
        return Err(InferenceSecurityError::InvalidTarget);
    }
    Ok(())
}

fn validate_external_origin(origin: &str) -> Result<(), InferenceSecurityError> {
    if !origin.starts_with("https://") {
        return Err(InferenceSecurityError::InvalidExternalOrigin);
    }
    let authority = &origin[8..];
    if authority.is_empty()
        || authority.bytes().any(|byte| byte.is_ascii_whitespace())
        || authority.contains('/')
        || authority.contains('?')
        || authority.contains('#')
        || authority.contains('@')
    {
        return Err(InferenceSecurityError::InvalidExternalOrigin);
    }
    Ok(())
}

fn validate_grant(grant: &ExternalInferenceGrant) -> Result<(), InferenceSecurityError> {
    if grant.grant_id.trim().is_empty()
        || grant.session_id.trim().is_empty()
        || grant.provider_id.trim().is_empty()
        || grant.origin.trim().is_empty()
        || grant.expires_at_unix_seconds == 0
    {
        return Err(InferenceSecurityError::InvalidGrant);
    }
    validate_principal(Some(&grant.principal)).map_err(|_| InferenceSecurityError::InvalidGrant)?;
    validate_external_origin(&grant.origin)?;
    grant.budget.validate()
}

fn enforce_budget(
    requested_max_output_tokens: u64,
    reservation: &InferenceReservation,
    budget: &InferenceBudget,
) -> Result<(), InferenceSecurityError> {
    budget.validate()?;
    if reservation.estimated_input_tokens > budget.max_input_tokens {
        return Err(InferenceSecurityError::InputBudgetExceeded);
    }
    if requested_max_output_tokens > budget.max_output_tokens {
        return Err(InferenceSecurityError::OutputBudgetExceeded);
    }
    if reservation
        .estimated_input_tokens
        .saturating_add(requested_max_output_tokens)
        > budget.max_total_tokens
    {
        return Err(InferenceSecurityError::TotalBudgetExceeded);
    }
    if reservation.estimated_cost_microusd > budget.max_cost_microusd {
        return Err(InferenceSecurityError::CostBudgetExceeded);
    }
    Ok(())
}
