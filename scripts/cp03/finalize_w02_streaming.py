from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-11"
NEXT = "W02-12"
CLAIM = "CLAIM-CP03-W02-STREAMING-20260921"
EVIDENCE = "EVID-W02-STREAMING-20260921"
WAVE = "CP03-W02-STREAMING-20260921"
MERGED_RUNTIME_HEAD = "8657b8c8b5246a6c611c7eea9dc59796bcc13a98"
PREMERGE_RUN = 35590345760
PR_RUN = 35590473694


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
    text = text.replace('- COMPLETE: `W02-00..W02-10`.', '- COMPLETE: `W02-00..W02-11`.')
    unary = '- W02-10 G3 evidence: `EVID-W02-UNARY-INFERENCE-20260921`; one real model execution, correlated unary chunk+terminal, provider egress 0, tool executions 0, parity promotions 0.'
    streaming = '- W02-11 G4 evidence: `EVID-W02-STREAMING-20260921`; native `stream_full` bridge semantics + fragmented/coalesced canonical transport PASS; duplicate/reordered/EOF-before-terminal paths fail closed; provider egress 0; parity promotions 0.'
    if streaming not in text:
        if unary not in text:
            raise RuntimeError("HANDOFF unary evidence anchor missing")
        text = text.replace(unary, unary + "\n" + streaming, 1)
    old = '''## Next executable\n\n`W02-11 — Stream y stream_full`.\n\nW02-10/M1 is evidence-backed COMPLETE but does not close W02. W02-11 is the sole READY G4 frontier and must prove fragmented/coalesced streaming semantics, UTF-8 boundaries, sequence integrity and exactly one terminal without converting EOF, duplicates or reordering into false success. Cancellation and later G4 tasks remain BLOCKED by the DAG.'''
    new = '''## Next executable\n\n`W02-12 — Cancelación real`.\n\nW02-11 is evidence-backed COMPLETE and does not close W02. W02-12 is the sole READY G4 frontier. Cancellation itself remains NOT_RUN in the W02-11 evidence and must now be proven end-to-end without treating process teardown, EOF, timeout, or synthetic STOPPING as cancellation success. Later G4 tasks remain BLOCKED by the DAG.'''
    if old not in text:
        raise RuntimeError("HANDOFF W02-11 frontier anchor missing")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_state() -> None:
    path = ROOT / "STATE.md"
    text = path.read_text(encoding="utf-8")
    marker = '- Capability denominator: `7565`\n'
    frontier = '- Canonical task frontier: `W02-12 — Cancelación real` (`READY`)\n'
    if frontier not in text:
        if marker not in text:
            raise RuntimeError("STATE denominator anchor missing")
        text = text.replace(marker, marker + frontier, 1)
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
        "status": "PASS",
        "validated_head": head,
        "github_actions_run_id": run_id,
        "merged_runtime_head": MERGED_RUNTIME_HEAD,
        "premerge_gauntlet_run_id": PREMERGE_RUN,
        "pr_gauntlet_run_id": PR_RUN,
        "native_stream_full_bridge": "PASS",
        "fragmented_utf8_transport": "PASS",
        "coalesced_frame_transport": "PASS",
        "duplicate_sequence": "REJECTED",
        "reordered_sequence": "REJECTED",
        "eof_before_terminal": "REJECTED",
        "exactly_one_terminal": "PASS",
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "cancellation_executions": 0,
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
        raise RuntimeError("W02-11 is not the exact READY frontier")
    if not all(tasks[dep]["status"] == "COMPLETE" and tasks[dep]["proof"] for dep in task["depends_on"]):
        raise RuntimeError("W02-11 dependency proof missing")
    if latest_claim_status() != "ACTIVE":
        raise RuntimeError("W02-11 claim is not ACTIVE")

    task["status"] = "COMPLETE"
    task["proof"] = [{
        "evidence_id": EVIDENCE,
        "result": "PASS",
        "validated_head": head,
        "run_id": run_id,
        "gate": "G4",
        "merged_runtime_head": MERGED_RUNTIME_HEAD,
        "premerge_gauntlet_run_id": PREMERGE_RUN,
        "pr_gauntlet_run_id": PR_RUN,
        "native_stream_full_bridge": "PASS",
        "fragmented_utf8_transport": "PASS",
        "coalesced_frame_transport": "PASS",
        "duplicate_sequence": "REJECTED",
        "reordered_sequence": "REJECTED",
        "eof_before_terminal": "REJECTED",
        "exactly_one_terminal": "PASS",
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "cancellation_executions": 0,
        "parity_promotions": 0,
    }]

    next_task = tasks[NEXT]
    if next_task["status"] != "BLOCKED" or next_task["proof"]:
        raise RuntimeError("W02-12 pre-transition state invalid")
    if not all(tasks[dep]["status"] == "COMPLETE" and tasks[dep]["proof"] for dep in next_task["depends_on"]):
        raise RuntimeError("W02-12 dependencies are not evidence-backed COMPLETE")
    next_task["status"] = "READY"
    plan["first_executable_task"] = NEXT
    write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

    write_json("evidence/cp03/cp03-w02/W02-11/receipt.json", receipt)
    report = dict(receipt)
    report.update({
        "date": "2026-09-21",
        "evidence_id": EVIDENCE,
        "support_wave": WAVE,
        "next_task": NEXT,
        "note": "W02-11 proves bounded streaming semantics only. Cancellation, tools, fallback, provider egress and parity promotion are not proven here.",
    })
    write_json("evidence/cp03/cp03-w02/W02-11/report.json", report)
    write_json("sessions/20260921-w02-streaming/RESULT.json", {
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

    claim_path = "sessions/20260921-w02-streaming/CLAIM.json"
    claim = read_json(claim_path)
    claim["status"] = "RELEASED"
    claim["release_evidence_id"] = EVIDENCE
    write_json(claim_path, claim)

    append_unique("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE, {
        "schema_version": 1,
        "date": "2026-09-21",
        "evidence_id": EVIDENCE,
        "status": "VERIFIED",
        "type": "cp03_w02_bounded_streaming",
        "wave_id": "CP03-W02",
        "support_wave": WAVE,
        "github_actions_run_id": run_id,
        "validated_head": head,
        "merged_runtime_head": MERGED_RUNTIME_HEAD,
        "premerge_gauntlet_run_id": PREMERGE_RUN,
        "pr_gauntlet_run_id": PR_RUN,
        "native_stream_full_bridge": "PASS",
        "fragmented_utf8_transport": "PASS",
        "coalesced_frame_transport": "PASS",
        "duplicate_sequence": "REJECTED",
        "reordered_sequence": "REJECTED",
        "eof_before_terminal": "REJECTED",
        "exactly_one_terminal": "PASS",
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "cancellation_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "claim": "Exact-head G4 proves W02-11 stream_full bridging and canonical fragmented/coalesced transport fail-closed semantics; it does not prove cancellation, tools, fallback, provider egress or parity.",
    })
    append_unique("ledgers/RUN_LOG.ndjson", "event_id", "RUN-W02-STREAMING-20260921-COMPLETE", {
        "schema_version": 1,
        "date": "2026-09-21",
        "event_id": "RUN-W02-STREAMING-20260921-COMPLETE",
        "event": "CP03_W02_STREAMING_ADVANCED",
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
    append_unique("ledgers/WAVE_LEDGER.ndjson", "event_id", "WAVE-W02-STREAMING-20260921", {
        "schema_version": 1,
        "date": "2026-09-21",
        "event_id": "WAVE-W02-STREAMING-20260921",
        "wave_id": WAVE,
        "parent_wave": "CP03-W02",
        "iteration": "I03",
        "checkpoint": "CP03",
        "event": "VERIFICATION",
        "status": "COMPLETE",
        "evidence_id": EVIDENCE,
        "next_task": NEXT,
    })
    append_unique("ledgers/DECISION_LEDGER.ndjson", "decision_id", "D-0017", {
        "schema_version": 1,
        "date": "2026-09-21",
        "decision_id": "D-0017",
        "status": "ACCEPTED",
        "decision": "W02-11 streaming is strictly ordered from sequence 1, emits a terminal only after successful native iterator completion, and poisons protocol state on duplicate, reordered, EOF-before-terminal or invalid terminal behavior; typed/tool fragments remain deferred and fail closed.",
        "context": "Bound the G4 streaming lane without smuggling W02-12 cancellation or W02-13 structured/tool semantics into W02-11.",
        "evidence_id": EVIDENCE,
    })
    append_unique("ledgers/RISK_LEDGER.ndjson", "risk_id", "RISK-0011", {
        "schema_version": 1,
        "date": "2026-09-21",
        "risk_id": "RISK-0011",
        "status": "MITIGATING",
        "severity": "HIGH",
        "risk": "Passing stream_full bridge and framing adversarials can be misread as proof of cancellation, structured/tool streaming, fallback/provider effects or complete inference parity.",
        "mitigation": "Keep parity promotions at zero, record cancellation_executions=0, reject typed/tool fragments until W02-13, and open only W02-12 after W02-11 evidence is persisted.",
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
