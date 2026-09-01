use std::collections::BTreeMap;

use clever_contracts::{RuntimeHealth, RuntimeHealthStatus};

use crate::{audit::AuditLog, error::KernelError, version::validate_contract_version};

#[derive(Debug, Default)]
pub struct RuntimeHealthTracker {
    health: BTreeMap<String, RuntimeHealth>,
}

impl RuntimeHealthTracker {
    pub fn observe(
        &mut self,
        health: RuntimeHealth,
        audit: &mut AuditLog,
    ) -> Result<(), KernelError> {
        validate_contract_version(health.contract_version.as_ref())?;
        if health.runtime_id.trim().is_empty() {
            return Err(KernelError::EmptyField("runtime.runtime_id"));
        }
        if health.observed_at.is_none() {
            return Err(KernelError::MissingField("runtime.observed_at"));
        }
        let status =
            RuntimeHealthStatus::try_from(health.status).map_err(|_| KernelError::InvalidEnum {
                field: "runtime.status",
                value: health.status,
            })?;
        if status == RuntimeHealthStatus::Unspecified {
            return Err(KernelError::InvalidEnum {
                field: "runtime.status",
                value: health.status,
            });
        }
        if status == RuntimeHealthStatus::Ready
            && (!health.degradation_reasons.is_empty()
                || health.dropped_event_count > 0
                || health.failed_action_count > 0)
        {
            return Err(KernelError::FalseGreenHealth(health.runtime_id));
        }
        if matches!(
            status,
            RuntimeHealthStatus::Degraded | RuntimeHealthStatus::Unavailable
        ) && health.degradation_reasons.is_empty()
        {
            return Err(KernelError::EmptyField("runtime.degradation_reasons"));
        }
        if let Some(previous) = self.health.get(&health.runtime_id) {
            let from = RuntimeHealthStatus::try_from(previous.status).map_err(|_| {
                KernelError::InvalidEnum {
                    field: "runtime.previous_status",
                    value: previous.status,
                }
            })?;
            if !transition_allowed(from, status) {
                return Err(KernelError::InvalidRuntimeTransition {
                    from: from as i32,
                    to: status as i32,
                });
            }
        }
        audit.append(
            format!("runtime.{}", status_name(status)),
            &health.runtime_id,
        );
        self.health.insert(health.runtime_id.clone(), health);
        Ok(())
    }

    #[must_use]
    pub fn get(&self, runtime_id: &str) -> Option<&RuntimeHealth> {
        self.health.get(runtime_id)
    }

    #[must_use]
    pub fn is_ready(&self, runtime_id: &str) -> bool {
        self.health.get(runtime_id).is_some_and(|health| {
            RuntimeHealthStatus::try_from(health.status) == Ok(RuntimeHealthStatus::Ready)
                && health.degradation_reasons.is_empty()
                && health.dropped_event_count == 0
                && health.failed_action_count == 0
        })
    }
}

fn transition_allowed(from: RuntimeHealthStatus, to: RuntimeHealthStatus) -> bool {
    from == to
        || matches!(
            (from, to),
            (RuntimeHealthStatus::Starting, RuntimeHealthStatus::Ready)
                | (RuntimeHealthStatus::Starting, RuntimeHealthStatus::Degraded)
                | (
                    RuntimeHealthStatus::Starting,
                    RuntimeHealthStatus::Unavailable
                )
                | (RuntimeHealthStatus::Starting, RuntimeHealthStatus::Stopping)
                | (RuntimeHealthStatus::Ready, RuntimeHealthStatus::Degraded)
                | (RuntimeHealthStatus::Ready, RuntimeHealthStatus::Unavailable)
                | (RuntimeHealthStatus::Ready, RuntimeHealthStatus::Stopping)
                | (RuntimeHealthStatus::Degraded, RuntimeHealthStatus::Ready)
                | (
                    RuntimeHealthStatus::Degraded,
                    RuntimeHealthStatus::Unavailable
                )
                | (RuntimeHealthStatus::Degraded, RuntimeHealthStatus::Stopping)
                | (
                    RuntimeHealthStatus::Unavailable,
                    RuntimeHealthStatus::Starting
                )
                | (
                    RuntimeHealthStatus::Unavailable,
                    RuntimeHealthStatus::Stopping
                )
        )
}

fn status_name(status: RuntimeHealthStatus) -> &'static str {
    match status {
        RuntimeHealthStatus::Starting => "starting",
        RuntimeHealthStatus::Ready => "ready",
        RuntimeHealthStatus::Degraded => "degraded",
        RuntimeHealthStatus::Unavailable => "unavailable",
        RuntimeHealthStatus::Stopping => "stopping",
        RuntimeHealthStatus::Unspecified => "unspecified",
    }
}
