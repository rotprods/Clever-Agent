#!/usr/bin/env python3
"""Evidence-bound runner for mandatory CP03-W02 supervisor tests.

This gate exists to prevent a missing prerequisite, zero executed tests, ignored
cases, or infrastructure failure from being interpreted as a successful
behavioral result.  It does not execute inference and never promotes parity.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TEST_SOURCE = ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs"
MANIFEST = ROOT / "kernel/Cargo.toml"

FAKE_REQUIRED = (
    "rejects_relative_adapter_programs_before_spawn",
    "rejects_unknown_contract_major",
    "rejects_oversized_and_truncated_frames",
    "handshake_timeout_is_bounded",
    "crash_restart_budget_is_bounded",
    "inherited_secrets_are_stripped_and_registry_metadata_cannot_escalate",
)
NATIVE_REQUIRED = ("real_openjarvis_sidecar_is_supervised_and_bridged_without_promotion",)
ALL_REQUIRED = FAKE_REQUIRED + NATIVE_REQUIRED
PASS_RE = re.compile(r"test result: ok\.\s+1 passed;\s+0 failed;\s+0 ignored;")


class HarnessError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessError(message)


def _git_head(root: Path = ROOT) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _required_executable(name: str) -> str:
    value = os.environ.get(name, "").strip()
    _require(bool(value), f"missing mandatory environment variable {name}")
    path = Path(value)
    _require(path.is_absolute(), f"{name} must be an absolute executable path")
    _require(path.is_file(), f"{name} does not point to a file: {value}")
    _require(bool(path.stat().st_mode & stat.S_IXUSR), f"{name} is not executable: {value}")
    return value


def preflight(mode: str) -> dict[str, str]:
    values = {"CLEVER_TEST_PYTHON": _required_executable("CLEVER_TEST_PYTHON")}
    if mode in {"native", "all"}:
        values["CLEVER_DOCKER_BIN"] = _required_executable("CLEVER_DOCKER_BIN")
        workspace = os.environ.get("CLEVER_REPO_ROOT", "").strip()
        _require(bool(workspace), "missing mandatory environment variable CLEVER_REPO_ROOT")
        workspace_path = Path(workspace)
        _require(workspace_path.is_absolute() and workspace_path.is_dir(), "CLEVER_REPO_ROOT must be an absolute directory")
        image = os.environ.get("CLEVER_OPENJARVIS_IMAGE", "").strip()
        _require(bool(image), "missing mandatory environment variable CLEVER_OPENJARVIS_IMAGE")
        values["CLEVER_REPO_ROOT"] = workspace
        values["CLEVER_OPENJARVIS_IMAGE"] = image
    return values


def _function_segment(source: str, name: str) -> str:
    marker = f"fn {name}("
    start = source.find(marker)
    _require(start >= 0, f"required test missing from source: {name}")
    next_test = source.find("#[test]", start + len(marker))
    return source[start : next_test if next_test >= 0 else len(source)]


def audit_source(source: str) -> dict[str, object]:
    silent: list[str] = []
    for name in ALL_REQUIRED:
        segment = _function_segment(source, name)
        if re.search(r"\breturn\s*;", segment):
            silent.append(name)
    _require(not silent, f"mandatory tests contain silent return paths: {silent}")
    _require("MANDATORY prerequisite" in source, "mandatory prerequisite failure marker missing")
    return {"status": "PASS", "required_tests": len(ALL_REQUIRED), "silent_returns": 0}


def audit_path(path: Path) -> dict[str, object]:
    _require(path.is_file(), f"test source missing: {path}")
    return audit_source(path.read_text(encoding="utf-8"))


def _run_case(name: str, *, timeout: float, log_path: Path, root: Path = ROOT) -> dict[str, object]:
    command = [
        "cargo",
        "test",
        "--locked",
        "--manifest-path",
        str(MANIFEST.relative_to(root)),
        "--test",
        "adapter_supervisor",
        name,
        "--",
        "--exact",
        "--nocapture",
    ]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout
        code = completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        # TimeoutExpired may carry bytes even when subprocess.run uses text=True.
        output = "".join(
            part.decode("utf-8", errors="replace") if isinstance(part, bytes) else part or ""
            for part in (exc.stdout, exc.stderr)
        )
        code = 124
        timed_out = True
    elapsed = time.monotonic() - started
    # Preserve the diagnostic before validation raises; failing cases must remain
    # failures, but their output must be available in the uploaded artifact.
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding="utf-8")
    result = validate_case_output(name, code, output, timed_out=timed_out)
    result.update({"duration_seconds": round(elapsed, 6), "command": command, "output": output})
    return result


def validate_case_output(name: str, returncode: int, output: str, *, timed_out: bool = False) -> dict[str, object]:
    _require(not timed_out, f"mandatory test timed out: {name}")
    _require(returncode == 0, f"mandatory test failed: {name} exit={returncode}")
    _require(PASS_RE.search(output) is not None, f"mandatory test did not execute exactly one non-ignored test: {name}")
    _require("0 tests" not in output, f"zero-test result rejected: {name}")
    _require("ignored" not in output.lower().split("test result: ok.", 1)[0], f"ignored mandatory test rejected: {name}")
    return {"name": name, "status": "PASS", "returncode": returncode}


def _write_junit(results: list[dict[str, object]], path: Path) -> None:
    suite = ET.Element("testsuite", name="CP03-W02 mandatory supervisor", tests=str(len(results)), failures="0", skipped="0")
    for row in results:
        case = ET.SubElement(suite, "testcase", classname="adapter_supervisor", name=str(row["name"]), time=str(row["duration_seconds"]))
        output = ET.SubElement(case, "system-out")
        output.text = str(row.get("output", ""))
    tree = ET.ElementTree(suite)
    ET.indent(tree, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def run(mode: str, out_dir: Path, *, timeout: float = 180.0) -> dict[str, object]:
    _require(mode in {"fake", "native", "all"}, f"invalid mode: {mode}")
    preflight(mode)
    audit_path(TEST_SOURCE)
    names = FAKE_REQUIRED if mode == "fake" else NATIVE_REQUIRED if mode == "native" else ALL_REQUIRED
    results = [_run_case(name, timeout=timeout, log_path=out_dir / f"{name}.log") for name in names]
    _require(len(results) == len(names), "mandatory execution count mismatch")
    _require(all(row["status"] == "PASS" for row in results), "mandatory test did not pass")
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "scope": "CP03-W02-HARNESS-NOT-INFERENCE-PARITY",
        "mode": mode,
        "status": "PASS",
        "source_sha": _git_head(),
        "required_test_ids": list(names),
        "executed_test_ids": [str(row["name"]) for row in results],
        "executed_count": len(results),
        "failed": 0,
        "ignored": 0,
        "parity_promotions": 0,
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_junit(results, out_dir / "results.junit.xml")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fake", "native", "all"))
    parser.add_argument("--out", type=Path, default=ROOT / "evidence/cp03/cp03-w02/W02-02")
    parser.add_argument("--audit-source", type=Path)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()
    try:
        if args.audit_source:
            report = audit_path(args.audit_source)
        else:
            _require(args.mode is not None, "--mode is required unless --audit-source is used")
            report = run(args.mode, args.out, timeout=args.timeout)
    except (HarnessError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
