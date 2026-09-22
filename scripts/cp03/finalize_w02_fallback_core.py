from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-14"
CLAIM = "CLAIM-CP03-W02-FALLBACK-20260922"
EVIDENCE = "EVID-W02-FALLBACK-CORE-20260922"
WAVE = "CP03-W02-FALLBACK-20260922"
DATE = "2026-09-22"
RED_RUN = 35697471602
CLIPPY_RED_RUN = 35697845508


def read_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str, value) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rows(path: str):
    target = ROOT / path
    if not target.exists():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_unique(path: str, key: str, value: str, row: dict) -> None:
    if any(existing.get(key) == value for existing in rows(path)):
        return
    with (ROOT / path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def assert_claim_active() -> None:
    states: dict[str, str] = {}
    for row in rows("ledgers/CLAIM_LEDGER.ndjson"):
        claim_id = row.get("claim_id")
        status = row.get("status")
        if isinstance(claim_id, str) and isinstance(status, str):
            states[claim_id] = status
    if states.get(CLAIM) != "ACTIVE":
        raise RuntimeError(f"W02-14 claim is not ACTIVE: {states.get(CLAIM)!r}")
    active_other = sorted(
        claim_id
        for claim_id, status in states.items()
        if status == "ACTIVE" and claim_id != CLAIM
    )
    if active_other:
        raise RuntimeError(f"overlapping/foreign active claims require reconciliation: {active_other}")


def update_state() -> None:
    path = ROOT / "STATE.md"
    text = path.read_text(encoding="utf-8")
    old = '- Canonical task frontier: `W02-14 — Fallback retry y salida parcial` (`READY`)\n'
    new = '- Canonical task frontier: `W02-14 — Fallback retry y salida parcial` (`IN_PROGRESS`)\n'
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise RuntimeError("STATE W02-14 frontier anchor missing")
    path.write_text(text, encoding="utf-8")


def update_handoff() -> None:
    path = ROOT / "HANDOFF.md"
    text = path.read_text(encoding="utf-8")
    marker = "## W02-14 fallback core — active"
    block = """## W02-14 fallback core — active

- Active claim: `CLAIM-CP03-W02-FALLBACK-20260922` on `wave/cp03/w02-fallback-20260922`.
- Evidence: `EVID-W02-FALLBACK-CORE-20260922` verifies the bounded Rust decision core only: fresh attempt IDs, cumulative reserved-cost ceiling, repeated-target loop rejection, explicit target-class authorization, non-retryable stop, and mandatory partial-output stop with no stream splicing.
- Historical RED is preserved: run `35697471602` failed because the implementation did not exist; run `35697845508` then exposed `clippy::too_many_arguments`; typed failure/candidate inputs fixed the root cause before the green gauntlet.
- W02-14 remains `IN_PROGRESS`. Runtime fallback orchestration through the supervised inference path is `NOT_RUN`; provider egress is 0; tool execution is 0; parity promotions are 0; denominator remains 7565; OpenJarvis obligations remain 646.
- Exact next sub-slice: wire this policy core into the supervised streaming inference attempt boundary and prove F01/F02 end-to-end: retry only after retryable failure before first token, new attempt ID/cumulative budget receipt, and partial/failure terminal after any emitted chunk without concatenating output from another engine. W02-15+ remain blocked.
"""
    if marker not in text:
        text = text.rstrip() + "\n\n" + block
    path.write_text(text, encoding="utf-8")


def main() -> int:
    head = os.environ["GITHUB_SHA"]
    run_id = int(os.environ["GITHUB_RUN_ID"])
    assert_claim_active()

    graph = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    if graph.get("global_denominator") != 7565 or graph.get("openjarvis_obligations") != 646:
        raise RuntimeError("task graph denominator drift")
    if graph.get("first_executable_task") != TASK:
        raise RuntimeError("W02-14 is not the canonical first executable task")
    tasks = {row["id"]: row for row in graph["tasks"]}
    task = tasks[TASK]
    if task.get("status") not in {"READY", "IN_PROGRESS"} or task.get("proof"):
        raise RuntimeError("W02-14 pre-transition state invalid")
    if not all(tasks[dep]["status"] == "COMPLETE" and tasks[dep]["proof"] for dep in task["depends_on"]):
        raise RuntimeError("W02-14 dependency proof missing")
    if tasks["W02-15"]["status"] != "BLOCKED" or tasks["W02-15"]["proof"]:
        raise RuntimeError("W02-15 must remain BLOCKED during the partial W02-14 wave")

    goal = read_json("GOAL_STATE.json")
    if goal["parity"]["total"] != 7565 or goal["parity"]["verified"] != 0:
        raise RuntimeError("parity drift")

    task["status"] = "IN_PROGRESS"
    graph["first_executable_task"] = TASK
    write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", graph)
    update_state()
    update_handoff()

    report = {
        "schema_version": 1,
        "date": DATE,
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "parent_wave": "CP03-W02",
        "support_wave": WAVE,
        "task": TASK,
        "task_status": "IN_PROGRESS",
        "evidence_id": EVIDENCE,
        "status": "VERIFIED_SUBSLICE",
        "validated_head": head,
        "github_actions_run_id": run_id,
        "historical_red_run_id": RED_RUN,
        "clippy_root_cause_red_run_id": CLIPPY_RED_RUN,
        "fallback_decision_core": "PASS",
        "targeted_tests": 7,
        "kernel_lib_regression": "PASS",
        "clippy": "PASS",
        "agentic_state_validation": "PASS",
        "plan_validation": "PASS",
        "parity_ledger_validation": "PASS",
        "runtime_fallback_integration": "NOT_RUN",
        "provider_egress_executions": 0,
        "model_executions": 0,
        "tool_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "decision": "Retry authority is bounded to pre-first-token retryable failures. A retry receives a fresh attempt_id, cannot repeat an already-attempted target, cannot exceed the cumulative reservation ceiling or target-class authorization, and is forbidden after partial output.",
        "risk": "The decision core is not yet wired into AdapterSupervisor/sidecar runtime orchestration; therefore W02-14 is not complete and F01/F02 runtime behavior remains NOT_RUN.",
        "next_subslice": "Integrate the policy at the supervised streaming attempt boundary and prove retry-before-first-token plus partial-output-no-splice end-to-end.",
    }
    write_json("evidence/cp03/cp03-w02/W02-14/core_policy_report.json", report)
    write_json("sessions/20260922-w02-fallback/RESULT.json", {
        "schema_version": 1,
        "date": DATE,
        "claim_id": CLAIM,
        "wave_id": WAVE,
        "task": TASK,
        "status": "ADVANCED_IN_PROGRESS",
        "evidence_id": EVIDENCE,
        "validated_head": head,
        "github_actions_run_id": run_id,
        "next_task": TASK,
        "next_subslice": report["next_subslice"],
    })
    session_claim = read_json("sessions/20260922-w02-fallback/CLAIM.json")
    session_claim["validated_head"] = head
    session_claim["last_evidence_id"] = EVIDENCE
    write_json("sessions/20260922-w02-fallback/CLAIM.json", session_claim)

    append_unique("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE, {
        "schema_version": 1,
        "date": DATE,
        "evidence_id": EVIDENCE,
        "status": "VERIFIED",
        "type": "cp03_w02_fallback_decision_core_partial",
        "wave_id": "CP03-W02",
        "support_wave": WAVE,
        "github_actions_run_id": run_id,
        "validated_head": head,
        "historical_red_run_id": RED_RUN,
        "clippy_root_cause_red_run_id": CLIPPY_RED_RUN,
        "fallback_decision_core": "PASS",
        "targeted_tests": 7,
        "kernel_lib_regression": "PASS",
        "clippy": "PASS",
        "runtime_fallback_integration": "NOT_RUN",
        "provider_egress_executions": 0,
        "model_executions": 0,
        "tool_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "claim": "Exact-head tests verify the bounded W02-14 fallback decision core only. Runtime F01/F02 orchestration remains NOT_RUN, so W02-14 stays IN_PROGRESS with no proof entry and W02-15 remains BLOCKED.",
    })
    append_unique("ledgers/RUN_LOG.ndjson", "event_id", "RUN-W02-FALLBACK-CORE-20260922", {
        "schema_version": 1,
        "date": DATE,
        "event_id": "RUN-W02-FALLBACK-CORE-20260922",
        "event": "CP03_W02_FALLBACK_CORE_ADVANCED",
        "goal_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "iteration": "I03",
        "wave_id": "CP03-W02",
        "support_wave": WAVE,
        "status": "ADVANCED",
        "evidence_id": EVIDENCE,
        "task_status": "IN_PROGRESS",
        "next_task": TASK,
        "K": 47,
        "parity_promotions": 0,
    })
    append_unique("ledgers/WAVE_LEDGER.ndjson", "event_id", "WAVE-W02-FALLBACK-CORE-20260922", {
        "schema_version": 1,
        "date": DATE,
        "event_id": "WAVE-W02-FALLBACK-CORE-20260922",
        "wave_id": WAVE,
        "parent_wave": "CP03-W02",
        "iteration": "I03",
        "checkpoint": "CP03",
        "event": "IMPLEMENTATION_VERIFICATION",
        "status": "IN_PROGRESS",
        "evidence_id": EVIDENCE,
        "next_task": TASK,
    })
    append_unique("ledgers/DECISION_LEDGER.ndjson", "decision_id", "D-0021", {
        "schema_version": 1,
        "date": DATE,
        "decision_id": "D-0021",
        "status": "ACCEPTED",
        "evidence_id": EVIDENCE,
        "decision": "W02-14 fallback is fail-closed: automatic retry is permitted only for a retryable failure before the first emitted token; every retry receives a fresh attempt_id, cumulative reserved cost is bounded, repeated targets are rejected, and target-class authorization cannot be widened by fallback. Any partial output terminates without stream splicing.",
        "context": "This isolates policy invariants before runtime integration and prevents fallback from becoming an implicit egress, budget, loop, or mixed-engine-output authority channel.",
    })
    append_unique("ledgers/RISK_LEDGER.ndjson", "risk_id", "RISK-0014", {
        "schema_version": 1,
        "date": DATE,
        "risk_id": "RISK-0014",
        "status": "OPEN",
        "severity": "HIGH",
        "evidence_id": EVIDENCE,
        "risk": "The W02-14 decision core is verified but not yet wired into the supervised inference runtime, so an integration could bypass fresh-attempt, cumulative-budget, no-loop or no-splice invariants.",
        "mitigation": "Keep W02-14 IN_PROGRESS and W02-15 BLOCKED; integrate only behind the existing supervised request/attempt boundary and add end-to-end F01/F02 adversarials before any W02-14 COMPLETE transition.",
    })

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
