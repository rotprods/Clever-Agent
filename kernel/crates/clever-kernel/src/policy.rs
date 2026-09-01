use clever_contracts::{
    ContractVersion, PolicyDecision, PolicyDecisionKind, PolicyEvaluationRequest, RiskClass,
};

use crate::{error::KernelError, identity::validate_principal, version::validate_contract_version};

pub trait PolicyBroker {
    fn evaluate(&self, request: &PolicyEvaluationRequest) -> Result<PolicyDecision, KernelError>;
}

#[derive(Debug, Default, Clone, Copy)]
pub struct DenyByDefaultPolicyBroker;

impl PolicyBroker for DenyByDefaultPolicyBroker {
    fn evaluate(&self, request: &PolicyEvaluationRequest) -> Result<PolicyDecision, KernelError> {
        validate_contract_version(request.contract_version.as_ref())?;
        require_text(&request.evaluation_id, "policy.evaluation_id")?;
        validate_principal(request.principal.as_ref())?;
        require_text(&request.capability_id, "policy.capability_id")?;
        require_text(&request.operation, "policy.operation")?;
        Ok(PolicyDecision {
            contract_version: Some(ContractVersion { major: 1, minor: 0 }),
            decision_id: format!("deny:{}", request.evaluation_id),
            evaluation_id: request.evaluation_id.clone(),
            decision: PolicyDecisionKind::Deny as i32,
            risk_class: RiskClass::R4 as i32,
            granted_scopes: Vec::new(),
            reason_codes: vec!["DENY_BY_DEFAULT".to_owned()],
            user_confirmation_required: false,
            expires_at: None,
            audit_ref: format!("policy:{}", request.evaluation_id),
        })
    }
}

fn require_text(value: &str, field: &'static str) -> Result<(), KernelError> {
    if value.trim().is_empty() {
        return Err(KernelError::EmptyField(field));
    }
    Ok(())
}
