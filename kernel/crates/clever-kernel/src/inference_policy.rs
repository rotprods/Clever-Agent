use std::{
    fmt::{Debug, Display, Formatter},
    time::SystemTime,
};

use clever_contracts::{InferenceRequest, PrincipalRef};

use crate::{
    error::KernelError, identity::validate_principal, version::validate_contract_version,
};

#[derive(Clone, PartialEq, Eq)]
pub struct SecretHandle(String);

impl SecretHandle {
    pub fn new(value: impl Into<String>) -> Result<Self, InferenceAdmissionError> {
        let value = value.into();
        if value.trim().is_empty() || value.chars().any(char::is_control) {
            return Err(InferenceAdmissionError::InvalidGrant);
        }
        Ok(Self(value))
    }

    fn matches(&self, other: &Self) -> bool {
        self.0 == other.0
    }
}

impl Debug for SecretHandle {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("SecretHandle(<redacted>)")
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InferenceEgressMode {
    Local,
    Remote,
}

#[derive(Clone, PartialEq, Eq)]
pub struct RemoteInferenceGrant {
    grant_id: String,
    principal: PrincipalRef,
    session_id: String,
    destination: String,
    max_input_tokens: u64,
    max_output_tokens: u64,
    max_total_tokens: u64,
    max_cost_microunits: u64,
    secret_handle: SecretHandle,
    expires_at: SystemTime,
}

impl Debug for RemoteInferenceGrant {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("RemoteInferenceGrant")
            .field("grant_id", &self.grant_id)
            .field("principal", &self.principal)
            .field("session_id", &self.session_id)
            .field("destination", &self.destination)
            .field("max_input_tokens", &self.max_input_tokens)
            .field("max_output_tokens", &self.max_output_tokens)
            .field("max_total_tokens", &self.max_total_tokens)
            .field("max_cost_microunits", &self.max_cost_microunits)
            .field("secret_handle", &self.secret_handle)
            .field("expires_at", &self.expires_at)
            .finish()
    }
}

