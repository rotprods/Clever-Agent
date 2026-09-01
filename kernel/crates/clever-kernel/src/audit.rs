use sha2::{Digest, Sha256};

use crate::error::KernelError;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuditEntry {
    pub sequence: u64,
    pub event_type: String,
    pub subject_id: String,
    pub previous_hash: String,
    pub hash: String,
}

#[derive(Debug, Default)]
pub struct AuditLog {
    entries: Vec<AuditEntry>,
}

impl AuditLog {
    pub fn append(
        &mut self,
        event_type: impl Into<String>,
        subject_id: impl Into<String>,
    ) -> &AuditEntry {
        let event_type = event_type.into();
        let subject_id = subject_id.into();
        let sequence = self.entries.len() as u64 + 1;
        let previous_hash = self
            .entries
            .last()
            .map_or_else(String::new, |entry| entry.hash.clone());
        let hash = entry_hash(sequence, &event_type, &subject_id, &previous_hash);
        self.entries.push(AuditEntry {
            sequence,
            event_type,
            subject_id,
            previous_hash,
            hash,
        });
        self.entries.last().expect("entry was just appended")
    }

    pub fn verify(&self) -> Result<(), KernelError> {
        let mut previous_hash = String::new();
        for (index, entry) in self.entries.iter().enumerate() {
            let sequence = index as u64 + 1;
            let expected = entry_hash(
                sequence,
                &entry.event_type,
                &entry.subject_id,
                &previous_hash,
            );
            if entry.sequence != sequence
                || entry.previous_hash != previous_hash
                || entry.hash != expected
            {
                return Err(KernelError::AuditIntegrity { sequence });
            }
            previous_hash.clone_from(&entry.hash);
        }
        Ok(())
    }

    #[must_use]
    pub fn entries(&self) -> &[AuditEntry] {
        &self.entries
    }
}

fn entry_hash(sequence: u64, event_type: &str, subject_id: &str, previous_hash: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(sequence.to_be_bytes());
    update_string(&mut hasher, previous_hash);
    update_string(&mut hasher, event_type);
    update_string(&mut hasher, subject_id);
    let bytes = hasher.finalize();
    let mut encoded = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        use std::fmt::Write;
        write!(&mut encoded, "{byte:02x}").expect("writing to String cannot fail");
    }
    encoded
}

fn update_string(hasher: &mut Sha256, value: &str) {
    hasher.update((value.len() as u64).to_be_bytes());
    hasher.update(value.as_bytes());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tampering_breaks_hash_chain() {
        let mut audit = AuditLog::default();
        audit.append("action.accepted", "act-1");
        audit.append("action.running", "act-1");
        assert!(audit.verify().is_ok());
        audit.entries[0].subject_id = "tampered".to_owned();
        assert_eq!(
            audit.verify(),
            Err(KernelError::AuditIntegrity { sequence: 1 })
        );
    }
}
