"""Named control regressions with watchdogs. Not model/provider parity."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

TESTS = [
    "unrelated_health_is_rejected", "unrelated_cancel_is_rejected", "unrelated_shutdown_is_rejected",
    "unspecified_health_is_rejected", "false_green_health_is_rejected", "peer_frame_limit_is_enforced",
    "timeout_prevents_stale_connection_reuse", "protocol_failure_prevents_reuse", "malformed_body_is_rejected",
    "wrong_runtime_is_rejected", "registry_invalid_tail_is_atomic", "registry_duplicate_batch_is_rejected",
    "registry_existing_conflict_is_atomic", "registry_replay_preserves_availability", "valid_control_roundtrip_still_works",
]
RED_TESTS = [t for t in TESTS if t not in {"malformed_body_is_rejected", "wrong_runtime_is_rejected", "registry_replay_preserves_availability", "valid_control_roundtrip_still_works"}]


def preflight(env: dict[str, str]) -> str:
    value = env.get("CLEVER_TEST_PYTHON", "")
    path = Path(value)
    if not value or not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("MANDATORY CLEVER_TEST_PYTHON absolute executable missing")
    subprocess.run([value, "-c", "from google.protobuf import __version__; print(__version__)"], check=True, timeout=10, capture_output=True, env=env)
    return value


def validate_single(name: str, returncode: int, text: str, expected_red: bool = False) -> None:
    outcome = "FAILED" if expected_red else "ok"
    if not re.search(rf"test {re.escape(name)} \.\.\. {outcome}(?:\r?\n|$)", text):
        raise ValueError(f"named test did not execute with expected outcome: {name}")
    count = re.search(r"test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;", text)
    if not count or tuple(map(int, count.groups())) != ((0, 1, 0) if expected_red else (1, 0, 0)):
        raise ValueError("empty, skipped, duplicated or unexpected test receipt")
    if expected_red:
        if returncode != 101 or "panicked at" not in text or "assertion" not in text:
            raise ValueError("RED must be an assertion failure, not infrastructure failure")
    elif returncode != 0:
        raise ValueError("test process failed")


def execute(command, cwd, env, limit=15):
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        output, _ = process.communicate(timeout=limit)
        return process.returncode, output, time.monotonic() - started
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate(timeout=5)
        return 124, output + "\nEXTERNAL_WATCHDOG_TIMEOUT\n", time.monotonic() - started


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=["red", "green"], required=True)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.repeat <= 20:
        raise SystemExit("repeat outside 1..20")
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    preflight(env)
    build = subprocess.run(["cargo", "test", "--locked", "--manifest-path", str(root / "kernel/Cargo.toml"), "--test", "control_regressions", "--no-run", "--message-format=json"], cwd=root, env=env, text=True, capture_output=True, timeout=180)
    (out / "build.stdout.txt").write_text(build.stdout)
    (out / "build.stderr.txt").write_text(build.stderr)
    if build.returncode:
        raise SystemExit("Build failed: not acceptable RED evidence")
    artifacts = [json.loads(line) for line in build.stdout.splitlines() if line.startswith("{")]
    binaries = [item["executable"] for item in artifacts if item.get("reason") == "compiler-artifact" and item.get("target", {}).get("name") == "control_regressions" and item.get("executable")]
    if len(binaries) != 1:
        raise SystemExit("missing or ambiguous Rust test binary")
    binary = binaries[0]
    listed = subprocess.check_output([binary, "--list"], text=True, env=env, timeout=10)
    names = {line.removesuffix(": test") for line in listed.splitlines() if line.endswith(": test")}
    if names != set(TESTS):
        raise SystemExit("required test manifest mismatch")
    chosen = RED_TESTS if args.mode == "red" else TESTS
    records, failures = [], []
    suite = ET.Element("testsuite", name=f"control-{args.mode}")
    for repeat in range(args.repeat):
        for name in chosen:
            code, output, seconds = execute([binary, "--exact", name, "--test-threads=1"], root, env)
            log_name = f"{repeat:02d}-{name}.txt"
            (out / log_name).write_text(output)
            error = None
            try:
                validate_single(name, code, output, args.mode == "red")
            except ValueError as exc:
                error = str(exc)
                failures.append({"test": name, "repeat": repeat, "error": error})
            case = ET.SubElement(suite, "testcase", name=f"{name}[{repeat}]", classname=f"control.{args.mode}", time=f"{seconds:.6f}")
            if error:
                ET.SubElement(case, "failure", message=error)
            records.append({"test_id": name, "repeat": repeat, "result": "EXPECTED_ASSERTION_FAILURE" if args.mode == "red" and not error else ("PASS" if not error else "FAIL"), "returncode": code, "seconds": seconds, "log": log_name, "sha256": hashlib.sha256(output.encode()).hexdigest()})
    for key, value in {"tests": len(records), "failures": len(failures), "errors": 0, "skipped": 0}.items():
        suite.set(key, str(value))
    ET.ElementTree(suite).write(out / "results.junit.xml", encoding="utf-8", xml_declaration=True)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    paths = ["kernel/crates/clever-kernel/src/adapter.rs", "kernel/crates/clever-kernel/src/capabilities.rs", "kernel/crates/clever-kernel/tests/control_regressions.rs", "kernel/crates/clever-kernel/tests/fixtures/control_peer.py"]
    report = {"schema_version": 1, "scope": "CONTROL_REGRESSION_NOT_MODEL_PARITY", "mode": args.mode, "source_sha": source, "test_source_sha": os.getenv("SOURCE_SHA"), "status": "PASS" if not failures else "FAIL", "required_test_count": len(chosen), "executions": len(records), "repeat": args.repeat, "source_hashes": {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}, "records": records, "failures": failures, "parity_promotions": 0}
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ["status", "mode", "executions", "source_sha", "parity_promotions"]}))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
