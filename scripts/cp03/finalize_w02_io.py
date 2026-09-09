"""Persist CP03-W02 task W02-03 only after bounded-I/O behavior is re-proven.

This subordinate finalizer may close W02-03 and open W02-04/W02-05. It must not
complete either successor, change K=47, mutate the CP01 denominator, promote
capability parity, alter inference contracts, or touch PR #15.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-09-09"
EVIDENCE_ID = "EVID-W02-IO-20260909"
CLAIM_ID = "CLAIM-CP03-W02-IO-001"
SUPPORT_WAVE = "CP03-W02-IO-20260909"
PARENT_WAVE = "CP03-W02"
TASK_ID = "W02-03"
NEXT_TASK = "W02-04"
READY_SUCCESSORS = ("W02-04", "W02-05")
EVIDENCE_ROOT = Path("evidence/cp03/cp03-w02/W02-03")
REQUIRED_TESTS = (
    "inbound_frame_queue_is_bounded_under_flood",
    "inbound_wire_byte_budget_is_enforced_before_decode",
    "outbound_write_timeout_poison_session_when_peer_stops_reading",
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    (ROOT / path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def read_rows(path: str) -> list[dict[str, Any]]:
    target = ROOT / path
    if not target.exists():
        return []
    return [
        json.loads(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def append_unique(path: str, key: str, value: str, row: dict[str, Any]) -> None:
    if any(existing.get(key) == value for existing in read_rows(path)):
        return
    with (ROOT / path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def latest_claim_status(claim_id: str) -> str | None:
    status: str | None = None
    for row in read_rows("ledgers/CLAIM_LEDGER.ndjson"):
        if row.get("claim_id") == claim_id and row.get("status"):
            status = str(row["status"])
    return status


def validate_evidence(root: Path, validated_head: str) -> dict[str, Any]:
    evidence_root = root / EVIDENCE_ROOT
    report_path = evidence_root / "report.json"
    junit_path = evidence_root / "results.junit.xml"
    parity_path = evidence_root / "parity.json"
    clippy_path = evidence_root / "clippy.log"
    if not report_path.is_file():
        raise RuntimeError(f"missing W02-03 report: {report_path}")
    if not junit_path.is_file():
        raise RuntimeError(f"missing W02-03 JUnit: {junit_path}")
    if not parity_path.is_file():
        raise RuntimeError(f"missing W02-03 parity receipt: {parity_path}")
    if not clippy_path.is_file() or not clippy_path.read_text(encoding="utf-8").strip():
        raise RuntimeError("missing/non-empty W02-03 Clippy evidence")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS":
        raise RuntimeError("W02-03 evidence report is not PASS")
    if report.get("validated_head") != validated_head:
        raise RuntimeError("W02-03 report head does not match finalizer head")
    if report.get("executed_test_ids") != list(REQUIRED_TESTS):
        raise RuntimeError("W02-03 evidence omitted/reordered a mandatory test")
    if report.get("required_test_ids") != list(REQUIRED_TESTS):
        raise RuntimeError("W02-03 required-test set drift")
    if report.get("executed_count") != len(REQUIRED_TESTS):
        raise RuntimeError("W02-03 executed test count drift")
    if report.get("failed") != 0 or report.get("ignored") != 0:
        raise RuntimeError("W02-03 report contains failed/ignored tests")
    if report.get("parity_promotions") != 0:
        raise RuntimeError("W02-03 may not promote parity")

    junit = junit_path.read_text(encoding="utf-8")
    for token in ('tests="3"', 'failures="0"', 'skipped="0"'):
        if token not in junit:
            raise RuntimeError(f"invalid W02-03 JUnit: missing {token}")

    for test_id in REQUIRED_TESTS:
        log_path = evidence_root / "tests" / f"{test_id}.log"
        if not log_path.is_file():
            raise RuntimeError(f"missing exact-test log: {test_id}")
        log = log_path.read_text(encoding="utf-8")
        if "test result: ok. 1 passed; 0 failed; 0 ignored" not in log:
            raise RuntimeError(f"exact test was not proven as one executed PASS: {test_id}")

    parity = json.loads(parity_path.read_text(encoding="utf-8"))
    if parity.get("source_repo") != "openjarvis":
        raise RuntimeError("parity receipt source drift")
    if parity.get("total") != 646 or parity.get("verified") != 0:
        raise RuntimeError("OpenJarvis parity changed during W02-03")
    return report


def validate_authority() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    lock = read_json("inventory/cp03/W02_SCOPE_LOCK.json")
    if (
        lock.get("w02_proof_units") != 47
        or lock.get("w02_owned_capabilities") != 37
        or lock.get("w02_shared_capabilities") != 10
    ):
        raise RuntimeError("W02 scope lock drift")
    if lock.get("global_denominator") != 7565 or lock.get("openjarvis_obligations") != 646:
        raise RuntimeError("denominator drift")

    goal = read_json("GOAL_STATE.json")
    parity = goal.get("parity", {})
    if parity.get("total") != 7565 or parity.get("verified") != 0:
        raise RuntimeError("W02-03 cannot finalize after parity/denominator drift")

    plan = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    if plan.get("wave") != PARENT_WAVE or plan.get("w02_obligation_count") != 47:
        raise RuntimeError("subordinate W02 plan authority drift")
    tasks = {row["id"]: row for row in plan.get("tasks", [])}
    for required in ("W02-02", TASK_ID, *READY_SUCCESSORS):
        if required not in tasks:
            raise RuntimeError(f"required W02 task missing: {required}")
    if tasks["W02-02"].get("status") != "COMPLETE":
        raise RuntimeError("W02-03 prerequisite W02-02 is not COMPLETE")
    return plan, tasks


def finalize(
    *, run_id: int, validated_head: str, artifact_id: int, artifact_digest: str
) -> dict[str, Any]:
    if run_id <= 0 or artifact_id <= 0:
        raise RuntimeError("run_id and artifact_id must be positive")
    if not SHA_RE.fullmatch(validated_head):
        raise RuntimeError("validated_head must be a full lowercase commit SHA")
    if not DIGEST_RE.fullmatch(artifact_digest):
        raise RuntimeError("artifact digest must be canonical sha256:<64 hex>")

    report = validate_evidence(ROOT, validated_head)
    plan, tasks = validate_authority()
    task = tasks[TASK_ID]
    status = task.get("status")
    if status not in {"READY", "IN_PROGRESS", "COMPLETE"}:
        raise RuntimeError("W02-03 has invalid pre-transition status")

    if status == "COMPLETE":
        proof = task.get("proof", [])
        if not any(
            isinstance(row, dict) and row.get("evidence_id") == EVIDENCE_ID
            for row in proof
        ):
            raise RuntimeError("W02-03 already complete without expected evidence")
        for successor in READY_SUCCESSORS:
            if tasks[successor].get("status") not in {"READY", "IN_PROGRESS", "COMPLETE"}:
                raise RuntimeError(f"completed W02-03 has unopened successor: {successor}")
    else:
        if plan.get("first_executable_task") != TASK_ID:
            raise RuntimeError("W02-03 is not the canonical first executable task")
        if any(tasks[dep].get("status") != "COMPLETE" for dep in task.get("depends_on", [])):
            raise RuntimeError("W02-03 dependencies are incomplete")
        for successor in READY_SUCCESSORS:
            if tasks[successor].get("status") not in {"BLOCKED", "READY"}:
                raise RuntimeError(f"unexpected pre-transition successor status: {successor}")

        task["status"] = "COMPLETE"
        task["proof"] = [
            {
                "evidence_id": EVIDENCE_ID,
                "run_id": run_id,
                "artifact_id": artifact_id,
                "validated_head": validated_head,
                "result": "PASS",
                "executed_count": report["executed_count"],
                "queue_flood": "PASS",
                "wire_byte_budget": "PASS",
                "write_deadline": "PASS",
                "parity_promotions": 0,
            }
        ]
        for successor in READY_SUCCESSORS:
            tasks[successor]["status"] = "READY"
            tasks[successor]["proof"] = []
        plan["first_executable_task"] = NEXT_TASK
        plan["status"] = "IN_PROGRESS"
        write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

    append_unique(
        "ledgers/EVIDENCE_LEDGER.ndjson",
        "evidence_id",
        EVIDENCE_ID,
        {
            "schema_version": 1,
            "date": DATE,
            "evidence_id": EVIDENCE_ID,
            "status": "VERIFIED",
            "type": "cp03_w02_bounded_io_backpressure",
            "wave_id": PARENT_WAVE,
            "support_wave": SUPPORT_WAVE,
            "claim": (
                "Adapter transport bounds inbound frame count and aggregate wire bytes before "
                "Protobuf decode, applies negotiated frame limits, and bounds outbound write "
                "completion. Exact adversarial tests prove frame flood, byte-budget flood, and "
                "a peer that stops reading; Clippy is clean and parity remains unchanged."
            ),
            "github_actions_run_id": run_id,
            "validated_head": validated_head,
            "artifact_id": artifact_id,
            "artifact_digest": artifact_digest,
            "global_denominator": 7565,
            "openjarvis_obligations": 646,
            "w02_proof_units": 47,
            "executed_tests": list(REQUIRED_TESTS),
            "parity_promotions": 0,
        },
    )

    if latest_claim_status(CLAIM_ID) != "RELEASED":
        with (ROOT / "ledgers/CLAIM_LEDGER.ndjson").open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "schema_version": 1,
                        "date": DATE,
                        "claim_id": CLAIM_ID,
                        "event": "RELEASE",
                        "wave_id": SUPPORT_WAVE,
                        "owner": "chatgpt-gpt-5.6-sol",
                        "status": "RELEASED",
                        "release_evidence_id": EVIDENCE_ID,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )

    append_unique(
        "ledgers/RUN_LOG.ndjson",
        "event_id",
        "RUN-W02-IO-20260909",
        {
            "schema_version": 1,
            "date": DATE,
            "event_id": "RUN-W02-IO-20260909",
            "event": "CP03_W02_IO_ADVANCED",
            "goal_id": "CLEVER-JARVIS-001",
            "checkpoint": "CP03",
            "iteration": "I03",
            "wave_id": PARENT_WAVE,
            "support_wave": SUPPORT_WAVE,
            "status": "ADVANCED",
            "evidence_id": EVIDENCE_ID,
            "next_task": NEXT_TASK,
            "also_ready": "W02-05",
            "K": 47,
            "parity_promotions": 0,
            "head": validated_head,
        },
    )
    append_unique(
        "ledgers/WAVE_LEDGER.ndjson",
        "event_id",
        "WAVE-W02-IO-20260909",
        {
            "schema_version": 1,
            "date": DATE,
            "event_id": "WAVE-W02-IO-20260909",
            "wave_id": SUPPORT_WAVE,
            "parent_wave": PARENT_WAVE,
            "iteration": "I03",
            "checkpoint": "CP03",
            "event": "VERIFICATION",
            "status": "COMPLETE",
            "evidence_id": EVIDENCE_ID,
            "next_task": NEXT_TASK,
            "also_ready": "W02-05",
        },
    )

    (ROOT / "HANDOFF.md").write_text(
        "# HANDOFF — CP03-W02\n\n"
        "- Checkpoint: `CP03`; iteration: `I03`; parent wave `CP03-W02` remains `IN_PROGRESS`.\n"
        "- Frozen proof scope: **K=47 = 37 owned + 10 shared**; denominator 7,565 / OpenJarvis 646 / VERIFIED 0.\n"
        "- Complete subordinate tasks: `W02-00`, `W02-01`, `W02-02`, `W02-03`.\n"
        f"- W02-03 evidence: `{EVIDENCE_ID}`; bounded frame queue, aggregate wire-byte budget before decode, negotiated frame limit and bounded write completion all re-proven.\n"
        "- Next executable: `W02-04 — Teardown y cleanup reales`.\n"
        "- Also READY: `W02-05 — Correlación y registry atómico`; do not parallelize it with W02-04 if write surfaces overlap.\n\n"
        "W02-04 must prove shutdown/Drop and descendant cleanup without unbounded waits. "
        "PR #15 and its publication boundary remain independent and untouched. No inference, "
        "model parity or capability VERIFIED promotion has occurred.\n",
        encoding="utf-8",
    )
    return {
        "status": "ADVANCED",
        "parent_wave": PARENT_WAVE,
        "completed_task": TASK_ID,
        "next_task": NEXT_TASK,
        "also_ready": "W02-05",
        "K": 47,
        "parity_promotions": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--validated-head", required=True)
    parser.add_argument("--artifact-id", required=True, type=int)
    parser.add_argument("--artifact-digest", required=True)
    args = parser.parse_args()
    result = finalize(
        run_id=args.run_id,
        validated_head=args.validated_head,
        artifact_id=args.artifact_id,
        artifact_digest=args.artifact_digest,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
