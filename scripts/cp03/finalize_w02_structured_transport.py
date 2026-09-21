from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-13"
NEXT = "W02-14"
CLAIM = "CLAIM-CP03-W02-STRUCTURED-20260921"
WAVE = "CP03-W02-STRUCTURED-20260921"
EVIDENCE = "EVID-W02-STRUCTURED-TRANSPORT-CANDIDATE-20260922"
DATE = "2026-09-22"


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


def update_handoff(validated_head: str) -> None:
    path = ROOT / "HANDOFF.md"
    text = path.read_text(encoding="utf-8")
    marker = "- W02-13 typed-transport candidate evidence:"
    line = (
        f"{marker} `{EVIDENCE}`; explicit protobuf fields now carry caller-schema-validated "
        "structured JSON and fully assembled model-emitted tool calls through InferenceTerminal/AdapterFrame, "
        "the kernel accepts and validates the typed terminal without executing it, generated SDK round trips "
        f"and G4 regressions are green on exact code HEAD `{validated_head}`. This remains candidate evidence: "
        "W02-13 stays IN_PROGRESS until canonical merge/post-merge qualification; W02-14 stays BLOCKED."
    )
    if marker not in text:
        anchor = "- W02-13 partial G4 evidence: `EVID-W02-STRUCTURED-CORE-20260921`; fragmented OpenJarvis tool-call arguments assemble into bounded typed inert data, malformed JSON/schema violations fail closed, malicious tool names are preserved without execution, and targeted + streaming/cancellation/contract + kernel security regressions pass on the exact head. This is not W02-13 completion: canonical AdapterFrame/sidecar transport for typed tool/structured data remains unimplemented."
        if anchor not in text:
            raise RuntimeError("HANDOFF W02-13 partial evidence anchor missing")
        text = text.replace(anchor, anchor + "\n" + line, 1)

    old = (
        "The bounded decoder/validator core is now evidence-backed, but W02-13 is intentionally not COMPLETE. "
        "The exact next sub-slice is to extend the canonical inference transport so assembled tool calls and validated structured output cross AdapterFrame/sidecar as typed data without metadata encoding, then re-run G4 exact-head tests. "
        "W02-14+ remain BLOCKED; no parity promotion or denominator change occurred."
    )
    new = (
        "The canonical W02-13 typed-transport candidate is now exact-head evidence-backed on its claimed branch: "
        "assembled tool calls and caller-schema-validated structured output cross InferenceTerminal/AdapterFrame and the kernel as inert typed data, with zero tool execution. "
        "W02-13 intentionally remains IN_PROGRESS until merge/post-merge qualification on canonical `main`. "
        "The exact next sub-slice is release qualification of this candidate; W02-14+ remain BLOCKED, parity remains 0/7,565, and the denominator is unchanged."
    )
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise RuntimeError("HANDOFF W02-13 next-subslice anchor missing")
    path.write_text(text, encoding="utf-8")


