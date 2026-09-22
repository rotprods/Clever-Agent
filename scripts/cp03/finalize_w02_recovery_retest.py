from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.cp03.w02_recovery_retest import validate_report

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-16"
CLAIM = "CLAIM-CP03-W02-RECOVERY-PERF-20260922"
EVIDENCE = "EVID-W02-RECOVERY-RETEST-20260922"
WAVE = "CP03-W02-RETEST-RECOVERY-20260922"


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
    report_path = Path(os.environ.get("W02_RECOVERY_REPORT", "/tmp/w02-16-recovery-report.json"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    validate_report(report, require_pass=True)
    if report.get("source_head") != validated_head:
        raise RuntimeError("recovery report is not bound to exact tested head")

    graph = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    tasks = {row["id"]: row for row in graph["tasks"]}
    if graph["first_executable_task"] != TASK:
        raise RuntimeError(f"unexpected DAG frontier: {graph['first_executable_task']}")
    if tasks[TASK]["status"] != "READY" or tasks[TASK].get("proof"):
        raise RuntimeError("W02-16 must remain unproved READY during P02 partial evidence persistence")
    if tasks[TASK]["depends_on"] != ["W02-15"] or tasks["W02-15"]["status"] != "COMPLETE":
        raise RuntimeError("W02-16 dependency drift")
    if tasks["W02-17"]["status"] != "BLOCKED" or tasks["W02-17"].get("proof"):
        raise RuntimeError("W02-17 must remain BLOCKED until full W02-16 completion")
    if graph["global_denominator"] != 7565 or graph["openjarvis_obligations"] != 646 or graph.get("w02_obligation_count") != 47:
        raise RuntimeError("denominator/obligation drift")
    goal = read_json("GOAL_STATE.json")
    if goal["parity"]["total"] != 7565 or goal["parity"]["verified"] != 0:
        raise RuntimeError("parity drift")

    durable = dict(report)
    durable.update(
        {
            "checkpoint": "CP03",
            "date": "2026-09-22",
            "evidence_id": EVIDENCE,
            "github_actions_run_id": run_id,
            "status": "PASS",
            "task_status_after_wave": "READY",
            "next_task": TASK,
            "next_subslice": "P01_SAME_HOST_PERFORMANCE_BASELINE",
            "w02_17_status": "BLOCKED",
        }
    )
    write_json("evidence/cp03/cp03-w02/W02-16/recovery_retest_report.json", durable)

    claim = read_json("sessions/20260922-w02-recovery-performance/CLAIM.json")
    if claim.get("claim_id") != CLAIM or claim.get("status") != "ACTIVE":
        raise RuntimeError("active W02-16 recovery claim missing")
    if claim.get("base_head") != "4b8923973a3d6bb2a74d8d846e00db79c8aabec3":
        raise RuntimeError("W02-16 claim base drift")
    claim["status"] = "RELEASED"
    claim["last_evidence_id"] = EVIDENCE
    claim["validated_head"] = validated_head
    claim["release_run_id"] = run_id
    write_json("sessions/20260922-w02-recovery-performance/CLAIM.json", claim)
    write_json(
        "sessions/20260922-w02-recovery-performance/RESULT.json",
        {
            "claim_id": CLAIM,
            "date": "2026-09-22",
            "evidence_id": EVIDENCE,
            "github_actions_run_id": run_id,
            "next_task": TASK,
            "next_subslice": "P01_SAME_HOST_PERFORMANCE_BASELINE",
            "performance_baseline_same_host": "NOT_RUN",
            "result": "ADVANCED_PARTIAL",
            "task": TASK,
            "task_status": "READY",
            "w02_17_status": "BLOCKED",
            "validated_head": validated_head,
        },
    )

    append_unique(
        "ledgers/EVIDENCE_LEDGER.ndjson",
        "evidence_id",
        EVIDENCE,
        {
            "claim": "Exact-head G5 P02 recovery/flakiness sub-slice executed the fixed cancel/flood/restart matrix for all 20 repetitions and retained every result without selecting a favorable rerun. This is partial W02-16 evidence only: the P01 same-host performance baseline remains NOT_RUN, so W02-16 remains READY and W02-17 remains BLOCKED.",
            "date": "2026-09-22",
            "evidence_id": EVIDENCE,
            "failed_invocations": 0,
            "gate": "G5",
            "global_denominator": 7565,
            "model_executions": 0,
            "openjarvis_obligations": 646,
            "parity_promotions": 0,
            "performance_baseline_same_host": "NOT_RUN",
            "provider_egress_executions": 0,
            "repetitions": 20,
            "result": "PASS_PARTIAL",
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
        "RUN-W02-RECOVERY-RETEST-20260922",
        {
            "checkpoint": "CP03",
            "date": "2026-09-22",
            "event": "CP03_W02_RECOVERY_RETEST_ADVANCED",
            "event_id": "RUN-W02-RECOVERY-RETEST-20260922",
            "evidence_id": EVIDENCE,
            "goal_id": "CLEVER-JARVIS-001",
            "iteration": "I03",
            "next_subslice": "P01_SAME_HOST_PERFORMANCE_BASELINE",
            "next_task": TASK,
            "result": "ADVANCED_PARTIAL",
            "run_id": run_id,
            "validated_head": validated_head,
        },
    )
    append_unique(
        "ledgers/WAVE_LEDGER.ndjson",
        "event_id",
        "WAVE-W02-RECOVERY-RETEST-20260922-COMPLETE",
        {
            "canonical_task": TASK,
            "checkpoint": "CP03",
            "date": "2026-09-22",
            "event": "COMPLETE",
            "event_id": "WAVE-W02-RECOVERY-RETEST-20260922-COMPLETE",
            "evidence_id": EVIDENCE,
            "next_subslice": "P01_SAME_HOST_PERFORMANCE_BASELINE",
            "next_task": TASK,
            "parent_wave": "CP03-W02",
            "result": "PASS_PARTIAL",
            "run_id": run_id,
            "task_status": "READY",
            "validated_head": validated_head,
            "wave_id": WAVE,
        },
    )
    append_unique(
        "ledgers/CLAIM_LEDGER.ndjson",
        "event_id",
        "CLAIM-W02-RECOVERY-PERF-20260922-RELEASE",
        {
            "canonical_task": TASK,
            "checkpoint": "CP03",
            "claim_id": CLAIM,
            "coordination": "P02 recovery/flakiness evidence is persisted and the bounded sub-wave is complete. Release the claim because P01 performance was deliberately NOT_RUN; W02-16 remains READY and W02-17 remains BLOCKED.",
            "date": "2026-09-22",
            "event": "RELEASE",
            "event_id": "CLAIM-W02-RECOVERY-PERF-20260922-RELEASE",
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
        "DEC-W02-RECOVERY-RETEST-BUDGET-20260922",
        {
            "context": "W02-16 G5 P02 recovery/flakiness retest.",
            "date": "2026-09-22",
            "decision": "Freeze the P02 retest budget at 20 deterministic repetition IDs over cancellation, frame flood, byte flood and restart-budget probes; retain every invocation result and forbid best-rerun selection. P02 evidence cannot be used to claim P01 performance.",
            "decision_id": "DEC-W02-RECOVERY-RETEST-BUDGET-20260922",
            "evidence_id": EVIDENCE,
            "status": "ACCEPTED",
            "task": TASK,
        },
    )
    append_unique(
        "ledgers/RISK_LEDGER.ndjson",
        "risk_id",
        "RISK-W02-PERFORMANCE-BASELINE-PENDING-20260922",
        {
            "date": "2026-09-22",
            "evidence_id": EVIDENCE,
            "mitigation": "Keep W02-16 READY and W02-17 BLOCKED until P01 executes a fixed-budget direct-vs-adapted same-host baseline and records latency, TTFT, memory and throughput without changing the measured budget post hoc.",
            "risk": "The P02 recovery retest does not measure the required P01 same-host performance baseline; treating recovery stability as performance evidence would create a false-green G5 closure.",
            "risk_id": "RISK-W02-PERFORMANCE-BASELINE-PENDING-20260922",
            "severity": "P2",
            "status": "OPEN",
            "task": TASK,
        },
    )

    handoff_path = ROOT / "HANDOFF.md"
    handoff = handoff_path.read_text(encoding="utf-8")
    old = "`W02-16 — Retest recovery performance` (`READY`).\n\nW02-15 is evidence-backed COMPLETE. The next and only READY DAG frontier is W02-16; W02-17+ remain BLOCKED. No parity promotion, denominator mutation, provider egress, model execution, or tool execution occurred in the W02-15 security closure."
    new = "`W02-16 — Retest recovery performance` (`READY`).\n\nW02-16 P02 recovery/flakiness retest is evidence-backed PASS across all 20 fixed repetitions, with every cancel/flood/restart result retained and no favorable-rerun selection. P01 same-host performance remains `NOT_RUN`, so W02-16 stays the only READY DAG frontier and W02-17+ remain BLOCKED. No parity promotion, denominator mutation, provider egress, model execution, tool execution, or performance claim occurred in this partial W02-16 wave."
    if old in handoff:
        handoff = handoff.replace(old, new, 1)
    elif new not in handoff:
        raise RuntimeError("HANDOFF W02-16 next-task anchor missing")
    marker = "## W02-16 recovery retest — PARTIAL"
    if marker not in handoff:
        handoff = handoff.rstrip() + f"\n\n{marker}\n\n- Evidence: `{EVIDENCE}` on exact tested head `{validated_head}` / run `{run_id}`.\n- P02: 20/20 fixed repetitions executed; cancellation, frame-flood, byte-flood and crash/restart-budget probes all PASS; all 80 invocation records retained; failed invocations 0; no best-rerun selection.\n- P01 same-host direct-vs-adapted performance: `NOT_RUN`; latency/TTFT/memory/throughput are therefore not claimed.\n- Provider egress 0; model executions 0; tool executions 0; parity promotions 0; denominator 7565; OpenJarvis obligations 646.\n- Claim `{CLAIM}` released at the end of this bounded sub-wave. `W02-16` remains `READY`; `W02-17` remains `BLOCKED`.\n- Exact next sub-slice: W02-16 P01 fixed-budget same-host performance baseline.\n"
    handoff_path.write_text(handoff, encoding="utf-8")


if __name__ == "__main__":
    main()
