from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-13"
NEXT = "W02-14"
CLAIM = "CLAIM-CP03-W02-STRUCTURED-20260921"
EVIDENCE = "EVID-W02-STRUCTURED-CORE-20260921"
WAVE = "CP03-W02-STRUCTURED-20260921"
DATE = "2026-09-21"


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


def latest_claim_states() -> dict[str, str]:
    states: dict[str, str] = {}
    for row in rows("ledgers/CLAIM_LEDGER.ndjson"):
        claim_id = row.get("claim_id")
        status = row.get("status")
        if isinstance(claim_id, str) and isinstance(status, str):
            states[claim_id] = status
    return states


def ensure_claim_record(base_head: str) -> None:
    states = latest_claim_states()
    active_other = sorted(
        claim_id for claim_id, status in states.items()
        if status == "ACTIVE" and claim_id != CLAIM
    )
    if active_other:
        raise RuntimeError(f"another active claim exists at this exact base: {active_other}")
    if states.get(CLAIM) == "ACTIVE":
        return
    if CLAIM in states:
        raise RuntimeError(f"W02-13 claim already has terminal/non-active state: {states[CLAIM]}")
    with (ROOT / "ledgers/CLAIM_LEDGER.ndjson").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "schema_version": 1,
            "date": DATE,
            "claim_id": CLAIM,
            "event": "CLAIM",
            "owner": "chatgpt-gpt-5.6-sol",
            "status": "ACTIVE",
            "project_id": "CLEVER-JARVIS-001",
            "checkpoint": "CP03",
            "canonical_task": TASK,
            "parent_wave": "CP03-W02",
            "wave_id": WAVE,
            "base_head": base_head,
            "coordination": "W02-13 only: typed structured-output validation and fragmented tool-call assembly as inert data. No tool execution, W02-14 fallback, provider egress, parity promotion, denominator mutation or W02 closure.",
            "scope": [
                "sessions/20260921-w02-structured/**",
                "adapters/openjarvis/streaming_inference.py",
                "adapters/openjarvis/structured_output.py",
                "tests/test_cp03_w02_structured_output.py",
                "tests/test_cp03_w02_streaming.py",
                "scripts/cp03/finalize_w02_structured.py",
                ".github/workflows/cp03-w02-structured.yml",
                "iterations/03/waves/CP03-W02/TASK_GRAPH.json",
                "evidence/cp03/cp03-w02/W02-13/**",
                "ledgers/CLAIM_LEDGER.ndjson",
                "ledgers/EVIDENCE_LEDGER.ndjson",
                "ledgers/RUN_LOG.ndjson",
                "ledgers/WAVE_LEDGER.ndjson",
                "ledgers/DECISION_LEDGER.ndjson",
                "ledgers/RISK_LEDGER.ndjson",
                "STATE.md",
                "HANDOFF.md",
                ".agentic/context/CURRENT_CONTEXT.json",
                ".agentic/context/CURRENT_CONTEXT.md"
            ],
        }, sort_keys=True, separators=(",", ":")) + "\n")


