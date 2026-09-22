from __future__ import annotations

import argparse
from pathlib import Path

# The first workflow phase persists the verified runtime patch with GITHUB_TOKEN.
# GitHub intentionally does not recursively trigger workflows from that bot push,
# so this no-semantic-change revision explicitly starts the exact-head finalize phase.
ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "kernel/crates/clever-kernel/src/adapter.rs"
TEST = ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs"

RED_NAME = "standalone_cancel_without_authority_context_must_fail_closed"
GREEN_NAME = "standalone_cancel_rejects_cross_principal_before_transport"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def transform_region(text: str, start: str, end: str, transform, label: str) -> str:
    start_i = text.find(start)
    if start_i < 0:
        raise RuntimeError(f"{label}: start anchor missing")
    end_i = text.find(end, start_i)
    if end_i < 0:
        raise RuntimeError(f"{label}: end anchor missing")
    region = text[start_i:end_i]
    changed = transform(region)
    if changed == region:
        raise RuntimeError(f"{label}: transform produced no change")
    return text[:start_i] + changed + text[end_i:]


RED_BLOCK = r'''
#[test]
fn standalone_cancel_without_authority_context_must_fail_closed() {
    let command = fake_command("stream-cancel-after-terminal");
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())
        .expect("connect after-terminal fake sidecar");
    let request = fake_stream_request();
    let request_id = request.request_id.clone();
    let attempt_id = request.attempt_id.clone();
    supervisor
        .infer_stream(request)
        .expect("stream reaches terminal before standalone cancellation");

    let outcome = supervisor.cancel_inference(
        request_id,
        attempt_id,
        "standalone cancellation with no caller authority context",
    );
    assert!(
        matches!(outcome, Err(AdapterSupervisorError::InvalidInferenceRequest(_))),
        "standalone cancellation without authority unexpectedly reached transport: {outcome:?}"
    );
}

'''

GREEN_BLOCK = r'''
#[test]
fn standalone_cancel_rejects_cross_principal_before_transport() {
    let command = fake_command("stream-cancel-after-terminal");
    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())
        .expect("connect after-terminal fake sidecar");
    let request = fake_stream_request();
    let request_id = request.request_id.clone();
    let attempt_id = request.attempt_id.clone();
    let owner = request.principal.clone().expect("stream request principal");
    let session_id = request.session_id.clone();
    supervisor
        .infer_stream(request)
        .expect("stream reaches terminal before standalone cancellation");

    let mut attacker = owner.clone();
    attacker.user_id = "cross-principal-attacker".to_owned();
    attacker.tenant_id = "other-tenant".to_owned();
    let error = supervisor
        .cancel_inference(
            &attacker,
            &session_id,
            request_id.clone(),
            attempt_id.clone(),
            "unauthorized cross-principal cancellation",
        )
        .expect_err("cross-principal cancellation must fail before transport");
    assert!(matches!(
        error,
        AdapterSupervisorError::InvalidInferenceRequest(message)
            if message.contains("cancellation authority mismatch")
    ));
    assert!(!supervisor.is_poisoned());

    // The fake peer expects exactly one post-terminal cancel. If the rejected
    // attacker request had crossed the kernel boundary, this owner request
    // could not receive the expected typed ALREADY_TERMINAL response.
    let outcome = supervisor
        .cancel_inference(
            &owner,
            &session_id,
            request_id,
            attempt_id,
            "authorized owner cancellation after terminal",
        )
        .expect("owner cancellation reaches canonical transport");
    assert_eq!(outcome, InferenceCancelOutcome::AlreadyTerminal);
    assert!(!supervisor.is_poisoned());
}

'''


def add_red_test() -> None:
    test = TEST.read_text(encoding="utf-8")
    if RED_NAME in test or GREEN_NAME in test:
        return
    anchor = "#[test]\nfn real_openjarvis_unary_inference_uses_pinned_llamacpp_lane()"
    if anchor not in test:
        raise RuntimeError("real-model test anchor missing")
    test = test.replace(anchor, RED_BLOCK + anchor, 1)
    TEST.write_text(test, encoding="utf-8")


