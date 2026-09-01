use std::collections::BTreeMap;

use clever_contracts::{
    ActionIntent, ActionReceipt, ActionReceiptStatus, Payload, PolicyDecision, PolicyDecisionKind,
    SideEffectClass,
};
use prost_types::Timestamp;

use crate::{
    audit::AuditLog, error::KernelError, identity::validate_principal,
    policy::validate_policy_decision, version::validate_contract_version,
};

#[derive(Debug, Clone)]
pub struct ActionRecord {
    pub intent: ActionIntent,
    pub receipt: ActionReceipt,
}

#[derive(Debug, Default)]
pub struct ActionStore {
    by_idempotency: BTreeMap<String, ActionRecord>,
    action_to_key: BTreeMap<String, String>,
}

#[derive(Debug, Clone, Default)]
pub struct ReceiptUpdate {
    pub status: ActionReceiptStatus,
    pub result: Option<Payload>,
    pub error_code: String,
    pub error_message: String,
    pub completed_at: Option<Timestamp>,
}

impl ActionStore {
    pub fn accept(
        &mut self,
        intent: ActionIntent,
        decision: &PolicyDecision,
        audit: &mut AuditLog,
    ) -> Result<ActionReceipt, KernelError> {
        validate_intent(&intent)?;
        validate_policy_decision(decision)?;
        if intent.policy_decision_id != decision.decision_id {
            return Err(KernelError::PolicyDenied(
                "policy decision id mismatch".to_owned(),
            ));
        }
        let decision_kind = PolicyDecisionKind::try_from(decision.decision).map_err(|_| {
            KernelError::InvalidEnum {
                field: "policy.decision",
                value: decision.decision,
            }
        })?;
        if decision_kind != PolicyDecisionKind::Allow || decision.user_confirmation_required {
            return Err(KernelError::PolicyDenied(
                "decision is not an unconditional ALLOW".to_owned(),
            ));
        }

        if let Some(existing) = self.by_idempotency.get(&intent.idempotency_key) {
            if existing.intent == intent {
                let mut duplicate = existing.receipt.clone();
                duplicate.status = ActionReceiptStatus::Duplicate as i32;
                duplicate
                    .verification_codes
                    .push("IDEMPOTENT_REPLAY".to_owned());
                audit.append("action.duplicate", &intent.action_id);
                return Ok(duplicate);
            }
            return Err(KernelError::IdempotencyConflict(intent.idempotency_key));
        }
        if self.action_to_key.contains_key(&intent.action_id) {
            return Err(KernelError::DuplicateId {
                kind: "action",
                id: intent.action_id,
            });
        }

        let receipt = ActionReceipt {
            contract_version: intent.contract_version.clone(),
            receipt_id: format!("receipt:{}", intent.action_id),
            action_id: intent.action_id.clone(),
            idempotency_key: intent.idempotency_key.clone(),
            status: ActionReceiptStatus::Accepted as i32,
            attempt: 1,
            started_at: intent.requested_at.clone(),
            completed_at: None,
            result: None,
            verification_codes: Vec::new(),
            error_code: String::new(),
            error_message: String::new(),
            audit_ref: format!("action:{}", intent.action_id),
        };
        self.action_to_key
            .insert(intent.action_id.clone(), intent.idempotency_key.clone());
        self.by_idempotency.insert(
            intent.idempotency_key.clone(),
            ActionRecord {
                intent: intent.clone(),
                receipt: receipt.clone(),
            },
        );
        audit.append("action.accepted", &intent.action_id);
        Ok(receipt)
    }

