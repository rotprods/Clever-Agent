from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-13"
CLAIM = "CLAIM-CP03-W02-STRUCTURED-20260921"
EVIDENCE = "EVID-W02-STRUCTURED-CORE-20260921"
WAVE = "CP03-W02-STRUCTURED-20260921"


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


def update_state() -> None:
    path = ROOT / "STATE.md"
    text = path.read_text(encoding="utf-8")
    old = '- Canonical task frontier: `W02-13 — Structured output y tools` (`READY`)\n'
    new = '- Canonical task frontier: `W02-13 — Structured output y tools` (`IN_PROGRESS`)\n'
    if old not in text:
        if new in text:
            return
        raise RuntimeError("STATE W02-13 frontier anchor missing")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_handoff() -> None:
    path = ROOT / "HANDOFF.md"
    text = path.read_text(encoding="utf-8")
    anchor = '- W02-12 G4 evidence: `EVID-W02-CANCELLATION-20260921`; request/attempt-scoped cancellation distinguishes REQUESTED → ACK → CANCELLED terminal, cancel-before/during PASS, already-terminal REJECTED, ACK-without-termination fails closed, explicit single-flight PASS; local worker cessation PASS; remote/provider cancellation effect remains UNKNOWN; provider egress 0; parity promotions 0.'
    partial = '- W02-13 partial G4 evidence: `EVID-W02-STRUCTURED-CORE-20260921`; fragmented structured JSON and OpenAI-style tool-call argument assembly are strict, byte-bounded and JSON-Schema validated; duplicate keys, non-finite constants, identity mutation, undeclared tools and invalid schemas fail closed; tool executions 0; provider egress 0; parity promotions 0. Canonical typed transport/stream integration remains `NOT_RUN`, so W02-13 is **not COMPLETE**.'
    if partial not in text:
        if anchor not in text:
            raise RuntimeError("HANDOFF W02-12 evidence anchor missing")
        text = text.replace(anchor, anchor + "\n" + partial, 1)
    old = '''## Next executable\n\n`W02-13 — Structured output y tools`.\n\nW02-12 is evidence-backed COMPLETE and does not close W02. W02-13 is the sole READY G4 frontier. Cancellation proves local cessation only after a correlated ACK and CANCELLED terminal; provider/remote cancellation effect remains UNKNOWN and is not promoted. W02-14+ remain BLOCKED by the one-frontier DAG policy.'''
    new = '''## Next executable\n\n`W02-13 — Structured output y tools` (continue `IN_PROGRESS`).\n\nThe W02-13 core data layer is evidence-backed, but the task is intentionally not COMPLETE. Exact residual: carry structured-output/tool-call fragments through the canonical typed streaming transport without executing tools, prove schema/fragment semantics end-to-end, and retain fail-closed behavior. W02-14+ remain BLOCKED by the one-frontier DAG policy.'''
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise RuntimeError("HANDOFF W02-13 frontier anchor missing")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    head = os.environ["GITHUB_SHA"]
    run_id = int(os.environ["GITHUB_RUN_ID"])

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
        raise RuntimeError("W02-13 is not the exact clean READY frontier")
    if not all(tasks[dep]["status"] == "COMPLETE" and tasks[dep]["proof"] for dep in task["depends_on"]):
        raise RuntimeError("W02-13 dependency proof missing")
    if tasks["W02-14"]["status"] != "BLOCKED":
        raise RuntimeError("W02-14 must remain BLOCKED")
    if latest_claim_status() != "ACTIVE":
        raise RuntimeError("W02-13 claim is not ACTIVE")

    partial_proof = {
        "evidence_id": EVIDENCE,
        "result": "PARTIAL_PASS",
        "scope": "CORE_STRUCTURED_DATA_ONLY",
        "validated_head": head,
        "run_id": run_id,
        "gate": "G4",
        "targeted_tests": 8,
        "regression_tests": 33,
        "structured_json_assembly": "PASS",
        "tool_argument_fragment_assembly": "PASS",
        "json_schema_validation": "PASS",
        "duplicate_keys": "REJECTED",
        "non_finite_json": "REJECTED",
        "tool_identity_mutation": "REJECTED",
        "undeclared_tool": "REJECTED",
        "byte_budgets": "PASS",
        "tool_executions": 0,
        "provider_egress_executions": 0,
        "parity_promotions": 0,
        "canonical_transport_exposure": "NOT_RUN",
    }
    task["status"] = "IN_PROGRESS"
    task["proof"] = [partial_proof]
    plan["first_executable_task"] = TASK
    write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

    report = {
        "schema_version": 1,
        "date": "2026-09-21",
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "parent_wave": "CP03-W02",
        "support_wave": WAVE,
        "task": TASK,
        "gate": "G4",
        "status": "PARTIAL_PASS",
        "evidence_id": EVIDENCE,
        "validated_head": head,
        "github_actions_run_id": run_id,
        "targeted_tests": 8,
        "regression_tests": 33,
        "structured_json_assembly": "PASS",
        "tool_argument_fragment_assembly": "PASS",
        "json_schema_validation": "PASS",
        "duplicate_keys": "REJECTED",
        "non_finite_json": "REJECTED",
        "tool_identity_mutation": "REJECTED",
        "undeclared_tool": "REJECTED",
        "tool_executions": 0,
        "provider_egress_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "canonical_transport_exposure": "NOT_RUN",
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "next_task": TASK,
        "note": "Core W02-13 data assembly is verified only. Canonical typed stream/transport exposure remains NOT_RUN; W02-13 therefore remains IN_PROGRESS and W02-14 stays BLOCKED.",
    }
    write_json("evidence/cp03/cp03-w02/W02-13/core-slice-report.json", report)
    write_json("sessions/20260921-w02-structured/RESULT.json", {
        "schema_version": 1,
        "date": "2026-09-21",
        "claim_id": CLAIM,
        "wave_id": WAVE,
        "task": TASK,
        "status": "PARTIAL_PASS",
        "evidence_id": EVIDENCE,
        "validated_head": head,
        "github_actions_run_id": run_id,
        "next_task": TASK,
        "residual": "canonical typed structured/tool fragments over streaming transport",
    })

    claim_path = "sessions/20260921-w02-structured/CLAIM.json"
    claim = read_json(claim_path)
    claim["status"] = "RELEASED"
    claim["release_evidence_id"] = EVIDENCE
    write_json(claim_path, claim)

    append_unique("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE, {
        "schema_version": 1,
        "date": "2026-09-21",
        "evidence_id": EVIDENCE,
        "status": "VERIFIED_PARTIAL",
        "type": "cp03_w02_structured_core",
        "wave_id": "CP03-W02",
        "support_wave": WAVE,
        "github_actions_run_id": run_id,
        "validated_head": head,
        "targeted_tests": 8,
        "regression_tests": 33,
        "tool_executions": 0,
        "provider_egress_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "canonical_transport_exposure": "NOT_RUN",
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "claim": "Strict fragmented structured JSON and tool-call argument assembly/schema validation are proven as inert data only. Canonical typed streaming transport remains NOT_RUN, so W02-13 is not complete and no parity is promoted.",
    })
    append_unique("ledgers/RUN_LOG.ndjson", "event_id", "RUN-W02-STRUCTURED-CORE-20260921", {
        "schema_version": 1,
        "date": "2026-09-21",
        "event_id": "RUN-W02-STRUCTURED-CORE-20260921",
        "event": "CP03_W02_STRUCTURED_CORE_ADVANCED",
        "goal_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "iteration": "I03",
        "wave_id": "CP03-W02",
        "support_wave": WAVE,
        "status": "PARTIAL_PASS",
        "evidence_id": EVIDENCE,
        "next_task": TASK,
        "K": 47,
        "parity_promotions": 0,
    })
    append_unique("ledgers/WAVE_LEDGER.ndjson", "event_id", "WAVE-W02-STRUCTURED-CORE-20260921", {
        "schema_version": 1,
        "date": "2026-09-21",
        "event_id": "WAVE-W02-STRUCTURED-CORE-20260921",
        "wave_id": WAVE,
        "parent_wave": "CP03-W02",
        "iteration": "I03",
        "checkpoint": "CP03",
        "event": "PARTIAL_VERIFICATION",
        "status": "COMPLETE",
        "evidence_id": EVIDENCE,
        "next_task": TASK,
    })
    append_unique("ledgers/DECISION_LEDGER.ndjson", "decision_id", "D-0019", {
        "schema_version": 1,
        "date": "2026-09-21",
        "decision_id": "D-0019",
        "status": "ACCEPTED",
        "decision": "W02-13 decodes fragmented structured output and native tool-call arguments with strict JSON, byte budgets and Draft 2020-12 JSON Schema validation, but represents tool calls as inert data only and exposes no execution surface.",
        "context": "The upstream StreamChunk contract carries tool_calls/content_blocks/tool_results, while the canonical v1.2 InferenceChunk currently carries only text_delta. Core parsing can be proven independently without falsely claiming typed transport or tool execution.",
        "evidence_id": EVIDENCE,
    })
    append_unique("ledgers/RISK_LEDGER.ndjson", "risk_id", "RISK-0013", {
        "schema_version": 1,
        "date": "2026-09-21",
        "risk_id": "RISK-0013",
        "status": "OPEN",
        "severity": "HIGH",
        "risk": "Treating the verified W02-13 core parser as complete would hide the absence of canonical typed transport/stream integration and could create false structured/tool parity claims.",
        "mitigation": "Keep W02-13 IN_PROGRESS, canonical_transport_exposure=NOT_RUN, tool executions=0, parity promotions=0 and W02-14 BLOCKED until typed structured/tool fragments are carried and validated end-to-end over canonical transport.",
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

    update_state()
    update_handoff()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
