use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum KernelError {
    MissingField(&'static str),
    EmptyField(&'static str),
    UnsupportedContractMajor(u32),
    InvalidEnum { field: &'static str, value: i32 },
    DuplicateId { kind: &'static str, id: String },
    UnknownCapability(String),
    UnknownAction(String),
    ReservedExtensionKey(String),
    IdempotencyConflict(String),
    PolicyDenied(String),
    InvalidActionTransition { from: i32, to: i32 },
    FalseGreenHealth(String),
    InvalidRuntimeTransition { from: i32, to: i32 },
    AuditIntegrity { sequence: u64 },
}

impl Display for KernelError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MissingField(field) => write!(formatter, "missing required field: {field}"),
            Self::EmptyField(field) => write!(formatter, "required field is empty: {field}"),
            Self::UnsupportedContractMajor(major) => {
                write!(
                    formatter,
                    "unsupported Clever contract major version: {major}"
                )
            }
            Self::InvalidEnum { field, value } => {
                write!(formatter, "invalid enum value {value} for {field}")
            }
            Self::DuplicateId { kind, id } => write!(formatter, "duplicate {kind} id: {id}"),
            Self::UnknownCapability(id) => write!(formatter, "unknown capability: {id}"),
            Self::UnknownAction(id) => write!(formatter, "unknown action: {id}"),
            Self::ReservedExtensionKey(key) => {
                write!(
                    formatter,
                    "extension metadata key is security-reserved: {key}"
                )
            }
            Self::IdempotencyConflict(key) => {
                write!(
                    formatter,
                    "idempotency key conflicts with prior action: {key}"
                )
            }
            Self::PolicyDenied(reason) => {
                write!(formatter, "policy did not authorize action: {reason}")
            }
            Self::InvalidActionTransition { from, to } => {
                write!(
                    formatter,
                    "invalid action receipt transition: {from} -> {to}"
                )
            }
            Self::FalseGreenHealth(runtime) => {
                write!(
                    formatter,
                    "runtime reported false-green READY health: {runtime}"
                )
            }
            Self::InvalidRuntimeTransition { from, to } => {
                write!(
                    formatter,
                    "invalid runtime health transition: {from} -> {to}"
                )
            }
            Self::AuditIntegrity { sequence } => {
                write!(
                    formatter,
                    "audit hash-chain integrity failure at sequence {sequence}"
                )
            }
        }
    }
}

impl std::error::Error for KernelError {}
