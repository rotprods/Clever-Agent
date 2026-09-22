from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-14"
CLAIM = "CLAIM-CP03-W02-FALLBACK-20260922"
EVIDENCE = "EVID-W02-FALLBACK-BOUNDARY-20260922"
WAVE = "CP03-W02-FALLBACK-BOUNDARY-20260922"
DATE = "2026-09-22"
STALE_CAS_RED_RUN = 35704980485
CARDINALITY_RED_RUN = 35706711804
FMT_RED_RUN = 35707116490
RELEASE_GATE_GREEN_RUN = 35706944406


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


def assert_scope_amendment_present() -> None:
    matching = [
        row
        for row in rows("ledgers/CLAIM_LEDGER.ndjson")
        if row.get("claim_id") == CLAIM
        and row.get("event") == "SCOPE_AMENDED"
        and row.get("red_run_id") == FMT_RED_RUN
    ]
    if len(matching) != 1:
        raise RuntimeError("boundary finalization scope amendment is not durably reconciled")
    scope = set(matching[0].get("scope", []))
    required = {
        ".github/workflows/cp03-w02-fallback-boundary.yml",
        "scripts/cp03/finalize_w02_fallback_boundary.py",
    }
    if not required.issubset(scope):
        raise RuntimeError("boundary finalization scope amendment is incomplete")


def update_handoff() -> None:
    path = ROOT / "HANDOFF.md"
    text = path.read_text(encoding="utf-8")
    marker = "## W02-14 fallback core — active"
    if marker not in text:
        raise RuntimeError("HANDOFF W02-14 marker missing")
    prefix = text.split(marker, 1)[0].rstrip()
    block = """## W02-14 fallback — active

- Active claim: `CLAIM-CP03-W02-FALLBACK-20260922` on `wave/cp03/w02-fallback-20260922`; no overlapping active claim was accepted.
- Preserved core evidence: `EVID-W02-FALLBACK-CORE-20260922` proves the authority-free fallback decision core: fresh attempt IDs, cumulative reservation ceiling, repeated-target rejection, explicit target-class authorization, non-retryable stop, and mandatory no-retry after partial output.
- New partial evidence: `EVID-W02-FALLBACK-BOUNDARY-20260922` proves the generic supervised streaming attempt state machine around that core. A retryable pre-first-token failure may invoke exactly a fresh fallback attempt; an initial partial-output failure never invokes a fallback; and if a retry itself emits partial output before failing, no third attempt is invoked and streams are never spliced.
- Release-gate RED evidence is retained rather than rewritten: run `35704980485` exposed self-induced stale event-SHA CAS after legal claim reconciliation; run `35706711804` exposed a wrong one-vs-two structured-frontier assertion cardinality assumption; PR run `35707116490` exposed missing workspace rustfmt conformance. Each root cause was corrected and retested.
- W02-14 remains `IN_PROGRESS` with no task proof. The generic boundary is verified, but actual `AdapterSupervisor`/OpenJarvis sidecar F01/F02 wiring is still `NOT_RUN`; provider egress is 0, model executions in this sub-slice are 0, tool executions are 0, parity promotions are 0, denominator remains 7565, and OpenJarvis obligations remain 646.
- Exact next sub-slice: wire the proven state machine into the real `AdapterSupervisor` streaming transport boundary and prove, with correlated fake-sidecar/adversarial transport tests, retry only after a retryable failure before the first token plus a hard partial-output/no-splice terminal path. Do not open W02-15 until that evidence closes W02-14.
"""
    path.write_text(prefix + "\n\n" + block, encoding="utf-8")


