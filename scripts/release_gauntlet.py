"""Read-only G1 release gauntlet for the CP03-W02 inference frontier.

This gate connects canonical state, persisted evidence, workflow security,
Python regressions and Rust lifecycle tests.  Missing required tooling is a
BLOCKED result, never a PASS.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHA_REF = re.compile(r"^[0-9a-f]{40}$")
WORKFLOWS = (
    ".github/workflows/cp03-w02-teardown.yml",
    ".github/workflows/cp03-w02-teardown-finalize.yml",
)


class GauntletError(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise GauntletError(message)


def read_json(path: str, root: Path = ROOT) -> dict[str, Any]:
    value = json.loads((root / path).read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def read_jsonl(path: str, root: Path = ROOT) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (root / path).read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_frontier(root: Path = ROOT) -> dict[str, Any]:
    goal = read_json("GOAL_STATE.json", root)
    execution = read_json("EXECUTION_STATE.json", root)
    graph = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", root)
    tasks = {row["id"]: row for row in graph["tasks"]}
    require(goal.get("active_checkpoint") == "CP03", "active checkpoint is not CP03")
    parity = goal.get("parity", {})
    require(parity.get("total") == 7565 and parity.get("verified") == 0, "parity invariant drift")
    require(execution.get("next_wave") == "CP03-W02", "execution frontier drift")
    for task_id in ("W02-04", "W02-05"):
        require(tasks.get(task_id, {}).get("status") == "COMPLETE", f"{task_id} is not COMPLETE")
        require(bool(tasks[task_id].get("proof")), f"{task_id} has no proof")
    w02_06 = tasks.get("W02-06", {})
    require(w02_06.get("status") == "READY", "W02-06 is not READY")
    require({"W02-04", "W02-05"} <= set(w02_06.get("depends_on", [])), "W02-06 bypasses G1 dependencies")
    evidence = {row.get("evidence_id"): row for row in read_jsonl("ledgers/EVIDENCE_LEDGER.ndjson", root)}
    required = {"EVID-W02-TEARDOWN-20260909", "EVID-W02-CONTROL-ATOMIC-20260909"}
    require(all(evidence.get(eid, {}).get("status") == "VERIFIED" for eid in required), "G1 evidence ledger gap")
    report = read_json("evidence/cp03/cp03-w02/W02-04/report.json", root)
    require(report.get("status") == "PASS" and report.get("parity_promotions") == 0, "W02-04 report drift")
    return {"status": "PASS", "frontier": "W02-06", "g1_evidence": sorted(required), "parity_promotions": 0}


def validate_workflow_text(text: str, name: str) -> dict[str, Any]:
    require("pull_request_target:" not in text, f"{name}: pull_request_target is forbidden")
    uses = re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", text, flags=re.MULTILINE)
    for action in uses:
        require("@" in action and SHA_REF.fullmatch(action.rsplit("@", 1)[1]) is not None,
                f"{name}: unpinned action {action}")
    if "contents: write" in text:
        require("git ls-remote origin refs/heads/" in text, f"{name}: write workflow lacks CAS guard")
        require("workflow_dispatch:" not in text, f"{name}: writable manual dispatch is forbidden")
    require("curl " not in text or "| sh" not in text, f"{name}: curl-to-shell forbidden")
    return {"status": "PASS", "actions": len(uses), "contents_write": "contents: write" in text}


def validate_workflows(root: Path = ROOT) -> dict[str, Any]:
    rows = {}
    for relative in WORKFLOWS:
        rows[relative] = validate_workflow_text((root / relative).read_text(encoding="utf-8"), relative)
    return {"status": "PASS", "workflows": rows}


def run(name: str, command: list[str], timeout: int = 120) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {"name": name, "status": "PASS" if proc.returncode == 0 else "FAIL",
            "returncode": proc.returncode, "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-2000:]}


def execute(require_rust: bool = True) -> dict[str, Any]:
    lanes: dict[str, Any] = {}
    try:
        lanes["frontier"] = validate_frontier()
        lanes["workflow_security"] = validate_workflows()
    except (OSError, KeyError, TypeError, json.JSONDecodeError, GauntletError) as error:
        return {"schema_version": 1, "status": "FAIL", "error": str(error), "lanes": lanes,
                "parity_promotions": 0}
    python_commands = (
        ("agentic_state", ["python3", "scripts/validate_agentic_state.py"]),
        ("context", ["python3", "scripts/context/validate_context_pack.py"]),
        ("context_determinism", ["python3", "scripts/context/build_context_pack.py", "--check"]),
        ("next_actions", ["python3", "scripts/context/validate_next_actions.py"]),
        ("w02_plan", ["python3", "scripts/cp03/validate_w02_plan.py"]),
        ("parity", ["python3", "-m", "scripts.parity.ledger", "--check", "--source-repo", "openjarvis"]),
        ("python_regressions", ["python3", "-m", "unittest", "tests.test_cp03_openjarvis_sidecar",
                                "tests.test_cp03_w02_plan", "tests.test_cp03_w02_teardown_finalizer", "-v"]),
    )
    lanes["python"] = [run(name, command) for name, command in python_commands]
    if not all(row["status"] == "PASS" for row in lanes["python"]):
        return {"schema_version": 1, "status": "FAIL", "lanes": lanes, "parity_promotions": 0}
    cargo = shutil.which("cargo")
    if cargo is None:
        lanes["rust"] = {"status": "BLOCKED", "reason": "cargo toolchain unavailable"}
        status = "BLOCKED" if require_rust else "PASS_WITH_RUST_BLOCKED"
    else:
        rust_commands = (
            ("rustfmt", [cargo, "fmt", "--manifest-path", "kernel/Cargo.toml", "--all", "--", "--check"]),
            ("lifecycle_legacy", [cargo, "test", "--locked", "--manifest-path", "kernel/Cargo.toml", "-p", "clever-kernel", "--test", "lifecycle_legacy_regressions"]),
            ("adapter_lifecycle", [cargo, "test", "--locked", "--manifest-path", "kernel/Cargo.toml", "-p", "clever-kernel", "--test", "adapter_lifecycle"]),
            ("control_regressions", [cargo, "test", "--locked", "--manifest-path", "kernel/Cargo.toml", "-p", "clever-kernel", "--test", "control_regressions"]),
            ("clippy", [cargo, "clippy", "--locked", "--manifest-path", "kernel/Cargo.toml", "--workspace", "--all-targets", "--all-features", "--", "-D", "warnings"]),
        )
        lanes["rust"] = [run(name, command, timeout=300) for name, command in rust_commands]
        status = "PASS" if all(row["status"] == "PASS" for row in lanes["rust"]) else "FAIL"
    return {"schema_version": 1, "status": status, "frontier": "W02-06", "lanes": lanes,
            "parity_promotions": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-rust", action="store_true",
                        help="diagnostic mode only; reports PASS_WITH_RUST_BLOCKED rather than BLOCKED")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = execute(require_rust=not args.allow_missing_rust)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["status"] in {"PASS", "PASS_WITH_RUST_BLOCKED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
