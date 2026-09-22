from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-15"
NEXT = "W02-16"
CLAIM = "CLAIM-CP03-W02-SECURITY-20260922"
EVIDENCE = "EVID-W02-SECURITY-20260922"
WAVE = "CP03-W02-SECURITY-20260922"


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str, value: dict) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_unique(path: str, key: str, key_value: str, value: dict) -> None:
    target = ROOT / path
    rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
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
    if tasks[TASK]["status"] not in {"READY", "IN_PROGRESS"} or tasks[TASK].get("proof"):
        raise RuntimeError("W02-15 must be the unproved active frontier before finalization")
    if set(tasks[TASK]["depends_on"]) != {"W02-07", "W02-12", "W02-13", "W02-14"}:
        raise RuntimeError("W02-15 dependency drift")
    if any(tasks[dep]["status"] != "COMPLETE" for dep in tasks[TASK]["depends_on"]):
        raise RuntimeError("W02-15 dependency not complete")
    if tasks[NEXT]["status"] != "BLOCKED" or tasks[NEXT].get("proof"):
        raise RuntimeError("W02-16 must remain BLOCKED before W02-15 proof")

    goal = read_json("GOAL_STATE.json")
    if goal["parity"]["total"] != 7565 or goal["parity"]["verified"] != 0:
        raise RuntimeError("parity drift")

    red = read_json("sessions/20260922-w02-security/RED.json")
    if red.get("test") != "standalone_cancel_without_authority_context_must_fail_closed":
        raise RuntimeError("W02-15 RED test identity missing")
    if red.get("exit_code") == 0 or red.get("classification") != "SECURITY_REGRESSION_REPRODUCED":
        raise RuntimeError("W02-15 RED evidence does not prove the pre-fix defect")

    proof = {
        "cross_principal_cancel": "FAIL_CLOSED_PRE_TRANSPORT",
        "egress_injection_ssrf": "PASS",
        "evidence_id": EVIDENCE,
        "gate": "G5",
        "inbound_flood_bounds": "PASS",
        "model_executions": 0,
        "parity_promotions": 0,
        "privileged_registry_metadata": "FILTERED",
        "provider_egress_executions": 0,
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "result": "PASS",
        "run_id": run_id,
        "secret_canary_redaction": "PASS",
        "standalone_cancel_authority": "PASS",
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
    old = '- Canonical task frontier: `W02-15 — Regresión de seguridad` (`READY`)\n'
    old_in_progress = '- Canonical task frontier: `W02-15 — Regresión de seguridad` (`IN_PROGRESS`)\n'
    new = '- Canonical task frontier: `W02-16 — Retest recovery performance` (`READY`)\n'
    if old in state:
        state = state.replace(old, new, 1)
    elif old_in_progress in state:
        state = state.replace(old_in_progress, new, 1)
    elif new not in state:
        raise RuntimeError("STATE W02-15 frontier anchor missing")
    state_path.write_text(state, encoding="utf-8")

    report = {
        "checkpoint": "CP03",
        "cross_principal_cancel": "FAIL_CLOSED_PRE_TRANSPORT",
        "date": "2026-09-22",
        "denominator": 7565,
        "egress_injection_ssrf": "PASS",
        "evidence_id": EVIDENCE,
        "gate": "G5",
        "global_parity_verified": 0,
        "inbound_flood_bounds": "PASS",
        "model_executions": 0,
        "next_task": NEXT,
        "openjarvis_obligations": 646,
        "parity_promotions": 0,
        "privileged_registry_metadata": "FILTERED",
        "provider_egress_executions": 0,
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "red_characterization": red,
        "run_id": run_id,
        "secret_canary_redaction": "PASS",
        "standalone_cancel_authority": "PASS",
        "status": "PASS",
        "task": TASK,
        "tool_executions": 0,
        "validated_head": validated_head,
        "w02_proof_units": 47,
    }
    write_json("evidence/cp03/cp03-w02/W02-15/security_regression_report.json", report)

    claim = read_json("sessions/20260922-w02-security/CLAIM.json")
    if claim.get("claim_id") != CLAIM or claim.get("status") != "ACTIVE":
        raise RuntimeError("active W02-15 claim missing")
    if claim.get("base_head") != "9dee62f1493e1529a71e7dd705bd0acdbcf2d653":
        raise RuntimeError("W02-15 claim base drift")
    claim["status"] = "RELEASED"
    claim["last_evidence_id"] = EVIDENCE
    claim["validated_head"] = validated_head
    claim["release_run_id"] = run_id
    write_json("sessions/20260922-w02-security/CLAIM.json", claim)

    write_json(
        "sessions/20260922-w02-security/RESULT.json",
        {
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
        },
    )

    append_unique(
        "ledgers/EVIDENCE_LEDGER.ndjson",
        "evidence_id",
        EVIDENCE,
        {
            "claim": "Exact-head G5 security regression reproduces and closes the unauthenticated standalone cancellation surface: cancellation is now bound to the last supervised request/attempt plus exact canonical principal and session and cross-principal attempts fail before transport. Existing deny-by-default egress/SSRF, secret-redaction, privileged-metadata stripping and inbound flood bounds all remain green. No provider/model/tool execution or parity promotion occurred; the W02-14 real fallback model lane remains NOT_RUN.",
            "cross_principal_cancel": "FAIL_CLOSED_PRE_TRANSPORT",
            "date": "2026-09-22",
            "egress_injection_ssrf": "PASS",
            "evidence_id": EVIDENCE,
            "global_denominator": 7565,
            "inbound_flood_bounds": "PASS",
            "model_executions": 0,
            "openjarvis_obligations": 646,
            "parity_promotions": 0,
            "privileged_registry_metadata": "FILTERED",
            "provider_egress_executions": 0,
            "real_openjarvis_fallback_model_execution": "NOT_RUN",
            "result": "PASS",
            "run_id": run_id,
            "secret_canary_redaction": "PASS",
            "task": TASK,
            "tool_executions": 0,
            "validated_head": validated_head,
            "w02_proof_units": 47,
        },
    )
    append_unique(
        "ledgers/RUN_LOG.ndjson",
        "event_id",
        "RUN-W02-SECURITY-20260922-COMPLETE",
        {
            "checkpoint": "CP03",
            "date": "2026-09-22",
            "event": "CP03_W02_SECURITY_COMPLETE",
            "event_id": "RUN-W02-SECURITY-20260922-COMPLETE",
            "evidence_id": EVIDENCE,
            "goal_id": "CLEVER-JARVIS-001",
            "iteration": "I03",
            "next_task": NEXT,
            "parity_promotions": 0,
            "provider_egress_executions": 0,
            "run_id": run_id,
            "task": TASK,
            "tool_executions": 0,
            "validated_head": validated_head,
        },
    )
    append_unique(
        "ledgers/WAVE_LEDGER.ndjson",
        "event_id",
        "WAVE-W02-SECURITY-20260922-COMPLETE",
        {
            "canonical_task": TASK,
            "checkpoint": "CP03",
            "date": "2026-09-22",
            "event": "COMPLETE",
            "event_id": "WAVE-W02-SECURITY-20260922-COMPLETE",
            "evidence_id": EVIDENCE,
            "next_task": NEXT,
            "parent_wave": "CP03-W02",
            "parity_promotions": 0,
            "result": "PASS",
            "run_id": run_id,
            "validated_head": validated_head,
            "wave_id": WAVE,
        },
    )
    append_unique(
        "ledgers/CLAIM_LEDGER.ndjson",
        "event_id",
        "CLAIM-W02-SECURITY-20260922-RELEASE",
        {
            "canonical_task": TASK,
            "checkpoint": "CP03",
            "claim_id": CLAIM,
            "coordination": "Evidence-backed W02-15 G5 completion releases the security claim. W02-16 becomes READY but is not claimed or implemented by this wave.",
            "date": "2026-09-22",
            "event": "RELEASE",
            "event_id": "CLAIM-W02-SECURITY-20260922-RELEASE",
            "evidence_id": EVIDENCE,
            "owner": "chatgpt-gpt-5.6-sol",
            "parent_wave": "CP03-W02",
            "project_id": "CLEVER-JARVIS-001",
            "status": "RELEASED",
            "validated_head": validated_head,
            "wave_id": WAVE,
        },
    )
    append_unique(
        "ledgers/DECISION_LEDGER.ndjson",
        "decision_id",
        "DEC-W02-CANCEL-AUTHORITY-20260922",
        {
            "context": "W02-15 G5 unauthorized-cancel regression.",
            "date": "2026-09-22",
            "decision": "The public standalone inference-cancel path must be authorized inside the T0 AdapterSupervisor against ownership recorded from the supervised request. Exact request_id, attempt_id, canonical PrincipalRef and session_id must all match before any cancel frame is written; authorization rejection is local and does not poison the transport session.",
            "decision_id": "DEC-W02-CANCEL-AUTHORITY-20260922",
            "evidence_id": EVIDENCE,
            "status": "ACCEPTED",
            "task": TASK,
        },
    )
    append_unique(
        "ledgers/RISK_LEDGER.ndjson",
        "risk_id",
        "RISK-W02-UNAUTHORIZED-CANCEL-20260922",
        {
            "date": "2026-09-22",
            "evidence_id": EVIDENCE,
            "mitigation": "Bind standalone cancellation to the last supervised request ownership tuple and reject principal/session mismatch before transport; retain regression test that proves a rejected attacker cannot consume the peer cancel slot.",
            "risk": "The W02-12 standalone cancel API accepted only request_id/attempt_id/reason and therefore had no caller principal/session input, making cross-principal authorization impossible at the kernel boundary.",
            "risk_id": "RISK-W02-UNAUTHORIZED-CANCEL-20260922",
            "severity": "P1",
            "status": "MITIGATED",
            "task": TASK,
        },
    )

    handoff_path = ROOT / "HANDOFF.md"
    handoff = handoff_path.read_text(encoding="utf-8")
    old_next = "## Next executable\n\n`W02-15 — Regresión de seguridad` (`READY`).\n\nW02-14 is evidence-backed COMPLETE. The next and only READY DAG frontier is W02-15; W02-16+ remain BLOCKED. No parity promotion, denominator mutation, provider egress, model execution, or tool execution occurred in the W02-14 adapter closure.\n"
    new_next = "## Next executable\n\n`W02-16 — Retest recovery performance` (`READY`).\n\nW02-15 is evidence-backed COMPLETE. The next and only READY DAG frontier is W02-16; W02-17+ remain BLOCKED. No parity promotion, denominator mutation, provider egress, model execution, or tool execution occurred in the W02-15 security closure.\n"
    if old_next in handoff:
        handoff = handoff.replace(old_next, new_next, 1)
    elif new_next not in handoff:
        raise RuntimeError("HANDOFF next-task anchor missing")
    marker = "## W02-15 security — COMPLETE"
    if marker not in handoff:
        handoff = handoff.rstrip() + f'''\n\n{marker}\n\n- Evidence: `{EVIDENCE}` on exact tested head `{validated_head}` / run `{run_id}`.\n- RED characterization reproduced the gap: the standalone cancellation API had no caller authority context and could reach transport using only request/attempt identifiers.\n- T0 `AdapterSupervisor` now records the supervised streaming ownership tuple and requires exact request, attempt, canonical principal and session match before writing a standalone cancel frame. Cross-principal/tenant mismatch fails locally and does not poison the healthy transport.\n- G5 regression remains green for injected/noncanonical egress origins, grant cross-principal/session isolation, secret canary redaction, privileged registry metadata filtering and bounded inbound flood behavior.\n- Provider egress 0; model executions 0; tool executions 0; parity promotions 0; denominator 7565; OpenJarvis obligations 646. W02-14 real fallback model execution remains `NOT_RUN` and is not promoted.\n- Claim `{CLAIM}` is released. Exact next task: `W02-16 — Retest recovery performance` (G5), dependency W02-15 COMPLETE.\n'''
    handoff_path.write_text(handoff, encoding="utf-8")


if __name__ == "__main__":
    main()
