"""Execute RED/GREEN control regressions; absent/ignored required tests fail closed."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
TESTS = {"invalid_snapshot_is_atomic", "conflicting_snapshot_is_atomic", "duplicate_snapshot_keys_are_rejected_atomically", "idempotent_snapshot_preserves_availability", "health_requires_request_correlation", "cancel_requires_request_correlation", "shutdown_requires_request_correlation", "unspecified_health_is_not_accepted", "ready_with_loss_is_rejected", "ready_with_degradation_is_rejected", "negotiated_receive_limit_is_enforced", "empty_response_identity_is_rejected", "timeout_poisons_session_before_late_reply", "protocol_error_requires_reconnect", "valid_control_exchange_remains_compatible"}
CONTROLS = {"idempotent_snapshot_preserves_availability", "valid_control_exchange_remains_compatible"}
SUBJECTS = ["kernel/crates/clever-kernel/src/adapter.rs", "adapters/openjarvis/sidecar.py", "kernel/crates/clever-kernel/tests/adapter_supervisor.rs", "kernel/crates/clever-kernel/tests/control_guards.rs", "kernel/crates/clever-kernel/tests/fixtures/control_guard_peer.py", "kernel/crates/clever-kernel/tests/fixtures/fake_adapter_sidecar.py"]
BASE_BLOBS = {SUBJECTS[0]: "44baaf170c904c9f16d4b430232c6dab2e5ffa76", SUBJECTS[1]: "e0e4229e336f219534c49cad65a25371a683075f", SUBJECTS[2]: "0768fc22dd027f245e366d15ee69e70f4fe79f72"}
OUT = ROOT / ".cache/control-guards"

def parsed_results(text: str, expected: set[str]) -> dict[str, str]:
    if "error[E" in text or "could not compile" in text:
        raise ValueError("compilation failure cannot count as a regression reproduction")
    pairs = re.findall(r"^test ([a-zA-Z0-9_:]+) \.\.\. (ok|FAILED|ignored[^\n]*)$", text, flags=re.M)
    results = {}
    for name, status in pairs:
        if name in results: raise ValueError("duplicate test result")
        results[name] = status
    if set(results) != expected:
        raise ValueError(f"test omission/unexpected case: missing={expected-set(results)}, extra={set(results)-expected}")
    if any(status.startswith("ignored") for status in results.values()): raise ValueError("required test was ignored")
    return results

def command(argv: list[str], label: str, *, env=None, expect: int = 0) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(argv, cwd=ROOT, env=env, text=True, capture_output=True, timeout=240)
    text = result.stdout + "\n" + result.stderr
    if len(text.encode()) > 8 * 1024 * 1024: raise ValueError("test output budget exceeded")
    (OUT / f"{label}.log").write_text(text)
    if (result.returncode == 0) != (expect == 0):
        print(text[-16000:])
        raise ValueError(f"{label}: unexpected exit {result.returncode}")
    return {"command": argv, "exit_code": result.returncode, "log": f"{label}.log", "output": text}

def cargo(*parts: str) -> list[str]:
    return ["cargo", "test", "--locked", "--manifest-path", "kernel/Cargo.toml", *parts]

def run(repair: bool) -> None:
    python = os.environ.get("CLEVER_TEST_PYTHON")
    if not python or not Path(python).is_absolute() or not Path(python).is_file():
        raise ValueError("CLEVER_TEST_PYTHON is required, absolute and executable")
    subprocess.run([python, "-c", "from clever.v1 import adapter_pb2"], check=True, env={**os.environ, "PYTHONPATH": str(ROOT / "contracts/sdk/python/gen")}, timeout=20)
    report = {"scope": "CONTROL_PROTOCOL_NOT_INFERENCE_PARITY", "repair": repair, "input_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "run_id": os.environ.get("GITHUB_RUN_ID"), "steps": [], "status": "IN_PROGRESS"}
    if repair:
        for relative, expected in BASE_BLOBS.items():
            b = (ROOT / relative).read_bytes()
            digest = hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()
            if digest != expected: raise ValueError(f"repair refused: source drift in {relative}")
        command(["rustfmt", "--edition", "2021", SUBJECTS[3]], "format-new-tests")
        red = command(cargo("--test", "control_guards", "--", "--test-threads=1"), "red", expect=1)
        cases = parsed_results(red.pop("output"), TESTS)
        if {name for name, status in cases.items() if status == "FAILED"} != TESTS - CONTROLS:
            raise ValueError("RED phase did not reproduce exactly the anticipated runtime failures")
        report["steps"].append({**red, "cases": cases})
        command([sys.executable, "scripts/cp03/apply_control_guards.py"], "apply-exact-repair")
        command(["cargo", "fmt", "--manifest-path", "kernel/Cargo.toml", "--all"], "format-repair")
    else:
        command(["cargo", "fmt", "--manifest-path", "kernel/Cargo.toml", "--all", "--", "--check"], "format-check")
    green = command(cargo("--test", "control_guards", "--", "--test-threads=1"), "green")
    cases = parsed_results(green.pop("output"), TESTS)
    if set(cases.values()) != {"ok"}: raise ValueError("GREEN cases contain failure")
    report["steps"].append({**green, "cases": cases})
    missing_env = dict(os.environ)
    missing_env.pop("CLEVER_TEST_PYTHON", None)
    negative = command(cargo("--test", "adapter_supervisor", "rejects_unknown_contract_major", "--", "--exact"), "missing-interpreter-negative", env=missing_env, expect=1)
    if "CLEVER_TEST_PYTHON is required" not in negative.pop("output"):
        raise ValueError("negative preflight did not fail for the intended missing prerequisite")
    report["steps"].append(negative)
    for argv, label in [
        (cargo("--workspace", "--all-targets"), "rust-regression"),
        (["cargo", "clippy", "--locked", "--manifest-path", "kernel/Cargo.toml", "--workspace", "--all-targets", "--all-features", "--", "-D", "warnings"], "clippy"),
        ([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_control_guard_gate.py", "-v"], "gate-tests"),
        ([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_cp03_openjarvis_sidecar.py", "-v"], "sidecar-tests"),
    ]:
        result = command(argv, label)
        result.pop("output")
        report["steps"].append(result)
    repeat = command(cargo("--test", "control_guards", "--", "--test-threads=1"), "green-retest")
    repeated = parsed_results(repeat.pop("output"), TESTS)
    if set(repeated.values()) != {"ok"}: raise ValueError("retest failed")
    report["steps"].append({**repeat, "cases": repeated})
    report["subject_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SUBJECTS}
    report["status"] = "PASS"
    report["parity_promotions"] = 0
    report["remaining_gaps"] = ["unbounded aggregate receive queue", "write and teardown deadlines", "actual inference cancellation", "real-model inference", "container cleanup after launcher failure"]
    (OUT / "GATE.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "PASS", "required_control_tests": len(TESTS), "red_cases": len(TESTS-CONTROLS) if repair else None, "real_inference": False}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()
    if args.native:
        name = "real_openjarvis_sidecar_is_supervised_and_bridged_without_promotion"
        result = command(cargo("--test", "adapter_supervisor", name, "--", "--ignored", "--exact"), "native-openjarvis")
        cases = parsed_results(result.pop("output"), {name})
        if set(cases.values()) != {"ok"}: raise ValueError("native test failed")
        (OUT / "NATIVE.json").write_text(json.dumps({"status": "PASS", "scope": "PINNED_NATIVE_REGISTRY_NOT_INFERENCE", "cases": cases, "command": result, "upstream": "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"}, indent=2) + "\n")
    else: run(args.repair)
