"""Exact-source repair recipe; not loaded by the application. Reject fuzzy edits."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def replace(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise RuntimeError(f"source drift: expected exactly one occurrence of {before[:100]!r}")
    return text.replace(before, after, 1)

def apply() -> None:
    path = ROOT / "kernel/crates/clever-kernel/src/adapter.rs"
    s = path.read_text()
    s = replace(s, "    receiver: Receiver<Result<AdapterFrame, AdapterSupervisorError>>,", "    receiver: Receiver<Result<(AdapterFrame, usize), AdapterSupervisorError>>,")
    s = replace(s, ") -> Result<Option<AdapterFrame>, AdapterSupervisorError> {", ") -> Result<Option<(AdapterFrame, usize)>, AdapterSupervisorError> {")
    s = replace(s, "    Ok(Some(frame))", "    Ok(Some((frame, length)))")
    s = replace(s, "    next_frame_sequence: u64,\n}", "    next_frame_sequence: u64,\n    protocol_failed: bool,\n}")
    s = replace(s, "            next_frame_sequence: 0,", "            next_frame_sequence: 0,\n            protocol_failed: false,")
    s = replace(s,
        '    fn write_frame(&mut self, frame: &AdapterFrame) -> Result<(), AdapterSupervisorError> {\n',
        '    fn write_frame(&mut self, frame: &AdapterFrame) -> Result<(), AdapterSupervisorError> {\n'
        '        if self.protocol_failed {\n'
        '            return Err(AdapterSupervisorError::InvalidRuntimeResponse(\n'
        '                "protocol session is unusable; reconnect before retry".to_owned(),\n'
        '            ));\n'
        '        }\n')
    start = s.index("    fn receive_frame(\n")
    end = s.index("    fn extract_health(\n", start)
    s = s[:start] + '''    fn receive_frame(
        &mut self,
        timeout: Duration,
        stage: &'static str,
    ) -> Result<AdapterFrame, AdapterSupervisorError> {
        let result = match self.receiver.recv_timeout(timeout) {
            Ok(result) => result.and_then(|(frame, wire_length)| {
                // The wire size includes unknown fields discarded by decoding.
                if wire_length > self.negotiated_max_frame_bytes {
                    return Err(AdapterSupervisorError::FrameTooLarge(wire_length));
                }
                if frame.frame_id.trim().is_empty() || frame.body.is_none() {
                    return Err(AdapterSupervisorError::UnexpectedFrame(stage));
                }
                Ok(frame)
            }),
            Err(RecvTimeoutError::Timeout) => Err(AdapterSupervisorError::Timeout(stage)),
            Err(RecvTimeoutError::Disconnected) => Err(AdapterSupervisorError::ProcessExited),
        };
        if result.is_err() {
            self.protocol_failed = true;
        }
        result
    }

    fn receive_response(
        &mut self,
        timeout: Duration,
        stage: &'static str,
        request_id: &str,
    ) -> Result<AdapterFrame, AdapterSupervisorError> {
        let response = self.receive_frame(timeout, stage)?;
        if response.correlation_id != request_id {
            self.protocol_failed = true;
            return Err(AdapterSupervisorError::InvalidRuntimeResponse(
                "response correlation_id does not match request frame_id".to_owned(),
            ));
        }
        Ok(response)
    }

''' + s[end:]
    for stage in ("registry snapshot", "health request", "cancel", "shutdown"):
        s = replace(s, f'self.receive_frame(self.policy.request_timeout, "{stage}")?', f'self.receive_response(self.policy.request_timeout, "{stage}", &request.frame_id)?')
    start = s.index("    fn extract_health(\n")
    end = s.index("\n}\n\nimpl Drop", start)
    s = s[:start] + '''    fn extract_health(
        &mut self,
        response: AdapterFrame,
        stage: &'static str,
    ) -> Result<RuntimeHealth, AdapterSupervisorError> {
        let result = (|| {
            let health = match response.body {
                Some(adapter_frame::Body::Health(health)) => health,
                _ => return Err(AdapterSupervisorError::UnexpectedFrame(stage)),
            };
            validate_contract_version(health.contract_version.as_ref())?;
            if health.runtime_id != self.identity.runtime_id {
                return Err(AdapterSupervisorError::InvalidRuntimeResponse(
                    "health runtime identity mismatch".to_owned(),
                ));
            }
            let status = RuntimeHealthStatus::try_from(health.status).map_err(|_| {
                AdapterSupervisorError::InvalidRuntimeResponse(
                    "invalid health status".to_owned(),
                )
            })?;
            if status == RuntimeHealthStatus::Unspecified {
                return Err(AdapterSupervisorError::InvalidRuntimeResponse(
                    "health status is unspecified".to_owned(),
                ));
            }
            if status == RuntimeHealthStatus::Ready
                && (!health.degradation_reasons.is_empty()
                    || health.dropped_event_count != 0
                    || health.failed_action_count != 0)
            {
                return Err(AdapterSupervisorError::InvalidRuntimeResponse(
                    "READY contradicts loss, failure or degradation evidence".to_owned(),
                ));
            }
            Ok(health)
        })();
        if result.is_err() {
            self.protocol_failed = true;
        }
        result
    }''' + s[end:]
    start = s.index("    let mut capability_ids = Vec::with_capacity(snapshot.entries.len());")
    end = s.index("\nfn descriptor_from_registry_entry(\n", start)
    s = s[:start] + '''    let mut validation_registry = CapabilityRegistry::default();
    let mut descriptors = Vec::with_capacity(snapshot.entries.len());
    let mut capability_ids = Vec::with_capacity(snapshot.entries.len());
    for entry in &snapshot.entries {
        let descriptor = descriptor_from_registry_entry(
            entry,
            runtime_id,
            adapter_id,
            source_repo,
            source_commit,
        )?;
        // Includes duplicate IDs within the snapshot, even identical duplicates.
        validation_registry.register(descriptor.clone())?;
        if let Some(existing) = registry.get(&descriptor.capability_id) {
            if existing.descriptor != descriptor {
                return Err(AdapterSupervisorError::Kernel(KernelError::DuplicateId {
                    kind: "capability",
                    id: descriptor.capability_id,
                }));
            }
        }
        capability_ids.push(descriptor.capability_id.clone());
        descriptors.push(descriptor);
    }
    // Exclusive &mut ownership prevents intervening mutation. All inserts were
    // validated above with the same validator; existing availability is preserved.
    for descriptor in descriptors {
        if registry.get(&descriptor.capability_id).is_none() {
            registry.register(descriptor)?;
        }
    }
    Ok(capability_ids)
}
''' + s[end:]
    path.write_text(s)
    path = ROOT / "adapters/openjarvis/sidecar.py"
    s = path.read_text()
    s = replace(s, 'def health_frame(*, degraded: bool = False, reasons: Iterable[str] = ()) -> adapter_pb2.AdapterFrame:', 'def health_frame(*, degraded: bool = False, reasons: Iterable[str] = (), correlation_id: str = "") -> adapter_pb2.AdapterFrame:')
    s = replace(s, '    return _frame("openjarvis-health", "health", health)', '    response = _frame(f"health:{correlation_id}", "health", health)\n    response.correlation_id = correlation_id\n    return response')
    s = replace(s, '            write_frame(stdout, health_frame(reasons=diagnostics["unsupported_registries"]))', '            write_frame(stdout, health_frame(reasons=diagnostics["unsupported_registries"], correlation_id=request.frame_id))')
    s = replace(s, '            write_frame(stdout, health_frame())', '            write_frame(stdout, health_frame(correlation_id=request.frame_id))')
    s = replace(s, '            write_frame(stdout, _frame("openjarvis-stopping", "health", stopping))', '            response = _frame(f"shutdown:{request.frame_id}", "health", stopping)\n            response.correlation_id = request.frame_id\n            write_frame(stdout, response)')
    s = replace(s, '            write_frame(stdout, _frame(f"error:{request.frame_id}", "error", error))', '            response = _frame(f"error:{request.frame_id}", "error", error)\n            response.correlation_id = request.frame_id\n            write_frame(stdout, response)')
    path.write_text(s)
    path = ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs"
    s = path.read_text()
    s = replace(s, '    let python = env::var("CLEVER_TEST_PYTHON").ok()?;', '    let python = env::var("CLEVER_TEST_PYTHON")\n        .expect("CLEVER_TEST_PYTHON is required for supervisor protocol tests");')
    s = replace(s, '#[test]\nfn real_openjarvis_sidecar_is_supervised_and_bridged_without_promotion()', '#[test]\n#[ignore = "requires the explicit pinned OpenJarvis container lane"]\nfn real_openjarvis_sidecar_is_supervised_and_bridged_without_promotion()')
    s = replace(s, '    ) else {\n        return;\n    };\n\n    let mount =', '    ) else {\n        panic!("real OpenJarvis lane requires image, workspace and Docker binary");\n    };\n\n    let mount =')
    path.write_text(s)

if __name__ == "__main__": apply()