def apply_fix() -> None:
    adapter = ADAPTER.read_text(encoding="utf-8")
    test = TEST.read_text(encoding="utf-8")

    if GREEN_NAME in test and "last_inference_authority: Option<InferenceAuthority>" in adapter:
        return
    if RED_NAME not in test:
        raise RuntimeError("RED characterization test must exist before applying fix")

    adapter = replace_once(
        adapter,
        "    InferenceUsageMeasurement, LifecycleMode, NativeRegistryEntry, PlatformConstraint,\n",
        "    InferenceUsageMeasurement, LifecycleMode, NativeRegistryEntry, PlatformConstraint,\n    PrincipalRef,\n",
        "PrincipalRef import",
    )

    authority_anchor = '''#[derive(Debug, Clone, Copy, PartialEq, Eq)]\npub enum InferenceCancelOutcome {\n    Acknowledged,\n    AlreadyTerminal,\n}\n\n'''
    authority_block = authority_anchor + '''#[derive(Debug, Clone, PartialEq)]\nstruct InferenceAuthority {\n    request_id: String,\n    attempt_id: String,\n    principal: PrincipalRef,\n    session_id: String,\n}\n\n'''
    adapter = replace_once(adapter, authority_anchor, authority_block, "inference authority type")

    adapter = replace_once(
        adapter,
        "    cleanup: Option<AdapterCleanupCommand>,\n    termination_complete: bool,\n",
        "    cleanup: Option<AdapterCleanupCommand>,\n    termination_complete: bool,\n    last_inference_authority: Option<InferenceAuthority>,\n",
        "supervisor authority field",
    )
    adapter = replace_once(
        adapter,
        "            cleanup,\n            termination_complete: false,\n",
        "            cleanup,\n            termination_complete: false,\n            last_inference_authority: None,\n",
        "supervisor authority initialization",
    )

    methods = r'''    fn record_inference_authority(
        &mut self,
        request: &InferenceRequest,
    ) -> Result<(), AdapterSupervisorError> {
        let principal = request.principal.clone().ok_or_else(|| {
            AdapterSupervisorError::InvalidInferenceRequest(
                "inference principal is required for cancellation authority".to_owned(),
            )
        })?;
        if principal.user_id.trim().is_empty() || request.session_id.trim().is_empty() {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "inference user_id and session_id are required for cancellation authority"
                    .to_owned(),
            ));
        }
        self.last_inference_authority = Some(InferenceAuthority {
            request_id: request.request_id.clone(),
            attempt_id: request.attempt_id.clone(),
            principal,
            session_id: request.session_id.clone(),
        });
        Ok(())
    }

    fn validate_inference_cancel_authority(
        &self,
        target_request_id: &str,
        target_attempt_id: &str,
        caller_principal: &PrincipalRef,
        caller_session_id: &str,
    ) -> Result<(), AdapterSupervisorError> {
        if caller_principal.user_id.trim().is_empty() || caller_session_id.trim().is_empty() {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "cancellation caller principal/session must be non-empty".to_owned(),
            ));
        }
        let Some(authority) = self.last_inference_authority.as_ref() else {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "cancellation authority mismatch: no supervised inference ownership record"
                    .to_owned(),
            ));
        };
        if authority.request_id != target_request_id
            || authority.attempt_id != target_attempt_id
            || authority.principal != *caller_principal
            || authority.session_id != caller_session_id
        {
            return Err(AdapterSupervisorError::InvalidInferenceRequest(
                "cancellation authority mismatch for request/attempt/principal/session"
                    .to_owned(),
            ));
        }
        Ok(())
    }

'''
    adapter = replace_once(
        adapter,
        "    fn send_inference_cancel_frame(\n",
        methods + "    fn send_inference_cancel_frame(\n",
        "cancellation authority methods",
    )

    def patch_stream_attempt(region: str) -> str:
        anchor = '''        let frame = self.next_control_frame(\n            adapter_frame::Body::InferenceRequest(request.clone()),\n            self.policy.request_timeout,\n        );\n'''
        insert = '''        if let Err(error) = self.record_inference_authority(&request) {\n            return Err(Self::streaming_attempt_failure(error, false, 0));\n        }\n\n''' + anchor
        return replace_once(region, anchor, insert, "stream authority record")

    adapter = transform_region(
        adapter,
        "    fn infer_stream_attempt(\n",
        "    fn streaming_attempt_failure(\n",
        patch_stream_attempt,
        "infer_stream_attempt",
    )

    def patch_cancellation_lane(region: str) -> str:
        anchor = '''        let frame = self.next_control_frame(\n            adapter_frame::Body::InferenceRequest(request.clone()),\n            self.policy.request_timeout,\n        );\n'''
        insert = '''        self.record_inference_authority(&request)?;\n\n''' + anchor
        return replace_once(region, anchor, insert, "cancellation-lane authority record")

    adapter = transform_region(
        adapter,
        "    pub fn infer_stream_with_cancellation(\n",
        "    fn validate_cancelled_terminal(\n",
        patch_cancellation_lane,
        "infer_stream_with_cancellation",
    )

    old_signature = '''    pub fn cancel_inference(\n        &mut self,\n        target_request_id: impl Into<String>,\n        target_attempt_id: impl Into<String>,\n        reason: impl Into<String>,\n    ) -> Result<InferenceCancelOutcome, AdapterSupervisorError> {\n'''
    new_signature = '''    pub fn cancel_inference(\n        &mut self,\n        caller_principal: &PrincipalRef,\n        caller_session_id: &str,\n        target_request_id: impl Into<String>,\n        target_attempt_id: impl Into<String>,\n        reason: impl Into<String>,\n    ) -> Result<InferenceCancelOutcome, AdapterSupervisorError> {\n'''
    adapter = replace_once(adapter, old_signature, new_signature, "authorized cancel signature")

    def patch_cancel_body(region: str) -> str:
        anchor = '''        let request_id = target_request_id.into();\n        let attempt_id = target_attempt_id.into();\n        let reason = reason.into();\n'''
        insert = anchor + '''        self.validate_inference_cancel_authority(\n            &request_id,\n            &attempt_id,\n            caller_principal,\n            caller_session_id,\n        )?;\n'''
        return replace_once(region, anchor, insert, "cancel authority check")

    adapter = transform_region(
        adapter,
        "    pub fn cancel_inference(\n",
        "    pub fn infer_stream_with_cancellation(\n",
        patch_cancel_body,
        "cancel_inference",
    )

    old_existing = '''    let request_id = request.request_id.clone();\n    let attempt_id = request.attempt_id.clone();\n    let result = supervisor\n        .infer_stream(request)\n        .expect("stream reaches terminal before cancellation");\n'''
    new_existing = '''    let request_id = request.request_id.clone();\n    let attempt_id = request.attempt_id.clone();\n    let caller_principal = request.principal.clone().expect("stream request principal");\n    let caller_session_id = request.session_id.clone();\n    let result = supervisor\n        .infer_stream(request)\n        .expect("stream reaches terminal before cancellation");\n'''
    test = replace_once(test, old_existing, new_existing, "after-terminal owner capture")
    old_call = '''    let outcome = supervisor\n        .cancel_inference(request_id, attempt_id, "too late")\n        .expect("already-terminal cancellation response is a typed non-success outcome");\n'''
    new_call = '''    let outcome = supervisor\n        .cancel_inference(\n            &caller_principal,\n            &caller_session_id,\n            request_id,\n            attempt_id,\n            "too late",\n        )\n        .expect("already-terminal cancellation response is a typed non-success outcome");\n'''
    test = replace_once(test, old_call, new_call, "after-terminal authorized cancel")
    test = transform_region(
        test,
        "#[test]\nfn standalone_cancel_without_authority_context_must_fail_closed()",
        "#[test]\nfn real_openjarvis_unary_inference_uses_pinned_llamacpp_lane()",
        lambda _region: GREEN_BLOCK,
        "rustfmt-stable RED to GREEN security test",
    )

    ADAPTER.write_text(adapter, encoding="utf-8")
    TEST.write_text(test, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--red", action="store_true")
    mode.add_argument("--fix", action="store_true")
    args = parser.parse_args()
    if args.red:
        add_red_test()
    else:
        apply_fix()


if __name__ == "__main__":
    main()
