use std::collections::BTreeMap;

use clever_contracts::{DataClassification, EventEnvelope};

use crate::{error::KernelError, identity::validate_principal, version::validate_contract_version};

#[derive(Debug, Default)]
pub struct EventRouter {
    events: BTreeMap<String, EventEnvelope>,
}

impl EventRouter {
    pub fn route(&mut self, event: EventEnvelope) -> Result<(), KernelError> {
        validate_contract_version(event.contract_version.as_ref())?;
        require_text(&event.message_id, "message_id")?;
        require_text(&event.correlation_id, "correlation_id")?;
        require_text(&event.causation_id, "causation_id")?;
        require_text(&event.event_type, "event_type")?;
        if event.occurred_at.is_none() {
            return Err(KernelError::MissingField("occurred_at"));
        }
        validate_principal(event.principal.as_ref())?;
        let producer = event
            .producer
            .as_ref()
            .ok_or(KernelError::MissingField("producer"))?;
        require_text(&producer.runtime_id, "producer.runtime_id")?;
        let payload = event
            .payload
            .as_ref()
            .ok_or(KernelError::MissingField("payload"))?;
        require_text(&payload.schema_uri, "payload.schema_uri")?;
        require_text(&payload.content_type, "payload.content_type")?;
        let classification = DataClassification::try_from(event.classification).map_err(|_| {
            KernelError::InvalidEnum {
                field: "classification",
                value: event.classification,
            }
        })?;
        if classification == DataClassification::Unspecified {
            return Err(KernelError::InvalidEnum {
                field: "classification",
                value: event.classification,
            });
        }
        if self.events.contains_key(&event.message_id) {
            return Err(KernelError::DuplicateId {
                kind: "event",
                id: event.message_id,
            });
        }
        self.events.insert(event.message_id.clone(), event);
        Ok(())
    }

    #[must_use]
    pub fn get(&self, message_id: &str) -> Option<&EventEnvelope> {
        self.events.get(message_id)
    }
    #[must_use]
    pub fn len(&self) -> usize {
        self.events.len()
    }
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.events.is_empty()
    }
}

fn require_text(value: &str, field: &'static str) -> Result<(), KernelError> {
    if value.trim().is_empty() {
        return Err(KernelError::EmptyField(field));
    }
    Ok(())
}
