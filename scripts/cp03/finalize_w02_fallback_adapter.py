from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-14"
NEXT = "W02-15"
CLAIM = "CLAIM-CP03-W02-FALLBACK-20260922"
EVIDENCE = "EVID-W02-FALLBACK-ADAPTER-20260922"


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str, value: dict) -> None:
    (ROOT / path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_unique(path: str, key: str, key_value: str, value: dict) -> None:
    target = ROOT / path
    lines = [line for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [json.loads(line) for line in lines]
    if any(row.get(key) == key_value for row in rows):
        return
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    validated_head = os.environ["GITHUB_SHA"]
    run_id = int(os.environ["GITHUB_RUN_ID"])

    graph_path = ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    tasks = {row["id"]: row for row in graph["tasks"]}
    if graph["global_denominator"] != 7565 or graph["openjarvis_obligations"] != 646:
        raise RuntimeError("denominator/obligation drift")
    if graph.get("w02_obligation_count") != 47:
        raise RuntimeError("W02 proof-unit denominator drift")
    if graph["first_executable_task"] != TASK:
        raise RuntimeError(f"unexpected DAG frontier: {graph['first_executable_task']}")
    if tasks[TASK]["status"] != "IN_PROGRESS" or tasks[TASK].get("proof"):
        raise RuntimeError("W02-14 must be IN_PROGRESS without task proof before finalization")
    if tasks[NEXT]["status"] != "BLOCKED" or tasks[NEXT].get("proof"):
        raise RuntimeError("W02-15 must remain blocked before W02-14 proof")
    if set(tasks[TASK]["depends_on"]) != {"W02-11", "W02-12"}:
        raise RuntimeError("W02-14 dependency drift")
    if any(tasks[dependency]["status"] != "COMPLETE" for dependency in tasks[TASK]["depends_on"]):
        raise RuntimeError("W02-14 dependency not complete")

    goal = read_json("GOAL_STATE.json")
    if goal["parity"]["total"] != 7565 or goal["parity"]["verified"] != 0:
        raise RuntimeError("parity drift")

    proof = {
        "adapter_supervisor_f01_f02": "PASS",
        "canonical_sidecar_transport": "PASS",
        "evidence_id": EVIDENCE,
        "failure_after_partial_output": "FAIL_CLOSED_NO_RETRY_NO_SPLICE",
        "failure_before_first_token": "PASS_FRESH_ATTEMPT",
        "gate": "G4",
        "parity_promotions": 0,
        "provider_egress_executions": 0,
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "result": "PASS",
        "run_id": run_id,
        "tool_executions": 0,
        "validated_head": validated_head,
    }
    tasks[TASK]["status"] = "COMPLETE"
    tasks[TASK]["proof"] = [proof]
    tasks[NEXT]["status"] = "READY"
    graph["first_executable_task"] = NEXT
    graph_path.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    state_path = ROOT / "STATE.md"
    state = state_path.read_text(encoding="utf-8")
    old = '- Canonical task frontier: `W02-14 — Fallback retry y salida parcial` (`IN_PROGRESS`)\n'
    new = '- Canonical task frontier: `W02-15 — Regresión de seguridad` (`READY`)\n'
    if old not in state and new not in state:
        raise RuntimeError("STATE W02-14 frontier anchor missing")
    state_path.write_text(state.replace(old, new, 1), encoding="utf-8")

    report = {
        "adapter_supervisor_f01_f02": "PASS",
        "canonical_sidecar_transport": "PASS",
        "checkpoint": "CP03",
        "cumulative_reservation_accounting": "PASS",
        "date": "2026-09-22",
        "denominator": 7565,
        "evidence_id": EVIDENCE,
        "fresh_attempt_id": "PASS",
        "gate": "G4",
        "global_parity_verified": 0,
        "openjarvis_obligations": 646,
        "partial_output_no_retry_no_splice": "PASS",
        "provider_egress_executions": 0,
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "real_openjarvis_fallback_note": "No real model/provider execution was authorized for this sub-slice. The runtime transport/state-machine behavior is proven with the real AdapterSupervisor against a correlated adversarial AdapterFrame sidecar peer; real-model fallback execution is intentionally not claimed.",
        "retry_after_pre_token_retryable_failure": "PASS",
        "retry_partial_output_blocks_third_attempt": "PASS",
        "run_id": run_id,
        "status": "PASS",
        "task": TASK,
        "task_status": "COMPLETE",
        "tool_executions": 0,
        "validated_head": validated_head,
        "w02_proof_units": 47,
    }
    write_json("evidence/cp03/cp03-w02/W02-14/adapter_runtime_report.json", report)

    claim = read_json("sessions/20260922-w02-fallback/CLAIM.json")
    if claim.get("claim_id") != CLAIM or claim.get("status") != "ACTIVE":
        raise RuntimeError("active W02-14 claim missing")
    claim["status"] = "RELEASED"
    claim["last_evidence_id"] = EVIDENCE
    claim["validated_head"] = validated_head
    claim["release_run_id"] = run_id
    write_json("sessions/20260922-w02-fallback/CLAIM.json", claim)

    result = {
        "claim_id": CLAIM,
        "date": "2026-09-22",
        "evidence_id": EVIDENCE,
        "github_actions_run_id": run_id,
        "next_task": NEXT,
        "parity_promotions": 0,
        "provider_egress_executions": 0,
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "result": "COMPLETE",
        "task": TASK,
        "tool_executions": 0,
        "validated_head": validated_head,
    }
    write_json("sessions/20260922-w02-fallback/RESULT.json", result)

    append_unique(
        "ledgers/EVIDENCE_LEDGER.ndjson",
        "evidence_id",
        EVIDENCE,
        {
            "adapter_supervisor_f01_f02": "PASS",
            "canonical_sidecar_transport": "PASS",
            "claim": "Exact-head G4 tests prove bounded fallback at the real AdapterSupervisor transport boundary: only retryable pre-token InferenceError may retry, generated attempt identity is fresh, cumulative reservation remains bounded, and partial output blocks all further attempts without stream splicing. Real OpenJarvis fallback model execution remains NOT_RUN and is not represented as PASS.",
            "date": "2026-09-22",
            "evidence_id": EVIDENCE,
            "global_denominator": 7565,
            "openjarvis_obligations": 646,
            "parity_promotions": 0,
            "provider_egress_executions": 0,
            "real_openjarvis_fallback_model_execution": "NOT_RUN",
            "result": "PASS",
            "run_id": run_id,
            "task": TASK,
            "tool_executions": 0,
            "validated_head": validated_head,
            "w02_proof_units": 47,
        },
    )
    append_unique(
        "ledgers/RUN_LOG.ndjson",
        "event_id",
        "RUN-W02-FALLBACK-ADAPTER-20260922-COMPLETE",
        {
            "checkpoint": "CP03",
            "date": "2026-09-22",
            "event": "CP03_W02_FALLBACK_ADAPTER_COMPLETE",
            "event_id": "RUN-W02-FALLBACK-ADAPTER-20260922-COMPLETE",
            "evidence_id": EVIDENCE,
            "goal_id": "CLEVER-JARVIS-001",
            "iteration": "I03",
            "next_task": NEXT,
            "parity_promotions": 0,
            "provider_egress_executions": 0,
            "real_openjarvis_fallback_model_execution": "NOT_RUN",
            "run_id": run_id,
            "task": TASK,
            "tool_executions": 0,
            "validated_head": validated_head,
        },
    )
    append_unique(
        "ledgers/WAVE_LEDGER.ndjson",
        "event_id",
        "WAVE-W02-FALLBACK-ADAPTER-20260922-COMPLETE",
        {
            "canonical_task": TASK,
            "checkpoint": "CP03",
            "date": "2026-09-22",
            "event": "COMPLETE",
            "event_id": "WAVE-W02-FALLBACK-ADAPTER-20260922-COMPLETE",
            "evidence_id": EVIDENCE,
            "next_task": NEXT,
            "parent_wave": "CP03-W02",
            "parity_promotions": 0,
            "result": "PASS",
            "run_id": run_id,
            "validated_head": validated_head,
            "wave_id": "CP03-W02-FALLBACK-20260922",
        },
    )
    append_unique(
        "ledgers/CLAIM_LEDGER.ndjson",
        "event_id",
        "CLAIM-W02-FALLBACK-20260922-RELEASE",
        {
            "canonical_task": TASK,
            "checkpoint": "CP03",
            "claim_id": CLAIM,
            "coordination": "Evidence-backed W02-14 completion releases the fallback claim. W02-15 becomes READY but is not claimed or implemented by this wave.",
            "date": "2026-09-22",
            "event": "RELEASE",
            "event_id": "CLAIM-W02-FALLBACK-20260922-RELEASE",
            "evidence_id": EVIDENCE,
            "owner": "chatgpt-gpt-5.6-sol",
            "parent_wave": "CP03-W02",
            "project_id": "CLEVER-JARVIS-001",
            "status": "RELEASED",
            "validated_head": validated_head,
            "wave_id": "CP03-W02-FALLBACK-20260922",
        },
    )
    append_unique(
        "ledgers/DECISION_LEDGER.ndjson",
        "decision_id",
        "DEC-W02-FALLBACK-ADAPTER-20260922",
        {
            "context": "W02-14 G4 AdapterSupervisor fallback closure.",
            "date": "2026-09-22",
            "decision": "Retry remains local llama.cpp only, only a correlated retryable InferenceError before any emitted chunk may invoke the bounded fallback core, and any partial output makes further attempts illegal. Real OpenJarvis fallback model execution remains NOT_RUN rather than being inferred from fake-sidecar transport proof.",
            "decision_id": "DEC-W02-FALLBACK-ADAPTER-20260922",
            "evidence_id": EVIDENCE,
            "status": "ACCEPTED",
            "task": TASK,
        },
    )
    append_unique(
        "ledgers/RISK_LEDGER.ndjson",
        "risk_id",
        "RISK-W02-FALLBACK-REAL-MODEL-NOT-RUN-20260922",
        {
            "date": "2026-09-22",
            "evidence_id": EVIDENCE,
            "mitigation": "Do not promote parity or claim provider/model execution from this transport proof. Preserve NOT_RUN until a later explicitly authorized real-model fallback lane is executed with exact artifact/runtime evidence.",
            "risk": "Real OpenJarvis fallback model execution was intentionally not run in W02-14 adapter closure; only canonical transport/state-machine behavior is proven.",
            "risk_id": "RISK-W02-FALLBACK-REAL-MODEL-NOT-RUN-20260922",
            "severity": "P2",
            "status": "OPEN",
            "task": TASK,
        },
    )

    handoff_path = ROOT / "HANDOFF.md"
    handoff = handoff_path.read_text(encoding="utf-8")
    handoff = handoff.replace(
        '`W02-14 — Fallback retry y salida parcial` (`IN_PROGRESS`).',
        '`W02-15 — Regresión de seguridad` (`READY`).',
        1,
    )
    handoff = handoff.replace(
        'W02-13 is evidence-backed COMPLETE. The next and only active DAG frontier is W02-14; W02-15+ remain BLOCKED. No parity promotion, denominator mutation, provider egress, or tool execution occurred in the W02-14 boundary sub-slice.',
        'W02-14 is evidence-backed COMPLETE. The next and only READY DAG frontier is W02-15; W02-16+ remain BLOCKED. No parity promotion, denominator mutation, provider egress, model execution, or tool execution occurred in the W02-14 adapter closure.',
        1,
    )
    marker = "## W02-14 fallback — active\n"
    if marker not in handoff:
        raise RuntimeError("HANDOFF active fallback marker missing")
    prefix = handoff.split(marker, 1)[0]
    complete = f'''## W02-14 fallback — COMPLETE\n\n- Evidence: `{EVIDENCE}` on exact tested head `{validated_head}` / run `{run_id}`.\n- `AdapterSupervisor` now invokes the already-proven bounded fallback state machine at the canonical streaming transport boundary. Retry is possible only for a correlated retryable `InferenceError` before the first emitted chunk; protocol/I/O failures are non-retryable.\n- Every fallback uses a generated fresh attempt ID, remains on the local `llamacpp` engine class, preserves cumulative reservation accounting, and repeated targets/attempt ceilings remain enforced by the core policy.\n- Adversarial fake-sidecar transport proves: pre-token retry recovers on a fresh attempt; primary partial output stops with no retry/no splice; retry partial output blocks a third attempt.\n- Real OpenJarvis fallback model execution is still `NOT_RUN`; this wave does not turn that into PASS. Provider egress 0; model executions 0; tool executions 0; parity promotions 0; denominator 7565; OpenJarvis obligations 646.\n- Claim `{CLAIM}` is released after evidence-backed W02-14 completion. W02-15 is only opened as `READY`; it is not claimed or implemented here.\n- Exact next task: `W02-15 — Regresión de seguridad` (G5), dependencies W02-07/W02-12/W02-13/W02-14 all COMPLETE.\n'''
    handoff_path.write_text(prefix + complete, encoding="utf-8")


if __name__ == "__main__":
    main()
