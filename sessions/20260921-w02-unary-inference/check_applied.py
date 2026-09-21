from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

checks = {
    "adapters/openjarvis/sidecar.py": [
        "from adapters.openjarvis.unary_inference import UnaryInferenceRejected, execute_unary",
        '"unary-inference"',
        'elif body == "inference_request":',
        "outcome = execute_unary(native_request)",
        '"inference_chunk"',
        '"inference_terminal"',
        '"inference_error"',
    ],
    "kernel/crates/clever-kernel/src/adapter.rs": [
        'const OPTIONAL_FEATURES: [&str; 1] = ["unary-inference"]',
        'const W02_UNARY_ENGINE_ID: &str = "llamacpp"',
        'const W02_UNARY_MODEL_ID: &str = "qwen3:0.6b"',
        "pub struct UnaryInferenceResult",
        "pub fn infer_unary(",
        "authorize_inference_egress",
        "fn validate_inference_outer(",
        "fn validate_inference_chunk(",
        "fn validate_inference_terminal(",
        "fn inference_failure<T>(",
    ],
    "kernel/crates/clever-kernel/tests/adapter_supervisor.rs": [
        "real_openjarvis_unary_inference_uses_pinned_llamacpp_lane",
        "infer_unary",
        '"qwen3:0.6b"',
        '"llamacpp"',
    ],
}

for relative, markers in checks.items():
    text = (ROOT / relative).read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise SystemExit(f"W02-10 source contract incomplete in {relative}: {missing}")

print("W02-10 source contract: PASS")
