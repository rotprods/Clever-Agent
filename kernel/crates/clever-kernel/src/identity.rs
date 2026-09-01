use clever_contracts::{PrincipalRef, SessionRef};

use crate::{error::KernelError, version::validate_contract_version};

fn require_text(value: &str, field: &'static str) -> Result<(), KernelError> {
    if value.trim().is_empty() {
        return Err(KernelError::EmptyField(field));
    }
    Ok(())
}

pub fn validate_principal(principal: Option<&PrincipalRef>) -> Result<(), KernelError> {
    let principal = principal.ok_or(KernelError::MissingField("principal"))?;
    require_text(&principal.user_id, "principal.user_id")
}

pub fn validate_session(session: &SessionRef) -> Result<(), KernelError> {
    validate_contract_version(session.contract_version.as_ref())?;
    require_text(&session.session_id, "session_id")?;
    validate_principal(session.principal.as_ref())?;
    if session.created_at.is_none() {
        return Err(KernelError::MissingField("session.created_at"));
    }
    Ok(())
}