    pub fn transition(
        &mut self,
        action_id: &str,
        update: ReceiptUpdate,
        audit: &mut AuditLog,
    ) -> Result<ActionReceipt, KernelError> {
        let key = self
            .action_to_key
            .get(action_id)
            .cloned()
            .ok_or_else(|| KernelError::UnknownAction(action_id.to_owned()))?;
        let record = self
            .by_idempotency
            .get_mut(&key)
            .ok_or_else(|| KernelError::UnknownAction(action_id.to_owned()))?;
        let from = ActionReceiptStatus::try_from(record.receipt.status).map_err(|_| {
            KernelError::InvalidEnum {
                field: "action.receipt.status",
                value: record.receipt.status,
            }
        })?;
        let to = update.status;
        if to == ActionReceiptStatus::Unspecified || !transition_allowed(from, to) {
            return Err(KernelError::InvalidActionTransition {
                from: from as i32,
                to: to as i32,
            });
        }
        if is_terminal(to) && update.completed_at.is_none() {
            return Err(KernelError::MissingField("action.receipt.completed_at"));
        }
        if to == ActionReceiptStatus::Failed && update.error_code.trim().is_empty() {
            return Err(KernelError::EmptyField("action.receipt.error_code"));
        }
        record.receipt.status = to as i32;
        record.receipt.result = update.result;
        record.receipt.error_code = update.error_code;
        record.receipt.error_message = update.error_message;
        record.receipt.completed_at = update.completed_at;
        audit.append(format!("action.{}", status_name(to)), action_id);
        Ok(record.receipt.clone())
    }

    #[must_use]
    pub fn get(&self, action_id: &str) -> Option<&ActionRecord> {
        let key = self.action_to_key.get(action_id)?;
        self.by_idempotency.get(key)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.by_idempotency.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.by_idempotency.is_empty()
    }
}

fn validate_intent(intent: &ActionIntent) -> Result<(), KernelError> {
    validate_contract_version(intent.contract_version.as_ref())?;
    require_text(&intent.action_id, "action.action_id")?;
    require_text(&intent.idempotency_key, "action.idempotency_key")?;
    validate_principal(intent.principal.as_ref())?;
    require_text(&intent.capability_id, "action.capability_id")?;
    require_text(&intent.operation, "action.operation")?;
    require_text(&intent.policy_decision_id, "action.policy_decision_id")?;
    if intent.payload.is_none() {
        return Err(KernelError::MissingField("action.payload"));
    }
    if intent.requested_at.is_none() {
        return Err(KernelError::MissingField("action.requested_at"));
    }
    let side_effect = SideEffectClass::try_from(intent.side_effect_class).map_err(|_| {
        KernelError::InvalidEnum {
            field: "action.side_effect_class",
            value: intent.side_effect_class,
        }
    })?;
    if side_effect == SideEffectClass::Unspecified {
        return Err(KernelError::InvalidEnum {
            field: "action.side_effect_class",
            value: intent.side_effect_class,
        });
    }
    Ok(())
}

fn transition_allowed(from: ActionReceiptStatus, to: ActionReceiptStatus) -> bool {
    matches!(
        (from, to),
        (ActionReceiptStatus::Accepted, ActionReceiptStatus::Running)
            | (ActionReceiptStatus::Accepted, ActionReceiptStatus::Denied)
            | (ActionReceiptStatus::Accepted, ActionReceiptStatus::Failed)
            | (ActionReceiptStatus::Running, ActionReceiptStatus::Succeeded)
            | (ActionReceiptStatus::Running, ActionReceiptStatus::Failed)
            | (
                ActionReceiptStatus::Running,
                ActionReceiptStatus::RolledBack
            )
            | (
                ActionReceiptStatus::Succeeded,
                ActionReceiptStatus::RolledBack
            )
    )
}

fn is_terminal(status: ActionReceiptStatus) -> bool {
    matches!(
        status,
        ActionReceiptStatus::Succeeded
            | ActionReceiptStatus::Failed
            | ActionReceiptStatus::Denied
            | ActionReceiptStatus::RolledBack
    )
}

fn status_name(status: ActionReceiptStatus) -> &'static str {
    match status {
        ActionReceiptStatus::Accepted => "accepted",
        ActionReceiptStatus::Running => "running",
        ActionReceiptStatus::Succeeded => "succeeded",
        ActionReceiptStatus::Failed => "failed",
        ActionReceiptStatus::Denied => "denied",
        ActionReceiptStatus::Duplicate => "duplicate",
        ActionReceiptStatus::RolledBack => "rolled_back",
        ActionReceiptStatus::Unspecified => "unspecified",
    }
}

fn require_text(value: &str, field: &'static str) -> Result<(), KernelError> {
    if value.trim().is_empty() {
        return Err(KernelError::EmptyField(field));
    }
    Ok(())
}
