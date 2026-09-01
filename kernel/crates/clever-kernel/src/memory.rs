use clever_contracts::{
    DataClassification, MemoryKind, MemoryRecord, PrincipalRef, RetentionClass,
};

use crate::{error::KernelError, identity::validate_principal, version::validate_contract_version};

pub fn validate_memory(record: &MemoryRecord) -> Result<(), KernelError> {
    validate_contract_version(record.contract_version.as_ref())?;
    require_text(&record.memory_id, "memory.memory_id")?;
    validate_principal(record.owner.as_ref())?;
    require_text(&record.access_scope, "memory.access_scope")?;
    require_text(&record.native_owner_runtime, "memory.native_owner_runtime")?;
    if record.content.is_none() {
        return Err(KernelError::MissingField("memory.content"));
    }
    if record.created_at.is_none() {
        return Err(KernelError::MissingField("memory.created_at"));
    }
    if !record.confidence.is_finite() || !(0.0..=1.0).contains(&record.confidence) {
        return Err(KernelError::InvalidConfidence);
    }
    let kind = MemoryKind::try_from(record.kind).map_err(|_| KernelError::InvalidEnum {
        field: "memory.kind",
        value: record.kind,
    })?;
    if kind == MemoryKind::Unspecified {
        return Err(KernelError::InvalidEnum {
            field: "memory.kind",
            value: record.kind,
        });
    }
    let retention =
        RetentionClass::try_from(record.retention).map_err(|_| KernelError::InvalidEnum {
            field: "memory.retention",
            value: record.retention,
        })?;
    if retention == RetentionClass::Unspecified {
        return Err(KernelError::InvalidEnum {
            field: "memory.retention",
            value: record.retention,
        });
    }
    let classification = DataClassification::try_from(record.classification).map_err(|_| {
        KernelError::InvalidEnum {
            field: "memory.classification",
            value: record.classification,
        }
    })?;
    if classification == DataClassification::Unspecified {
        return Err(KernelError::InvalidEnum {
            field: "memory.classification",
            value: record.classification,
        });
    }
    Ok(())
}

pub fn authorize_owner_read(
    record: &MemoryRecord,
    principal: &PrincipalRef,
) -> Result<(), KernelError> {
    validate_memory(record)?;
    validate_principal(Some(principal))?;
    let owner = record
        .owner
        .as_ref()
        .ok_or(KernelError::MissingField("memory.owner"))?;
    let expected_scope = format!("user:{}", owner.user_id);
    if principal.user_id != owner.user_id || record.access_scope != expected_scope {
        return Err(KernelError::MemoryAccessDenied {
            memory_id: record.memory_id.clone(),
            user_id: principal.user_id.clone(),
        });
    }
    Ok(())
}

fn require_text(value: &str, field: &'static str) -> Result<(), KernelError> {
    if value.trim().is_empty() {
        return Err(KernelError::EmptyField(field));
    }
    Ok(())
}
