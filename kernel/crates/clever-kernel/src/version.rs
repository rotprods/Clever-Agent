use clever_contracts::ContractVersion;

use crate::error::KernelError;

pub const SUPPORTED_CONTRACT_MAJOR: u32 = 1;

pub fn validate_contract_version(version: Option<&ContractVersion>) -> Result<(), KernelError> {
    let version = version.ok_or(KernelError::MissingField("contract_version"))?;
    if version.major != SUPPORTED_CONTRACT_MAJOR {
        return Err(KernelError::UnsupportedContractMajor(version.major));
    }
    Ok(())
}