def update_handoff() -> None:
    path = ROOT / "HANDOFF.md"
    text = path.read_text(encoding="utf-8")
    evidence_line = (
        "- W02-13 partial G4 evidence: `EVID-W02-STRUCTURED-CORE-20260921`; "
        "fragmented OpenJarvis tool-call arguments assemble into bounded typed inert data, "
        "malformed JSON/schema violations fail closed, malicious tool names are preserved without execution, "
        "and targeted + streaming/cancellation/contract + kernel security regressions pass on the exact head. "
        "This is not W02-13 completion: canonical AdapterFrame/sidecar transport for typed tool/structured data remains unimplemented."
    )
    anchor = "- W02-12 G4 evidence: `EVID-W02-CANCELLATION-20260921`; request/attempt-scoped cancellation distinguishes REQUESTED → ACK → CANCELLED terminal, cancel-before/during PASS, already-terminal REJECTED, ACK-without-termination fails closed, explicit single-flight PASS; local worker cessation PASS; remote/provider cancellation effect remains UNKNOWN; provider egress 0; parity promotions 0."
    if evidence_line not in text:
        if anchor not in text:
            raise RuntimeError("HANDOFF W02-12 evidence anchor missing")
        text = text.replace(anchor, anchor + "\n" + evidence_line, 1)

    old = '''## Next executable\n\n`W02-13 — Structured output y tools`.\n\nW02-12 is evidence-backed COMPLETE and does not close W02. W02-13 is the sole READY G4 frontier. Cancellation proves local cessation only after a correlated ACK and CANCELLED terminal; provider/remote cancellation effect remains UNKNOWN and is not promoted. W02-14+ remain BLOCKED by the one-frontier DAG policy.'''
    new = '''## Next executable\n\n`W02-13 — Structured output y tools` (`IN_PROGRESS`).\n\nThe bounded decoder/validator core is now evidence-backed, but W02-13 is intentionally not COMPLETE. The exact next sub-slice is to extend the canonical inference transport so assembled tool calls and validated structured output cross AdapterFrame/sidecar as typed data without metadata encoding, then re-run G4 exact-head tests. W02-14+ remain BLOCKED; no parity promotion or denominator change occurred.'''
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise RuntimeError("HANDOFF W02-13 frontier anchor missing")
    path.write_text(text, encoding="utf-8")


