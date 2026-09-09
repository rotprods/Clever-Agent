"""Finalize canonical task W02-05 after exact-head correlation/atomicity proof.

This finalizer may close W02-05 only. W02-04 remains the first executable task,
W02-06 remains blocked until the G1 lifecycle boundary is closed, and parity is
never promoted here.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-09-09"
TASK = "W02-05"
NEXT = "W02-04"
EVIDENCE_ID = "EVID-W02-CONTROL-ATOMIC-20260909"
CLAIM_ID = "CLAIM-CP03-W02-CONTROL-002"
SUPPORT_WAVE = "CP03-W02-CONTROL-20260909-B"
EVIDENCE_ROOT = Path("evidence/cp03/cp03-w02/W02-05")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    (ROOT / path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rows(path: str) -> list[dict[str, Any]]:
    target = ROOT / path
    if not target.exists():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_unique(path: str, key: str, value: str, row: dict[str, Any]) -> None:
    if any(existing.get(key) == value for existing in rows(path)):
        return
    with (ROOT / path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def latest_claim_status() -> str | None:
    status = None
    for row in rows("ledgers/CLAIM_LEDGER.ndjson"):
        if row.get("claim_id") == CLAIM_ID and row.get("status"):
            status = str(row["status"])
    return status


def validate_authority() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    lock = read_json("inventory/cp03/W02_SCOPE_LOCK.json")
    if (lock.get("w02_proof_units"), lock.get("w02_owned_capabilities"), lock.get("w02_shared_capabilities")) != (47, 37, 10):
        raise RuntimeError("W02 scope lock drift")
    if lock.get("global_denominator") != 7565 or lock.get("openjarvis_obligations") != 646:
        raise RuntimeError("denominator drift")
    goal = read_json("GOAL_STATE.json")
    if goal.get("parity", {}).get("total") != 7565 or goal.get("parity", {}).get("verified") != 0:
        raise RuntimeError("W02-05 cannot finalize after parity drift")
    plan = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    tasks = {task["id"]: task for task in plan.get("tasks", [])}
    for required in ("W02-03", "W02-04", "W02-05", "W02-06"):
        if required not in tasks:
            raise RuntimeError(f"missing task: {required}")
    if tasks["W02-03"].get("status") != "COMPLETE":
        raise RuntimeError("W02-03 prerequisite is not COMPLETE")
    if tasks["W02-04"].get("status") != "READY":
        raise RuntimeError("W02-04 must remain READY during W02-05 close")
    if plan.get("first_executable_task") != "W02-04":
        raise RuntimeError("W02-04 is not the current frontier")
    return plan, tasks


def validate_evidence(validated_head: str) -> dict[str, Any]:
    folder = ROOT / EVIDENCE_ROOT
    report_path = folder / "report.json"
    if not report_path.is_file():
        raise RuntimeError("missing W02-05 report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    required = {
        "status": "PASS",
        "validated_head": validated_head,
        "historical_red_failures": 12,
        "green_tests": 15,
        "retest_executions": 75,
        "w02_03_regression": "PASS",
        "clippy": "PASS",
        "parity_promotions": 0,
    }
    for key, expected in required.items():
        if report.get(key) != expected:
            raise RuntimeError(f"W02-05 evidence mismatch: {key}={report.get(key)!r}, expected {expected!r}")
    for name in ("green.log", "retest.log", "adapter-regression.log", "clippy.log", "red-summary.json"):
        target = folder / name
        if not target.is_file() or not target.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"missing/non-empty evidence file: {name}")
    if "15 passed; 0 failed; 0 ignored" not in (folder / "green.log").read_text(encoding="utf-8"):
        raise RuntimeError("GREEN log does not prove all 15 control tests")
    return report


def finalize(*, run_id: int, validated_head: str, artifact_id: int, artifact_digest: str) -> dict[str, Any]:
    if run_id <= 0 or artifact_id <= 0:
        raise RuntimeError("run/artifact IDs must be positive")
    if not SHA_RE.fullmatch(validated_head):
        raise RuntimeError("validated_head must be a full lowercase SHA")
    if not DIGEST_RE.fullmatch(artifact_digest):
        raise RuntimeError("artifact digest must be sha256:<64 hex>")
    report = validate_evidence(validated_head)
    plan, tasks = validate_authority()
    task = tasks[TASK]
    if task.get("status") not in {"READY", "IN_PROGRESS", "COMPLETE"}:
        raise RuntimeError("invalid W02-05 status")
    if task.get("status") != "COMPLETE":
        task["status"] = "COMPLETE"
        task["proof"] = [{
            "evidence_id": EVIDENCE_ID,
            "run_id": run_id,
            "artifact_id": artifact_id,
            "validated_head": validated_head,
            "result": "PASS",
            "historical_red_failures": report["historical_red_failures"],
            "green_tests": report["green_tests"],
            "retest_executions": report["retest_executions"],
            "parity_promotions": 0,
        }]
        # W02-06 stays blocked intentionally until W02-04 closes G1.
        if tasks["W02-06"].get("status") != "BLOCKED":
            raise RuntimeError("W02-06 must remain BLOCKED until W02-04 completes")
        plan["first_executable_task"] = NEXT
        write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

    append_unique("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE_ID, {
        "schema_version": 1,
        "date": DATE,
        "evidence_id": EVIDENCE_ID,
        "status": "VERIFIED",
        "type": "cp03_w02_correlation_atomic_registry",
        "wave_id": "CP03-W02",
        "support_wave": SUPPORT_WAVE,
        "github_actions_run_id": run_id,
        "validated_head": validated_head,
        "artifact_id": artifact_id,
        "artifact_digest": artifact_digest,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "historical_red_failures": 12,
        "green_tests": 15,
        "retest_executions": 75,
        "parity_promotions": 0,
        "claim": "All control responses are request-correlated; protocol ambiguity poisons the session; health cannot be false-green; registry snapshots validate fully before atomic batch commit and idempotent replay preserves availability.",
    })
    append_unique("ledgers/RUN_LOG.ndjson", "event_id", "RUN-W02-CONTROL-ATOMIC-20260909", {
        "schema_version": 1,
        "date": DATE,
        "event_id": "RUN-W02-CONTROL-ATOMIC-20260909",
        "event": "CP03_W02_CONTROL_ATOMIC_ADVANCED",
        "goal_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "iteration": "I03",
        "wave_id": "CP03-W02",
        "support_wave": SUPPORT_WAVE,
        "status": "ADVANCED",
        "evidence_id": EVIDENCE_ID,
        "next_task": NEXT,
        "K": 47,
        "parity_promotions": 0,
    })
    append_unique("ledgers/WAVE_LEDGER.ndjson", "event_id", "WAVE-W02-CONTROL-ATOMIC-20260909", {
        "schema_version": 1,
        "date": DATE,
        "event_id": "WAVE-W02-CONTROL-ATOMIC-20260909",
        "wave_id": SUPPORT_WAVE,
        "parent_wave": "CP03-W02",
        "iteration": "I03",
        "checkpoint": "CP03",
        "event": "VERIFICATION",
        "status": "COMPLETE",
        "evidence_id": EVIDENCE_ID,
        "next_task": NEXT,
    })
    if latest_claim_status() != "RELEASED":
        with (ROOT / "ledgers/CLAIM_LEDGER.ndjson").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "schema_version": 1,
                "date": DATE,
                "claim_id": CLAIM_ID,
                "event": "RELEASE",
                "wave_id": SUPPORT_WAVE,
                "owner": "chatgpt-gpt-5.6-sol",
                "status": "RELEASED",
                "release_evidence_id": EVIDENCE_ID,
            }, sort_keys=True, separators=(",", ":")) + "\n")
    (ROOT / "HANDOFF.md").write_text(
        "# HANDOFF — CP03-W02\n\n"
        "- `W02-00..W02-03` COMPLETE; `W02-05` COMPLETE with `EVID-W02-CONTROL-ATOMIC-20260909`.\n"
        "- Frozen scope remains K=47 (37 owned + 10 shared); global denominator 7,565; OpenJarvis 646; VERIFIED 0.\n"
        "- First executable task remains `W02-04 — Teardown y cleanup reales`.\n"
        "- `W02-06` remains BLOCKED until W02-04 closes the G1 lifecycle boundary.\n"
        "- W02-05 proves correlated control exchanges, poison-on-ambiguity, strict health and atomic registry replay. It does not prove inference.\n"
        "- Do not merge or mutate historical PR #15; relevant behavior was ported cleanly and re-proven.\n",
        encoding="utf-8",
    )
    return {"status": "ADVANCED", "completed_task": TASK, "next_task": NEXT, "K": 47, "parity_promotions": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--validated-head", required=True)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--artifact-digest", required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(run_id=args.run_id, validated_head=args.validated_head, artifact_id=args.artifact_id, artifact_digest=args.artifact_digest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
