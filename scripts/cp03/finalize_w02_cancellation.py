from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-12"
NEXT = "W02-13"
CLAIM = "CLAIM-CP03-W02-CANCELLATION-20260921"
EVIDENCE = "EVID-W02-CANCELLATION-20260921"
WAVE = "CP03-W02-CANCELLATION-20260921"


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


def latest_claim_status() -> str | None:
    status = None
    for row in rows("ledgers/CLAIM_LEDGER.ndjson"):
        if row.get("claim_id") == CLAIM and row.get("status"):
            status = row["status"]
    return status


def update_handoff() -> None:
    path = ROOT / "HANDOFF.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace('- COMPLETE: `W02-00..W02-11`.', '- COMPLETE: `W02-00..W02-12`.')
    streaming = '- W02-11 G4 evidence: `EVID-W02-STREAMING-20260921`; native `stream_full` bridge semantics + fragmented/coalesced canonical transport PASS; duplicate/reordered/EOF-before-terminal paths fail closed; provider egress 0; parity promotions 0.'
    cancellation = '- W02-12 G4 evidence: `EVID-W02-CANCELLATION-20260921`; request/attempt-scoped cancellation distinguishes REQUESTED → ACK → CANCELLED terminal, cancel-before/during PASS, already-terminal REJECTED, ACK-without-termination fails closed, explicit single-flight PASS; local worker cessation PASS; remote/provider cancellation effect remains UNKNOWN; provider egress 0; parity promotions 0.'
    if cancellation not in text:
        if streaming not in text:
            raise RuntimeError("HANDOFF streaming evidence anchor missing")
        text = text.replace(streaming, streaming + "\n" + cancellation, 1)
    old = '''## Next executable\n\n`W02-12 — Cancelación real`.\n\nW02-11 is evidence-backed COMPLETE and does not close W02. W02-12 is the sole READY G4 frontier. Cancellation itself remains NOT_RUN in the W02-11 evidence and must now be proven end-to-end without treating process teardown, EOF, timeout, or synthetic STOPPING as cancellation success. Later G4 tasks remain BLOCKED by the DAG.'''
    new = '''## Next executable\n\n`W02-13 — Structured output y tools`.\n\nW02-12 is evidence-backed COMPLETE and does not close W02. W02-13 is the sole READY G4 frontier. Cancellation proves local cessation only after a correlated ACK and CANCELLED terminal; provider/remote cancellation effect remains UNKNOWN and is not promoted. W02-14+ remain BLOCKED by the one-frontier DAG policy.'''
    if old not in text:
        raise RuntimeError("HANDOFF W02-12 frontier anchor missing")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_state() -> None:
    path = ROOT / "STATE.md"
    text = path.read_text(encoding="utf-8")
    old = '- Canonical task frontier: `W02-12 — Cancelación real` (`READY`)\n'
    new = '- Canonical task frontier: `W02-13 — Structured output y tools` (`READY`)\n'
    if old not in text:
        raise RuntimeError("STATE W02-12 frontier anchor missing")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    head = os.environ["GITHUB_SHA"]
    run_id = int(os.environ["GITHUB_RUN_ID"])
    expected = {
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "parent_wave": "CP03-W02",
        "task": TASK,
        "gate": "G4",
        "status": "PASS",
        "validated_head": head,
        "github_actions_run_id": run_id,
        "runtime_head": head,
        "cancel_before_first_chunk": "PASS",
        "cancel_during_stream": "PASS",
        "cancel_after_terminal": "REJECTED",
        "ack_without_termination": "FAIL_CLOSED",
        "requested_ack_terminal_distinct": "PASS",
        "single_flight": "PASS",
        "local_worker_cessation": "PASS",
        "remote_provider_cancellation_effect": "UNKNOWN",
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise RuntimeError(f"receipt mismatch {key}: {receipt.get(key)!r} != {value!r}")

    lock = read_json("inventory/cp03/W02_SCOPE_LOCK.json")
    goal = read_json("GOAL_STATE.json")
    plan = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    if not (
        lock["global_denominator"] == 7565
        and lock["openjarvis_obligations"] == 646
        and lock["w02_proof_units"] == 47
    ):
        raise RuntimeError("scope lock drift")
    if goal["parity"]["total"] != 7565 or goal["parity"]["verified"] != 0:
        raise RuntimeError("parity drift")
    if plan["global_denominator"] != 7565 or plan["openjarvis_obligations"] != 646:
        raise RuntimeError("task graph denominator drift")

    tasks = {row["id"]: row for row in plan["tasks"]}
    task = tasks[TASK]
    if plan["first_executable_task"] != TASK or task["status"] != "READY" or task["proof"]:
        raise RuntimeError("W02-12 is not the exact READY frontier")
    if not all(tasks[dep]["status"] == "COMPLETE" and tasks[dep]["proof"] for dep in task["depends_on"]):
        raise RuntimeError("W02-12 dependency proof missing")
    if latest_claim_status() != "ACTIVE":
        raise RuntimeError("W02-12 claim is not ACTIVE")

    task["status"] = "COMPLETE"
    task["proof"] = [{
        "evidence_id": EVIDENCE,
        "result": "PASS",
        "validated_head": head,
        "run_id": run_id,
        "gate": "G4",
        "cancel_before_first_chunk": "PASS",
        "cancel_during_stream": "PASS",
        "cancel_after_terminal": "REJECTED",
        "ack_without_termination": "FAIL_CLOSED",
        "requested_ack_terminal_distinct": "PASS",
        "single_flight": "PASS",
        "local_worker_cessation": "PASS",
        "remote_provider_cancellation_effect": "UNKNOWN",
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "parity_promotions": 0,
    }]

    next_task = tasks[NEXT]
    if next_task["status"] != "BLOCKED" or next_task["proof"]:
        raise RuntimeError("W02-13 pre-transition state invalid")
    if not all(tasks[dep]["status"] == "COMPLETE" and tasks[dep]["proof"] for dep in next_task["depends_on"]):
        raise RuntimeError("W02-13 dependencies are not evidence-backed COMPLETE")
    next_task["status"] = "READY"
    # Intentionally keep W02-14+ BLOCKED even if their dependency set is now
    # satisfied: this project advances one canonical frontier at a time.
    plan["first_executable_task"] = NEXT
    write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

    write_json("evidence/cp03/cp03-w02/W02-12/receipt.json", receipt)
    report = dict(receipt)
    report.update({
        "date": "2026-09-21",
        "evidence_id": EVIDENCE,
        "support_wave": WAVE,
        "next_task": NEXT,
        "note": "W02-12 proves request/attempt-scoped local cancellation semantics. Remote/provider cessation remains UNKNOWN; no provider egress, tool execution or parity promotion is claimed.",
    })
    write_json("evidence/cp03/cp03-w02/W02-12/report.json", report)
    write_json("sessions/20260921-w02-cancellation/RESULT.json", {
        "schema_version": 1,
        "date": "2026-09-21",
        "claim_id": CLAIM,
        "wave_id": WAVE,
        "task": TASK,
        "status": "COMPLETE",
        "evidence_id": EVIDENCE,
        "validated_head": head,
        "github_actions_run_id": run_id,
        "next_task": NEXT,
    })

    claim_path = "sessions/20260921-w02-cancellation/CLAIM.json"
    claim = read_json(claim_path)
    claim["status"] = "RELEASED"
    claim["release_evidence_id"] = EVIDENCE
    write_json(claim_path, claim)

    append_unique("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE, {
        "schema_version": 1,
        "date": "2026-09-21",
        "evidence_id": EVIDENCE,
        "status": "VERIFIED",
        "type": "cp03_w02_real_cancellation",
        "wave_id": "CP03-W02",
        "support_wave": WAVE,
        "github_actions_run_id": run_id,
        "validated_head": head,
        "runtime_head": head,
        "cancel_before_first_chunk": "PASS",
        "cancel_during_stream": "PASS",
        "cancel_after_terminal": "REJECTED",
        "ack_without_termination": "FAIL_CLOSED",
        "requested_ack_terminal_distinct": "PASS",
        "single_flight": "PASS",
        "local_worker_cessation": "PASS",
        "remote_provider_cancellation_effect": "UNKNOWN",
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "claim": "Exact-head G4 proves W02-12 local cancellation with REQUESTED, correlated ACK and CANCELLED terminal kept distinct. ACK alone, EOF, timeout and already-terminal responses are not cancellation success; remote/provider effect remains UNKNOWN.",
    })
    append_unique("ledgers/RUN_LOG.ndjson", "event_id", "RUN-W02-CANCELLATION-20260921-COMPLETE", {
        "schema_version": 1,
        "date": "2026-09-21",
        "event_id": "RUN-W02-CANCELLATION-20260921-COMPLETE",
        "event": "CP03_W02_CANCELLATION_ADVANCED",
        "goal_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "iteration": "I03",
        "wave_id": "CP03-W02",
        "support_wave": WAVE,
        "status": "ADVANCED",
        "evidence_id": EVIDENCE,
        "next_task": NEXT,
        "K": 47,
        "parity_promotions": 0,
    })
    append_unique("ledgers/WAVE_LEDGER.ndjson", "event_id", "WAVE-W02-CANCELLATION-20260921", {
        "schema_version": 1,
        "date": "2026-09-21",
        "event_id": "WAVE-W02-CANCELLATION-20260921",
        "wave_id": WAVE,
        "parent_wave": "CP03-W02",
        "iteration": "I03",
        "checkpoint": "CP03",
        "event": "VERIFICATION",
        "status": "COMPLETE",
        "evidence_id": EVIDENCE,
        "next_task": NEXT,
    })
    append_unique("ledgers/DECISION_LEDGER.ndjson", "decision_id", "D-0018", {
        "schema_version": 1,
        "date": "2026-09-21",
        "decision_id": "D-0018",
        "status": "ACCEPTED",
        "decision": "W02-12 uses explicit single-flight request/attempt ownership and treats InferenceCancel echo as transport ACK only; success requires a later correlated CANCELLED terminal. Already-terminal, ACK-without-termination, EOF and timeout never become cancellation success.",
        "context": "The v1.2 contract has InferenceCancel but no distinct Ack message. Reusing the typed cancel body as a correlated ACK preserves the existing additive wire contract while keeping remote/provider cessation explicitly UNKNOWN.",
        "evidence_id": EVIDENCE,
    })
    append_unique("ledgers/RISK_LEDGER.ndjson", "risk_id", "RISK-0012", {
        "schema_version": 1,
        "date": "2026-09-21",
        "risk_id": "RISK-0012",
        "status": "OPEN",
        "severity": "HIGH",
        "risk": "A local cancellation ACK and CANCELLED terminal do not prove that a future remote provider stopped generation, transport work, or billing.",
        "mitigation": "W02-12 records remote_provider_cancellation_effect=UNKNOWN, keeps provider egress executions at zero, and forbids parity promotion from local cancellation evidence. Future provider adapters must prove provider-specific abort/billing semantics before upgrading this risk.",
        "evidence_id": EVIDENCE,
    })
    with (ROOT / "ledgers/CLAIM_LEDGER.ndjson").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "schema_version": 1,
            "date": "2026-09-21",
            "claim_id": CLAIM,
            "event": "RELEASE",
            "owner": "chatgpt-gpt-5.6-sol",
            "status": "RELEASED",
            "release_evidence_id": EVIDENCE,
            "wave_id": WAVE,
        }, sort_keys=True, separators=(",", ":")) + "\n")

    update_handoff()
    update_state()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