def update_state() -> None:
    path = ROOT / "STATE.md"
    text = path.read_text(encoding="utf-8")
    frontier = '- Canonical task frontier: `W02-13 — Structured output y tools` (`IN_PROGRESS`)\n'
    if frontier not in text:
        raise RuntimeError("STATE W02-13 frontier anchor missing")
    evidence_line = f"- Active candidate evidence: `{EVIDENCE}`; merge/post-merge qualification still required before COMPLETE.\n"
    if evidence_line not in text:
        text = text.replace(frontier, frontier + evidence_line, 1)
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
        "status": "PASS_PENDING_CANONICAL_MERGE",
        "validated_head": head,
        "github_actions_run_id": run_id,
        "canonical_typed_transport": "PASS",
        "adapter_frame_roundtrip": "PASS",
        "kernel_typed_terminal": "PASS",
        "structured_schema_validation": "PASS",
        "fragmented_tool_assembly": "PASS",
        "malicious_tool_name_execution": "ZERO_EXECUTION",
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

    evidence_path = ROOT / "evidence/cp03/cp03-w02/W02-13/typed_transport_candidate.json"
    if evidence_path.exists():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("evidence_id") != EVIDENCE:
            raise RuntimeError("typed transport evidence id drift")
        return 0

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
    if task["status"] != "IN_PROGRESS" or task["proof"]:
        raise RuntimeError("W02-13 must remain evidence-unpromoted IN_PROGRESS")
    if not all(tasks[dep]["status"] == "COMPLETE" and tasks[dep]["proof"] for dep in task["depends_on"]):
        raise RuntimeError("W02-13 dependency proof missing")
    if tasks[NEXT]["status"] != "BLOCKED" or tasks[NEXT]["proof"]:
        raise RuntimeError("W02-14 must remain BLOCKED before canonical merge qualification")

    claim = read_json("sessions/20260921-w02-structured/CLAIM.json")
    if claim.get("claim_id") != CLAIM or claim.get("status") != "ACTIVE":
        raise RuntimeError("W02-13 claim is not ACTIVE")
    latest_claim = {}
    for row in rows("ledgers/CLAIM_LEDGER.ndjson"):
        claim_id = row.get("claim_id")
        status = row.get("status")
        if isinstance(claim_id, str) and isinstance(status, str):
            latest_claim[claim_id] = status
    conflicts = sorted(cid for cid, status in latest_claim.items() if status == "ACTIVE" and cid != CLAIM)
    if conflicts:
        raise RuntimeError(f"conflicting active claims: {conflicts}")

    code_phase = read_json("evidence/cp03/cp03-w02/W02-13/typed_transport_code_phase.json")
    if code_phase.get("status") != "CODE_PERSISTED_AFTER_GREEN_PRECOMMIT" or not code_phase.get("code_commit_parent"):
        raise RuntimeError("typed transport code-phase evidence is missing")

    evidence = dict(receipt)
    evidence.update({
        "schema_version": 1,
        "date": DATE,
        "evidence_id": EVIDENCE,
        "support_wave": WAVE,
        "task_status": "IN_PROGRESS",
        "promotion_status": "PENDING_CANONICAL_MERGE",
        "red_gate": code_phase.get("red_gate"),
        "code_phase_run_id": code_phase.get("github_actions_run_id"),
        "note": "Exact-head G4 verifies canonical typed transport on the claimed branch. This does not promote parity or complete W02-13 before canonical merge/post-merge qualification.",
    })
    write_json("evidence/cp03/cp03-w02/W02-13/typed_transport_candidate.json", evidence)

    report = read_json("evidence/cp03/cp03-w02/W02-13/report.json")
    report.update({
        "typed_transport_candidate_evidence_id": EVIDENCE,
        "typed_transport_candidate_validated_head": head,
        "canonical_typed_transport": "PASS_PENDING_CANONICAL_MERGE",
        "task_status": "IN_PROGRESS",
        "next_task": TASK,
        "next_subslice": "Merge/requalify the W02-13 typed transport candidate on canonical main; only then may W02-13 become COMPLETE and W02-14 become READY.",
    })
    write_json("evidence/cp03/cp03-w02/W02-13/report.json", report)

    append_unique("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE, {
        "schema_version": 1,
        "date": DATE,
        "evidence_id": EVIDENCE,
        "status": "VERIFIED",
        "type": "cp03_w02_structured_typed_transport_candidate",
        "wave_id": "CP03-W02",
        "support_wave": WAVE,
        "github_actions_run_id": run_id,
        "validated_head": head,
        "canonical_typed_transport": "PASS",
        "adapter_frame_roundtrip": "PASS",
        "kernel_typed_terminal": "PASS",
        "structured_schema_validation": "PASS",
        "fragmented_tool_assembly": "PASS",
        "malicious_tool_name_execution": "ZERO_EXECUTION",
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "claim": "Typed structured/tool data crosses the canonical inference protobuf and kernel as inert data on the exact claimed branch head. Candidate evidence only; canonical merge/post-merge qualification is still required before task completion.",
    })
    append_unique("ledgers/RUN_LOG.ndjson", "event_id", "RUN-W02-STRUCTURED-TRANSPORT-CANDIDATE-20260922", {
        "schema_version": 1,
        "date": DATE,
        "event_id": "RUN-W02-STRUCTURED-TRANSPORT-CANDIDATE-20260922",
        "event": "CP03_W02_STRUCTURED_TRANSPORT_CANDIDATE_VERIFIED",
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
    append_unique("ledgers/WAVE_LEDGER.ndjson", "event_id", "WAVE-W02-STRUCTURED-TRANSPORT-CANDIDATE-20260922", {
        "schema_version": 1,
        "date": DATE,
        "event_id": "WAVE-W02-STRUCTURED-TRANSPORT-CANDIDATE-20260922",
        "wave_id": WAVE,
        "parent_wave": "CP03-W02",
        "iteration": "I03",
        "checkpoint": "CP03",
        "event": "IMPLEMENTATION_VERIFICATION",
        "status": "IN_PROGRESS",
        "evidence_id": EVIDENCE,
        "next_task": TASK,
    })
    append_unique("ledgers/DECISION_LEDGER.ndjson", "decision_id", "D-0020", {
        "schema_version": 1,
        "date": DATE,
        "decision_id": "D-0020",
        "status": "ACCEPTED",
        "decision": "Carry W02-13 structured output and model-emitted tool calls in explicit inference protobuf fields on InferenceTerminal. response_schema_json is caller-authored configuration; tool calls remain inert data and never imply execution authority.",
        "context": "Metadata encoding would erase type boundaries and risk conflating model output with authorization. Explicit additive fields preserve transport truth across generated SDKs and the kernel.",
        "evidence_id": EVIDENCE,
    })
    append_unique("ledgers/RISK_LEDGER.ndjson", "risk_id", "RISK-0014", {
        "schema_version": 1,
        "date": DATE,
        "risk_id": "RISK-0014",
        "status": "MITIGATING",
        "severity": "HIGH",
        "risk": "Downstream code could mistake model-emitted typed tool-call data for permission to execute a tool.",
        "mitigation": "Inference transport exposes only inert protobuf data; the bridge performs no registry lookup or execution, kernel validates identity/shape, and execution remains reserved for a separate policy/action path.",
        "evidence_id": EVIDENCE,
    })
    append_unique("ledgers/CLAIM_LEDGER.ndjson", "evidence_id", EVIDENCE, {
        "schema_version": 1,
        "date": DATE,
        "event": "EVIDENCE_LINKED",
        "claim_id": CLAIM,
        "owner": "chatgpt-gpt-5.6-sol",
        "status": "ACTIVE",
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "canonical_task": TASK,
        "parent_wave": "CP03-W02",
        "wave_id": WAVE,
        "evidence_id": EVIDENCE,
        "validated_head": head,
        "coordination": "Typed transport candidate is exact-head verified on the claimed branch; claim remains ACTIVE until canonical merge/post-merge qualification. No W02-14 work, parity promotion, denominator mutation, provider egress, or tool execution.",
    })

    claim["last_evidence_id"] = EVIDENCE
    claim["transport_validated_head"] = head
    write_json("sessions/20260921-w02-structured/CLAIM.json", claim)
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
        "next_subslice": "canonical merge/post-merge qualification of typed transport candidate",
    })
    update_state()
    update_handoff(head)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