def update_state() -> None:
    path = ROOT / "STATE.md"
    text = path.read_text(encoding="utf-8")
    old = '- Canonical task frontier: `W02-13 — Structured output y tools` (`READY`)\n'
    new = '- Canonical task frontier: `W02-13 — Structured output y tools` (`IN_PROGRESS`)\n'
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise RuntimeError("STATE W02-13 frontier anchor missing")
    path.write_text(text, encoding="utf-8")


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
        "status": "PARTIAL_PASS",
        "validated_head": head,
        "github_actions_run_id": run_id,
        "red_run_id": 35648078142,
        "fragmented_tool_arguments": "PASS",
        "invalid_tool_arguments": "FAIL_CLOSED",
        "malicious_tool_name_execution": "ZERO_EXECUTION",
        "structured_json_schema_validation": "PASS",
        "invalid_structured_json": "FAIL_CLOSED",
        "canonical_typed_transport": "NOT_RUN",
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
    if plan["first_executable_task"] != TASK:
        raise RuntimeError("W02-13 is not the exact canonical frontier")
    if task["status"] not in {"READY", "IN_PROGRESS"} or task["proof"]:
        raise RuntimeError("W02-13 pre-transition state invalid")
    if not all(tasks[dep]["status"] == "COMPLETE" and tasks[dep]["proof"] for dep in task["depends_on"]):
        raise RuntimeError("W02-13 dependency proof missing")
    if tasks[NEXT]["status"] != "BLOCKED" or tasks[NEXT]["proof"]:
        raise RuntimeError("W02-14 must remain BLOCKED during this partial W02-13 wave")

    session_claim = read_json("sessions/20260921-w02-structured/CLAIM.json")
    if session_claim.get("claim_id") != CLAIM or session_claim.get("status") != "ACTIVE":
        raise RuntimeError("session W02-13 claim is not ACTIVE")
    base_head = session_claim.get("base_head")
    if base_head != "c46aca03854e227e236f421d784c05e50691aee9":
        raise RuntimeError("W02-13 claim base head drift")
    ensure_claim_record(base_head)

    task["status"] = "IN_PROGRESS"
    # Deliberately no proof entry: the canonical transport part of W02-13 is NOT_RUN.
    plan["first_executable_task"] = TASK
    write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

    write_json("evidence/cp03/cp03-w02/W02-13/partial_receipt.json", receipt)
    report = dict(receipt)
    report.update({
        "date": DATE,
        "evidence_id": EVIDENCE,
        "support_wave": WAVE,
        "task_status": "IN_PROGRESS",
        "next_task": TASK,
        "next_subslice": "Canonical typed AdapterFrame/sidecar transport for assembled tool calls and validated structured output; no metadata encoding and no execution authority.",
        "note": "Evidence proves the bounded decoder/validator core and inert typed sink only. canonical_typed_transport remains NOT_RUN, so W02-13 stays IN_PROGRESS and W02-14 stays BLOCKED.",
    })
    write_json("evidence/cp03/cp03-w02/W02-13/report.json", report)
    write_json("sessions/20260921-w02-structured/RESULT.json", {
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
        "next_subslice": "canonical typed transport for W02-13",
    })
    session_claim["validated_head"] = head
    session_claim["last_evidence_id"] = EVIDENCE
    write_json("sessions/20260921-w02-structured/CLAIM.json", session_claim)

    append_unique("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE, {
        "schema_version": 1,
        "date": DATE,
        "evidence_id": EVIDENCE,
        "status": "VERIFIED",
        "type": "cp03_w02_structured_core_partial",
        "wave_id": "CP03-W02",
        "support_wave": WAVE,
        "github_actions_run_id": run_id,
        "validated_head": head,
        "red_run_id": 35648078142,
        "fragmented_tool_arguments": "PASS",
        "invalid_tool_arguments": "FAIL_CLOSED",
        "malicious_tool_name_execution": "ZERO_EXECUTION",
        "structured_json_schema_validation": "PASS",
        "invalid_structured_json": "FAIL_CLOSED",
        "canonical_typed_transport": "NOT_RUN",
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "claim": "Exact-head tests verify bounded typed assembly/validation as inert model data. This evidence explicitly does not prove canonical AdapterFrame/sidecar transport and does not complete W02-13.",
    })
    append_unique("ledgers/RUN_LOG.ndjson", "event_id", "RUN-W02-STRUCTURED-CORE-20260921", {
        "schema_version": 1,
        "date": DATE,
        "event_id": "RUN-W02-STRUCTURED-CORE-20260921",
        "event": "CP03_W02_STRUCTURED_CORE_ADVANCED",
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
    append_unique("ledgers/WAVE_LEDGER.ndjson", "event_id", "WAVE-W02-STRUCTURED-CORE-20260921", {
        "schema_version": 1,
        "date": DATE,
        "event_id": "WAVE-W02-STRUCTURED-CORE-20260921",
        "wave_id": WAVE,
        "parent_wave": "CP03-W02",
        "iteration": "I03",
        "checkpoint": "CP03",
        "event": "IMPLEMENTATION_VERIFICATION",
        "status": "IN_PROGRESS",
        "evidence_id": EVIDENCE,
        "next_task": TASK,
    })
    append_unique("ledgers/DECISION_LEDGER.ndjson", "decision_id", "D-0019", {
        "schema_version": 1,
        "date": DATE,
        "decision_id": "D-0019",
        "status": "ACCEPTED",
        "decision": "Model-emitted tool calls remain bounded inert data. Fragmented function arguments are assembled and JSON-validated, malicious names are preserved rather than executed or normalized into authority, and structured JSON is validated against a caller-supplied Draft 2020-12 schema without repair.",
        "context": "W02-13 must preserve OpenJarvis rich streaming semantics without allowing model output to become a tool-execution permission channel. Canonical transport is intentionally left NOT_RUN until a typed additive contract is implemented.",
        "evidence_id": EVIDENCE,
    })
    append_unique("ledgers/RISK_LEDGER.ndjson", "risk_id", "RISK-0013", {
        "schema_version": 1,
        "date": DATE,
        "risk_id": "RISK-0013",
        "status": "OPEN",
        "severity": "HIGH",
        "risk": "The W02-13 decoder/validator core is implemented, but assembled tool calls and validated structured output are not yet carried through the canonical AdapterFrame/sidecar wire path.",
        "mitigation": "Keep W02-13 IN_PROGRESS and W02-14 BLOCKED. Next sub-slice must extend the canonical inference contract additively, regenerate all language bindings, wire sidecar/kernel transport, and prove exact-head round trips without metadata encoding or tool execution.",
        "evidence_id": EVIDENCE,
    })

    update_handoff()
    update_state()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
