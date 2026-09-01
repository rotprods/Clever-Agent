use std::collections::BTreeMap;

use clever_contracts::{
    CapabilityAvailability, CapabilityDescriptor, LifecycleMode, PermissionRequirement,
};

use crate::{error::KernelError, version::validate_contract_version};

#[derive(Debug, Clone)]
pub struct CapabilityState {
    pub descriptor: CapabilityDescriptor,
    pub availability: CapabilityAvailability,
}

#[derive(Debug, Default)]
pub struct CapabilityRegistry {
    capabilities: BTreeMap<String, CapabilityState>,
}

impl CapabilityRegistry {
    pub fn register(&mut self, descriptor: CapabilityDescriptor) -> Result<(), KernelError> {
        validate_descriptor(&descriptor)?;
        if self.capabilities.contains_key(&descriptor.capability_id) {
            return Err(KernelError::DuplicateId {
                kind: "capability",
                id: descriptor.capability_id,
            });
        }
        self.capabilities.insert(
            descriptor.capability_id.clone(),
            CapabilityState {
                descriptor,
                availability: CapabilityAvailability::Unavailable,
            },
        );
        Ok(())
    }

    pub fn set_availability(
        &mut self,
        capability_id: &str,
        availability: CapabilityAvailability,
    ) -> Result<(), KernelError> {
        if availability == CapabilityAvailability::Unspecified {
            return Err(KernelError::InvalidEnum {
                field: "capability.availability",
                value: availability as i32,
            });
        }
        let state = self
            .capabilities
            .get_mut(capability_id)
            .ok_or_else(|| KernelError::UnknownCapability(capability_id.to_owned()))?;
        state.availability = availability;
        Ok(())
    }

    #[must_use]
    pub fn get(&self, capability_id: &str) -> Option<&CapabilityState> {
        self.capabilities.get(capability_id)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.capabilities.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.capabilities.is_empty()
    }
}

fn validate_descriptor(descriptor: &CapabilityDescriptor) -> Result<(), KernelError> {
    validate_contract_version(descriptor.contract_version.as_ref())?;
    require_text(&descriptor.capability_id, "capability_id")?;
    require_text(&descriptor.family, "capability.family")?;
    require_text(&descriptor.name, "capability.name")?;
    require_text(
        &descriptor.interface_contract,
        "capability.interface_contract",
    )?;
    require_text(
        &descriptor.interface_version,
        "capability.interface_version",
    )?;
    let owner = descriptor
        .owner
        .as_ref()
        .ok_or(KernelError::MissingField("capability.owner"))?;
    require_text(&owner.runtime_id, "capability.owner.runtime_id")?;
    let lifecycle = LifecycleMode::try_from(descriptor.lifecycle_mode).map_err(|_| {
        KernelError::InvalidEnum {
            field: "capability.lifecycle_mode",
            value: descriptor.lifecycle_mode,
        }
    })?;
    if lifecycle == LifecycleMode::Unspecified {
        return Err(KernelError::InvalidEnum {
            field: "capability.lifecycle_mode",
            value: descriptor.lifecycle_mode,
        });
    }
    for permission in &descriptor.permissions {
        validate_permission(permission)?;
    }
    for key in descriptor.extension_metadata.keys() {
        let normalized = key.to_ascii_lowercase();
        if [
            "permission",
            "scope",
            "risk",
            "policy",
            "authorization",
            "authz",
        ]
        .iter()
        .any(|reserved| normalized.contains(reserved))
        {
            return Err(KernelError::ReservedExtensionKey(key.clone()));
        }
    }
    Ok(())
}

fn validate_permission(permission: &PermissionRequirement) -> Result<(), KernelError> {
    require_text(&permission.permission, "capability.permission.permission")?;
    if permission.mandatory {
        require_text(&permission.scope, "capability.permission.scope")?;
    }
    Ok(())
}

fn require_text(value: &str, field: &'static str) -> Result<(), KernelError> {
    if value.trim().is_empty() {
        return Err(KernelError::EmptyField(field));
    }
    Ok(())
}