def main() -> int:
    head = os.environ["GITHUB_SHA"]
    run_id = int(os.environ["GITHUB_RUN_ID"])
    assert_claim_active()
    assert_scope_amendment_present()

    graph = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    if graph.get("global_denominator") != 7565 or graph.get("openjarvis_obligations") != 646:
        raise RuntimeError("task graph denominator drift")
    if graph.get("w02_obligation_count") != 47:
        raise RuntimeError("W02 proof-unit denominator drift")
    if graph.get("first_executable_task") != TASK:
        raise RuntimeError("W02-14 is not the canonical first executable task")
    tasks = {row["id"]: row for row in graph["tasks"]}
    task = tasks[TASK]
    if task.get("status") != "IN_PROGRESS" or task.get("proof"):
        raise RuntimeError("W02-14 must remain IN_PROGRESS without terminal proof")
    if not all(tasks[dep]["status"] == "COMPLETE" and tasks[dep]["proof"] for dep in task["depends_on"]):
        raise RuntimeError("W02-14 dependency proof missing")
    if tasks["W02-15"]["status"] != "BLOCKED" or tasks["W02-15"]["proof"]:
        raise RuntimeError("W02-15 must remain BLOCKED during W02-14 boundary work")

    goal = read_json("GOAL_STATE.json")
    if goal["parity"]["total"] != 7565 or goal["parity"]["verified"] != 0:
        raise RuntimeError("parity drift")

    state = (ROOT / "STATE.md").read_text(encoding="utf-8")
    required_state = '- Canonical task frontier: `W02-14 — Fallback retry y salida parcial` (`IN_PROGRESS`)'
    if required_state not in state:
        raise RuntimeError("STATE frontier drift")

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
        "historical_red_runs": [STALE_CAS_RED_RUN, CARDINALITY_RED_RUN, FMT_RED_RUN],
        "release_gate_green_run_id": RELEASE_GATE_GREEN_RUN,
        "fallback_decision_core": "PASS",
        "supervised_boundary_state_machine": "PASS",
        "boundary_specific_tests": 3,
        "fallback_test_binary_tests": 10,
        "cargo_fmt": "PASS",
        "kernel_lib_regression": "PASS",
        "inference_security_regression": "PASS",
        "clippy": "PASS",
        "agentic_state_validation": "PASS",
        "context_pack_validation": "PASS",
        "next_actions_validation": "PASS",
        "plan_validation": "PASS",
        "parity_ledger_validation": "PASS",
        "release_gate_repair": "PASS",
        "adapter_supervisor_f01_f02": "NOT_RUN",
        "openjarvis_sidecar_f01_f02": "NOT_RUN",
        "provider_egress_executions": 0,
        "model_executions": 0,
        "tool_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "decision": "The retry state machine is centralized at one supervised attempt boundary. Transport/model execution remains caller-owned; the fallback module only decides legal continuation, allocates fresh attempt IDs, tracks cumulative reservation, and permanently disables further fallback after any emitted chunk.",
        "risk": "AdapterSupervisor/sidecar integration can still misclassify retryability or emitted-chunk state, so F01/F02 runtime parity is not established by this generic boundary proof.",
        "next_subslice": "Wire execute_streaming_fallbacks into the real AdapterSupervisor streaming transport and prove correlated pre-token retry plus post-partial no-splice end-to-end with the fake sidecar/adversarial harness.",
    }
    write_json("evidence/cp03/cp03-w02/W02-14/boundary_state_machine_report.json", report)

    write_json(
        "sessions/20260922-w02-fallback/RESULT.json",
        {
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
        },
    )
    session_claim = read_json("sessions/20260922-w02-fallback/CLAIM.json")
    session_claim["validated_head"] = head
    session_claim["last_evidence_id"] = EVIDENCE
    write_json("sessions/20260922-w02-fallback/CLAIM.json", session_claim)

    append_unique(
        "ledgers/EVIDENCE_LEDGER.ndjson",
        "evidence_id",
        EVIDENCE,
        {
            "schema_version": 1,
            "date": DATE,
            "evidence_id": EVIDENCE,
            "status": "VERIFIED",
            "type": "cp03_w02_supervised_fallback_boundary_partial",
            "wave_id": "CP03-W02",
            "support_wave": WAVE,
            "github_actions_run_id": run_id,
            "validated_head": head,
            "historical_red_runs": [STALE_CAS_RED_RUN, CARDINALITY_RED_RUN, FMT_RED_RUN],
            "fallback_decision_core": "PASS",
            "supervised_boundary_state_machine": "PASS",
            "boundary_specific_tests": 3,
            "fallback_test_binary_tests": 10,
            "cargo_fmt": "PASS",
            "kernel_lib_regression": "PASS",
            "inference_security_regression": "PASS",
            "clippy": "PASS",
            "adapter_supervisor_f01_f02": "NOT_RUN",
            "openjarvis_sidecar_f01_f02": "NOT_RUN",
            "provider_egress_executions": 0,
            "model_executions": 0,
            "tool_executions": 0,
            "parity_promotions": 0,
            "verified_capabilities": 0,
            "global_denominator": 7565,
            "openjarvis_obligations": 646,
            "w02_proof_units": 47,
            "claim": "Exact-head tests verify the authority-free decision core plus generic supervised streaming fallback state machine. They do not prove AdapterSupervisor/OpenJarvis sidecar F01/F02 wiring, so W02-14 remains IN_PROGRESS without task proof and W02-15 remains BLOCKED.",
        },
    )
    append_unique(
        "ledgers/RUN_LOG.ndjson",
        "event_id",
        "RUN-W02-FALLBACK-BOUNDARY-20260922",
        {
            "schema_version": 1,
            "date": DATE,
            "event_id": "RUN-W02-FALLBACK-BOUNDARY-20260922",
            "event": "CP03_W02_FALLBACK_BOUNDARY_ADVANCED",
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
        },
    )
    append_unique(
        "ledgers/WAVE_LEDGER.ndjson",
        "event_id",
        "WAVE-W02-FALLBACK-BOUNDARY-20260922",
        {
            "schema_version": 1,
            "date": DATE,
            "event_id": "WAVE-W02-FALLBACK-BOUNDARY-20260922",
            "wave_id": WAVE,
            "parent_wave": "CP03-W02",
            "iteration": "I03",
            "checkpoint": "CP03",
            "event": "IMPLEMENTATION_VERIFICATION",
            "status": "IN_PROGRESS",
            "evidence_id": EVIDENCE,
            "next_task": TASK,
        },
    )
    append_unique(
        "ledgers/DECISION_LEDGER.ndjson",
        "decision_id",
        "D-0022",
        {
            "schema_version": 1,
            "date": DATE,
            "decision_id": "D-0022",
            "status": "ACCEPTED",
            "evidence_id": EVIDENCE,
            "decision": "Centralize retry legality in one authority-free supervised streaming attempt state machine. The caller owns transport/model execution; emitted_chunks > 0 irreversibly forbids any subsequent fallback, while pre-token retry receives a fresh attempt_id and remains subject to cumulative reservation, repeated-target and target-class checks.",
            "context": "This makes retry/no-splice invariants composable before wiring them into AdapterSupervisor and prevents runtime integration from creating an implicit budget, egress, loop or mixed-engine-output authority channel.",
        },
    )
    append_unique(
        "ledgers/RISK_LEDGER.ndjson",
        "evidence_id",
        EVIDENCE,
        {
            "schema_version": 1,
            "date": DATE,
            "risk_id": "RISK-0014",
            "status": "OPEN",
            "severity": "HIGH",
            "evidence_id": EVIDENCE,
            "risk": "The generic supervised fallback state machine is verified, but AdapterSupervisor/OpenJarvis sidecar integration remains NOT_RUN; transport integration could still misclassify retryability or emitted-chunk state and bypass F01/F02 invariants.",
            "mitigation": "Keep W02-14 IN_PROGRESS and W02-15 BLOCKED; wire only through the existing correlated request/attempt transport and add fake-sidecar adversarial pre-token retry and post-partial no-splice tests before any W02-14 COMPLETE transition.",
        },
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
