from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from typing import Any, Callable

REPETITIONS = 20
SEED_BASE = 2026092200
TASK = "W02-16"
SUITE_VERSION = 1

PROBES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "cancel",
        (
            "cargo",
            "test",
            "--locked",
            "--manifest-path",
            "kernel/Cargo.toml",
            "-p",
            "clever-kernel",
            "--test",
            "adapter_supervisor",
            "cancellation_",
            "--",
            "--nocapture",
        ),
    ),
    (
        "frame_flood",
        (
            "cargo",
            "test",
            "--locked",
            "--manifest-path",
            "kernel/Cargo.toml",
            "-p",
            "clever-kernel",
            "--test",
            "adapter_supervisor",
            "inbound_frame_queue_is_bounded_under_flood",
            "--",
            "--exact",
            "--nocapture",
        ),
    ),
    (
        "byte_flood",
        (
            "cargo",
            "test",
            "--locked",
            "--manifest-path",
            "kernel/Cargo.toml",
            "-p",
            "clever-kernel",
            "--test",
            "adapter_supervisor",
            "inbound_wire_byte_budget_is_enforced_before_decode",
            "--",
            "--exact",
            "--nocapture",
        ),
    ),
    (
        "restart",
        (
            "cargo",
            "test",
            "--locked",
            "--manifest-path",
            "kernel/Cargo.toml",
            "-p",
            "clever-kernel",
            "--test",
            "adapter_supervisor",
            "crash_restart_budget_is_bounded",
            "--",
            "--exact",
            "--nocapture",
        ),
    ),
)

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def plan_digest() -> str:
    payload = {
        "repetitions": REPETITIONS,
        "seed_base": SEED_BASE,
        "probes": [{"name": name, "command": list(command)} for name, command in PROBES],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256(encoded)


def run_suite(*, runner: Runner = subprocess.run) -> dict[str, Any]:
    source_head = os.environ.get("GITHUB_SHA", "UNKNOWN")
    python = os.environ.get("CLEVER_TEST_PYTHON", "")
    if not python:
        raise RuntimeError("CLEVER_TEST_PYTHON must point to the exact Python used by fake sidecars")

    rows: list[dict[str, Any]] = []
    for repetition in range(1, REPETITIONS + 1):
        seed = SEED_BASE + repetition
        for probe_name, command in PROBES:
            env = os.environ.copy()
            env["CLEVER_W02_RETEST_SEED"] = str(seed)
            started = time.monotonic_ns()
            completed = runner(
                list(command),
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            elapsed_ms = round((time.monotonic_ns() - started) / 1_000_000, 3)
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            rows.append(
                {
                    "repetition": repetition,
                    "seed": seed,
                    "probe": probe_name,
                    "command": list(command),
                    "exit_code": int(completed.returncode),
                    "duration_ms": elapsed_ms,
                    "stdout_sha256": _sha256(stdout),
                    "stderr_sha256": _sha256(stderr),
                    "stdout_tail": stdout[-2000:],
                    "stderr_tail": stderr[-2000:],
                }
            )

    failures = [row for row in rows if row["exit_code"] != 0]
    report: dict[str, Any] = {
        "schema_version": SUITE_VERSION,
        "task": TASK,
        "gate": "G5",
        "source_head": source_head,
        "suite": "P02_REPEATED_RECOVERY",
        "suite_plan_sha256": plan_digest(),
        "repetitions_required": REPETITIONS,
        "repetitions_executed": REPETITIONS,
        "seed_base": SEED_BASE,
        "seeds": [SEED_BASE + index for index in range(1, REPETITIONS + 1)],
        "probe_names": [name for name, _ in PROBES],
        "invocations_expected": REPETITIONS * len(PROBES),
        "invocations_executed": len(rows),
        "failed_invocations": len(failures),
        "all_results_retained": True,
        "best_rerun_selection": False,
        "performance_baseline_same_host": "NOT_RUN",
        "performance_claims": 0,
        "provider_egress_executions": 0,
        "model_executions": 0,
        "tool_executions": 0,
        "parity_promotions": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "results": rows,
        "result": "PASS" if not failures else "FAIL",
    }
    validate_report(report, require_pass=False)
    return report


def validate_report(report: dict[str, Any], *, require_pass: bool = True) -> None:
    if report.get("schema_version") != SUITE_VERSION or report.get("task") != TASK:
        raise ValueError("unexpected recovery report identity")
    if report.get("suite") != "P02_REPEATED_RECOVERY" or report.get("gate") != "G5":
        raise ValueError("unexpected recovery suite/gate")
    if report.get("suite_plan_sha256") != plan_digest():
        raise ValueError("recovery plan digest drift")
    if report.get("repetitions_required") != REPETITIONS or report.get("repetitions_executed") != REPETITIONS:
        raise ValueError("exactly 20 repetitions are required")
    expected_seeds = [SEED_BASE + index for index in range(1, REPETITIONS + 1)]
    if report.get("seeds") != expected_seeds or len(set(expected_seeds)) != REPETITIONS:
        raise ValueError("repetition seeds are missing, reordered, or duplicated")
    expected_invocations = REPETITIONS * len(PROBES)
    rows = report.get("results")
    if not isinstance(rows, list) or len(rows) != expected_invocations:
        raise ValueError("all cancel/flood/restart invocation records must be retained")
    if report.get("invocations_expected") != expected_invocations or report.get("invocations_executed") != expected_invocations:
        raise ValueError("recovery invocation count drift")
    expected_pairs = {
        (repetition, name)
        for repetition in range(1, REPETITIONS + 1)
        for name, _ in PROBES
    }
    observed_pairs = {(row.get("repetition"), row.get("probe")) for row in rows}
    if observed_pairs != expected_pairs:
        raise ValueError("missing or duplicate recovery probe/repetition records")
    if report.get("all_results_retained") is not True or report.get("best_rerun_selection") is not False:
        raise ValueError("rerun cherry-picking is forbidden")
    failures = [row for row in rows if row.get("exit_code") != 0]
    if report.get("failed_invocations") != len(failures):
        raise ValueError("failure count mismatch")
    if report.get("performance_baseline_same_host") != "NOT_RUN" or report.get("performance_claims") != 0:
        raise ValueError("P02 evidence must not fabricate the unexecuted P01 performance baseline")
    for field in ("provider_egress_executions", "model_executions", "tool_executions", "parity_promotions"):
        if report.get(field) != 0:
            raise ValueError(f"unexpected side effect in recovery-only suite: {field}")
    if report.get("global_denominator") != 7565 or report.get("openjarvis_obligations") != 646:
        raise ValueError("denominator/obligation drift")
    expected_result = "PASS" if not failures else "FAIL"
    if report.get("result") != expected_result:
        raise ValueError("report result does not match retained failures")
    if require_pass and failures:
        raise ValueError(f"recovery suite contains {len(failures)} failing invocation(s)")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--out", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--report", required=True)
    args = parser.parse_args()

    if args.command == "run":
        report = run_suite()
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        validate_report(report, require_pass=True)
        return 0

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    validate_report(report, require_pass=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
