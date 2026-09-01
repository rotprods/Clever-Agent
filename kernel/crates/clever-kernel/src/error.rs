use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum KernelError {
    MissingField(&'static str),
    EmptyField(&'static str),
    UnsupportedContractMajor(u32),
    InvalidEnum { field: &'static str, value: i32 },
    DuplicateId { kind: &'static str, id: String },
    UnknownCapability(String),
    ReservedExtensionKey(String),
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
            Self::ReservedExtensionKey(key) => {
                write!(
                    formatter,
                    "extension metadata key is security-reserved: {key}"
                )
            }
        }
    }
}

impl std::error::Error for KernelError {}
