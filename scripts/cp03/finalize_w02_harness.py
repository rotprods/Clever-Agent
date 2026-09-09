"""Persist CP03-W02 task W02-02 only after the exact harness gate is re-proven.

This is a subordinate transition inside CP03-W02.  It does not close the parent
wave, change K=47, mutate the CP01 denominator, or promote capability parity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-09-09"
EVIDENCE_ID = "EVID-W02-HARNESS-20260909"
CLAIM_ID = "CLAIM-CP03-W02-HARNESS-001"
SUPPORT_WAVE = "CP03-W02-HARNESS-20260909"
PARENT_WAVE = "CP03-W02"


def read_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str, payload: dict[str, Any]) -> None:
    (ROOT / path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_rows(path: str) -> list[dict[str, Any]]:
    target = ROOT / path
    if not target.exists():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def validate_reports(root: Path) -> dict[str, Any]:
    lanes = {"fake": 6, "native": 1, "retest": 6}
    reports: dict[str, Any] = {}
    evidence_root = root / "evidence/cp03/cp03-w02/W02-02"
    for lane, count in lanes.items():
        path = evidence_root / lane / "report.json"
        if not path.is_file():
            raise RuntimeError(f"missing harness evidence: {path}")
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("status") != "PASS":
            raise RuntimeError(f"harness lane is not PASS: {lane}")
        if row.get("executed_count") != count:
            raise RuntimeError(f"harness lane count drift: {lane}")
        if row.get("executed_test_ids") != row.get("required_test_ids"):
            raise RuntimeError(f"harness lane omitted a mandatory test: {lane}")
        if row.get("failed") != 0 or row.get("ignored") != 0:
            raise RuntimeError(f"harness lane contains failed/ignored tests: {lane}")
        if row.get("parity_promotions") != 0:
            raise RuntimeError("W02-02 may not promote parity")
        junit = (evidence_root / lane / "results.junit.xml").read_text(encoding="utf-8")
        if f'tests="{count}"' not in junit or 'failures="0"' not in junit or 'skipped="0"' not in junit:
            raise RuntimeError(f"invalid JUnit evidence for {lane}")
        reports[lane] = row
    red = evidence_root / "red/audit.log"
    if not red.is_file() or "silent return paths" not in red.read_text(encoding="utf-8"):
        raise RuntimeError("historical RED proof missing")
    return reports


def finalize(*, run_id: int, validated_head: str, artifact_id: int, artifact_digest: str) -> dict[str, Any]:
    reports = validate_reports(ROOT)
    if not validated_head or len(validated_head) != 40:
        raise RuntimeError("validated_head must be a full commit SHA")
    if not artifact_digest.startswith("sha256:"):
        raise RuntimeError("artifact digest must be SHA256")

    lock = read_json("inventory/cp03/W02_SCOPE_LOCK.json")
    if lock.get("w02_proof_units") != 47 or lock.get("w02_owned_capabilities") != 37 or lock.get("w02_shared_capabilities") != 10:
        raise RuntimeError("W02 scope lock drift")
    if lock.get("global_denominator") != 7565 or lock.get("openjarvis_obligations") != 646:
        raise RuntimeError("denominator drift")

    goal = read_json("GOAL_STATE.json")
    parity = goal.get("parity", {})
    if parity.get("total") != 7565 or parity.get("verified") != 0:
        raise RuntimeError("W02-02 cannot run after parity/denominator drift")

    plan = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    if plan.get("wave") != PARENT_WAVE or plan.get("w02_obligation_count") != 47:
        raise RuntimeError("subordinate W02 plan authority drift")
    tasks = {row["id"]: row for row in plan.get("tasks", [])}
    if "W02-02" not in tasks or "W02-03" not in tasks:
        raise RuntimeError("required W02 tasks missing")
    if tasks["W02-02"].get("status") not in {"READY", "IN_PROGRESS", "COMPLETE"}:
        raise RuntimeError("W02-02 has invalid pre-transition status")
    if tasks["W02-02"].get("status") == "COMPLETE":
        existing = tasks["W02-02"].get("proof", [])
        if not any(row.get("evidence_id") == EVIDENCE_ID for row in existing if isinstance(row, dict)):
            raise RuntimeError("W02-02 already complete without expected evidence")
    else:
        if any(tasks[dep].get("status") != "COMPLETE" for dep in tasks["W02-02"].get("depends_on", [])):
            raise RuntimeError("W02-02 dependencies are incomplete")
        tasks["W02-02"]["status"] = "COMPLETE"
        tasks["W02-02"]["proof"] = [{
            "evidence_id": EVIDENCE_ID,
            "run_id": run_id,
            "artifact_id": artifact_id,
            "validated_head": validated_head,
            "result": "PASS",
            "fake_executed": reports["fake"]["executed_count"],
            "native_executed": reports["native"]["executed_count"],
            "retest_executed": reports["retest"]["executed_count"],
        }]
        tasks["W02-03"]["status"] = "READY"
        tasks["W02-03"]["proof"] = []
        plan["first_executable_task"] = "W02-03"
        plan["status"] = "IN_PROGRESS"
        write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

    append_unique("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE_ID, {
        "schema_version": 1,
        "date": DATE,
        "evidence_id": EVIDENCE_ID,
        "status": "VERIFIED",
        "type": "cp03_w02_harness_integrity",
        "wave_id": PARENT_WAVE,
        "support_wave": SUPPORT_WAVE,
        "claim": "Mandatory supervisor harness fails closed on missing prerequisites, zero/ignored cases and timeouts; historical silent returns are reproduced as RED; six fake tests, one exact pinned OpenJarvis native test and six fake retests execute with zero skips/failures and zero parity promotion.",
        "github_actions_run_id": run_id,
        "validated_head": validated_head,
        "artifact_id": artifact_id,
        "artifact_digest": artifact_digest,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "parity_promotions": 0,
    })

    if latest_claim_status(CLAIM_ID) != "RELEASED":
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

    append_unique("ledgers/RUN_LOG.ndjson", "event_id", "RUN-W02-HARNESS-20260909", {
        "schema_version": 1,
        "date": DATE,
        "event_id": "RUN-W02-HARNESS-20260909",
        "event": "CP03_W02_HARNESS_ADVANCED",
        "goal_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "iteration": "I03",
        "wave_id": PARENT_WAVE,
        "support_wave": SUPPORT_WAVE,
        "status": "ADVANCED",
        "evidence_id": EVIDENCE_ID,
        "next_task": "W02-03",
        "K": 47,
        "parity_promotions": 0,
        "head": validated_head,
    })
    append_unique("ledgers/WAVE_LEDGER.ndjson", "event_id", "WAVE-W02-HARNESS-20260909", {
        "schema_version": 1,
        "date": DATE,
        "event_id": "WAVE-W02-HARNESS-20260909",
        "wave_id": SUPPORT_WAVE,
        "parent_wave": PARENT_WAVE,
        "iteration": "I03",
        "checkpoint": "CP03",
        "event": "VERIFICATION",
        "status": "COMPLETE",
        "evidence_id": EVIDENCE_ID,
        "next_task": "W02-03",
    })

    (ROOT / "HANDOFF.md").write_text(
        "# HANDOFF — CP03-W02\n\n"
        "- Checkpoint: `CP03`; iteration: `I03`; parent wave `CP03-W02` remains `IN_PROGRESS`.\n"
        "- Frozen proof scope: **K=47 = 37 owned + 10 shared**; denominator 7,565 / OpenJarvis 646 / VERIFIED 0.\n"
        "- Complete subordinate tasks: `W02-00`, `W02-01`, `W02-02`.\n"
        f"- W02-02 evidence: `{EVIDENCE_ID}`; mandatory lanes 6 fake + 1 exact pinned native + 6 fake retest, with historical silent-return RED proof.\n"
        "- Next executable: `W02-03 — Acotar I/O y backpressure`.\n\n"
        "Next slice must bound aggregate frame/byte pressure and writes without creating reader/Drop deadlocks. PR #15 and its publication boundary remain independent and untouched. No inference, model parity or capability VERIFIED promotion has occurred.\n",
        encoding="utf-8",
    )
    return {"status": "ADVANCED", "parent_wave": PARENT_WAVE, "completed_task": "W02-02", "next_task": "W02-03", "K": 47, "parity_promotions": 0}


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