impl RemoteInferenceGrant {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        grant_id: impl Into<String>,
        principal: PrincipalRef,
        session_id: impl Into<String>,
        destination: impl Into<String>,
        max_input_tokens: u64,
        max_output_tokens: u64,
        max_total_tokens: u64,
        max_cost_microunits: u64,
        secret_handle: SecretHandle,
        expires_at: SystemTime,
    ) -> Result<Self, InferenceAdmissionError> {
        validate_principal(Some(&principal))?;
        let grant_id = grant_id.into();
        let session_id = session_id.into();
        let destination = destination.into();
        if grant_id.trim().is_empty()
            || session_id.trim().is_empty()
            || max_input_tokens == 0
            || max_output_tokens == 0
            || max_total_tokens == 0
            || max_cost_microunits == 0
            || max_input_tokens > max_total_tokens
            || max_output_tokens > max_total_tokens
        {
            return Err(InferenceAdmissionError::InvalidGrant);
        }
        validate_remote_destination(&destination)?;
        Ok(Self {
            grant_id,
            principal,
            session_id,
            destination,
            max_input_tokens,
            max_output_tokens,
            max_total_tokens,
            max_cost_microunits,
            secret_handle,
            expires_at,
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InferenceRoute {
    Local,
    Remote {
        destination: String,
        secret_handle: SecretHandle,
        estimated_input_tokens: u64,
        estimated_cost_microunits: u64,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InferenceBudgetReservation {
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub total_tokens: u64,
    pub cost_microunits: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InferenceAuditRecord {
    pub request_id: String,
    pub attempt_id: String,
    pub user_id: String,
    pub session_id: String,
    pub mode: InferenceEgressMode,
    pub grant_id: Option<String>,
    pub destination: Option<String>,
    pub secret_handle_used: bool,
    pub reservation: InferenceBudgetReservation,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InferenceAdmission {
    pub mode: InferenceEgressMode,
    pub reservation: InferenceBudgetReservation,
    pub audit: InferenceAuditRecord,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InferenceAdmissionError {
    Kernel(KernelError),
    RemoteGrantRequired,
    GrantExpired,
    GrantPrincipalMismatch,
    GrantSessionMismatch,
    DestinationNotAllowed,
    SecretHandleMismatch,
    InputTokenBudgetExceeded,
    OutputTokenBudgetExceeded,
    TotalTokenBudgetExceeded,
    CostBudgetExceeded,
    InvalidDestination,
    InvalidGrant,
}

impl Display for InferenceAdmissionError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Kernel(error) => Display::fmt(error, formatter),
            Self::RemoteGrantRequired => formatter.write_str("remote inference requires a trusted grant"),
            Self::GrantExpired => formatter.write_str("remote inference grant is expired"),
            Self::GrantPrincipalMismatch => formatter.write_str("remote inference grant principal mismatch"),
            Self::GrantSessionMismatch => formatter.write_str("remote inference grant session mismatch"),
            Self::DestinationNotAllowed => formatter.write_str("remote inference destination is not allowed"),
            Self::SecretHandleMismatch => formatter.write_str("remote inference secret handle is not allowed"),
            Self::InputTokenBudgetExceeded => formatter.write_str("remote inference input-token budget exceeded"),
            Self::OutputTokenBudgetExceeded => formatter.write_str("remote inference output-token budget exceeded"),
            Self::TotalTokenBudgetExceeded => formatter.write_str("remote inference total-token budget exceeded"),
            Self::CostBudgetExceeded => formatter.write_str("remote inference cost budget exceeded"),
            Self::InvalidDestination => formatter.write_str("remote inference destination is invalid"),
            Self::InvalidGrant => formatter.write_str("remote inference grant is invalid"),
        }
    }
}

impl std::error::Error for InferenceAdmissionError {}

impl From<KernelError> for InferenceAdmissionError {
    fn from(value: KernelError) -> Self {
        Self::Kernel(value)
    }
}

pub fn authorize_inference(
    request: &InferenceRequest,
    route: &InferenceRoute,
    grant: Option<&RemoteInferenceGrant>,
    now: SystemTime,
) -> Result<InferenceAdmission, InferenceAdmissionError> {
    validate_request_identity(request)?;
    let config = request
        .config
        .as_ref()
        .ok_or(KernelError::MissingField("inference.config"))?;
    if config.max_output_tokens == 0 {
        return Err(KernelError::EmptyField("inference.config.max_output_tokens").into());
    }

    match route {
        InferenceRoute::Local => {
            let reservation = InferenceBudgetReservation {
                input_tokens: 0,
                output_tokens: config.max_output_tokens,
                total_tokens: config.max_output_tokens,
                cost_microunits: 0,
            };
            Ok(build_admission(
                request,
                InferenceEgressMode::Local,
                None,
                None,
                false,
                reservation,
            ))
        }
        InferenceRoute::Remote {
            destination,
            secret_handle,
            estimated_input_tokens,
            estimated_cost_microunits,
        } => {
            validate_remote_destination(destination)?;
            let grant = grant.ok_or(InferenceAdmissionError::RemoteGrantRequired)?;
            if now >= grant.expires_at {
                return Err(InferenceAdmissionError::GrantExpired);
            }
            let request_principal = request
                .principal
                .as_ref()
                .ok_or(KernelError::MissingField("principal"))?;
            if !same_principal(request_principal, &grant.principal) {
                return Err(InferenceAdmissionError::GrantPrincipalMismatch);
            }
            if request.session_id != grant.session_id {
                return Err(InferenceAdmissionError::GrantSessionMismatch);
            }
            if destination != &grant.destination {
                return Err(InferenceAdmissionError::DestinationNotAllowed);
            }
            if !secret_handle.matches(&grant.secret_handle) {
                return Err(InferenceAdmissionError::SecretHandleMismatch);
            }
            if *estimated_input_tokens > grant.max_input_tokens {
                return Err(InferenceAdmissionError::InputTokenBudgetExceeded);
            }
            if config.max_output_tokens > grant.max_output_tokens {
                return Err(InferenceAdmissionError::OutputTokenBudgetExceeded);
            }
            let total_tokens = estimated_input_tokens.saturating_add(config.max_output_tokens);
            if total_tokens > grant.max_total_tokens {
                return Err(InferenceAdmissionError::TotalTokenBudgetExceeded);
            }
            if *estimated_cost_microunits > grant.max_cost_microunits {
                return Err(InferenceAdmissionError::CostBudgetExceeded);
            }
            let reservation = InferenceBudgetReservation {
                input_tokens: *estimated_input_tokens,
                output_tokens: config.max_output_tokens,
                total_tokens,
                cost_microunits: *estimated_cost_microunits,
            };
            Ok(build_admission(
                request,
                InferenceEgressMode::Remote,
                Some(grant.grant_id.clone()),
                Some(grant.destination.clone()),
                true,
                reservation,
            ))
        }
    }
}

fn validate_request_identity(request: &InferenceRequest) -> Result<(), InferenceAdmissionError> {
    validate_contract_version(request.contract_version.as_ref())?;
    require_text(&request.request_id, "inference.request_id")?;
    require_text(&request.attempt_id, "inference.attempt_id")?;
    validate_principal(request.principal.as_ref())?;
    require_text(&request.session_id, "inference.session_id")?;
    require_text(&request.engine_id, "inference.engine_id")?;
    require_text(&request.model_id, "inference.model_id")?;
    require_text(&request.idempotency_key, "inference.idempotency_key")?;
    Ok(())
}

fn build_admission(
    request: &InferenceRequest,
    mode: InferenceEgressMode,
    grant_id: Option<String>,
    destination: Option<String>,
    secret_handle_used: bool,
    reservation: InferenceBudgetReservation,
) -> InferenceAdmission {
    let principal = request.principal.as_ref().expect("principal validated");
    let audit = InferenceAuditRecord {
        request_id: request.request_id.clone(),
        attempt_id: request.attempt_id.clone(),
        user_id: principal.user_id.clone(),
        session_id: request.session_id.clone(),
        mode,
        grant_id,
        destination,
        secret_handle_used,
        reservation: reservation.clone(),
    };
    InferenceAdmission {
        mode,
        reservation,
        audit,
    }
}

fn same_principal(left: &PrincipalRef, right: &PrincipalRef) -> bool {
    left.user_id == right.user_id
        && left.device_id == right.device_id
        && left.channel_id == right.channel_id
        && left.tenant_id == right.tenant_id
}

fn validate_remote_destination(value: &str) -> Result<(), InferenceAdmissionError> {
    if value.is_empty()
        || value.trim() != value
        || !value.starts_with("https://")
        || value.chars().any(|character| character.is_whitespace() || character.is_control())
        || value.contains('\\')
        || value.contains('@')
        || value.contains('?')
        || value.contains('#')
    {
        return Err(InferenceAdmissionError::InvalidDestination);
    }
    let authority_and_path = &value["https://".len()..];
    let authority = authority_and_path.split('/').next().unwrap_or_default();
    if authority.is_empty() || authority.starts_with('.') || authority.ends_with('.') {
        return Err(InferenceAdmissionError::InvalidDestination);
    }
    Ok(())
}

fn require_text(value: &str, field: &'static str) -> Result<(), KernelError> {
    if value.trim().is_empty() {
        return Err(KernelError::EmptyField(field));
    }
    Ok(())
}
