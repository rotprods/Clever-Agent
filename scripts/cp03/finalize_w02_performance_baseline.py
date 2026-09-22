from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cp03.w02_performance_baseline import validate

TASK = "W02-16"
NEXT = "W02-17"
CLAIM = "CLAIM-CP03-W02-PERFORMANCE-20260922"
EVIDENCE = "EVID-W02-PERFORMANCE-BASELINE-20260922"
WAVE = "CP03-W02-PERFORMANCE-BASELINE-20260922"


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str, value: dict) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append(path: str, value: dict) -> None:
    with (ROOT / path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def ensure_unique(path: str, key: str, value: str) -> None:
    rows=[json.loads(x) for x in (ROOT/path).read_text(encoding="utf-8").splitlines() if x.strip()]
    if any(row.get(key)==value for row in rows):
        raise RuntimeError(f"duplicate durable id {value} in {path}")


def main() -> None:
    tested_head = os.environ["GITHUB_SHA"]
    run_id = int(os.environ["GITHUB_RUN_ID"])
    report_path = Path(os.environ.get("W02_PERFORMANCE_REPORT", "/tmp/w02-16-performance-report.json"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    validate(report)
    if report.get("source_head") != tested_head:
        raise RuntimeError("performance report is not bound to exact tested head")

    recovery = read_json("evidence/cp03/cp03-w02/W02-16/recovery_retest_report.json")
    if recovery.get("result") != "PASS" or recovery.get("repetitions_executed") != 20 or recovery.get("failed_invocations") != 0:
        raise RuntimeError("prior P02 recovery evidence is absent or no longer PASS")
    if recovery.get("best_rerun_selection") is not False or recovery.get("all_results_retained") is not True:
        raise RuntimeError("prior P02 retention semantics drifted")

    graph = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    tasks = {row["id"]: row for row in graph["tasks"]}
    if graph["first_executable_task"] != TASK:
        raise RuntimeError(f"unexpected frontier {graph['first_executable_task']}")
    if tasks[TASK]["status"] != "READY" or tasks[TASK].get("proof"):
        raise RuntimeError("W02-16 must be unproved READY before completion")
    if tasks[TASK]["depends_on"] != ["W02-15"] or tasks["W02-15"]["status"] != "COMPLETE":
        raise RuntimeError("W02-16 dependency drift")
    if tasks[NEXT]["status"] != "BLOCKED" or tasks[NEXT].get("proof"):
        raise RuntimeError("W02-17 must be unproved BLOCKED before W02-16 completion")
    if not all(tasks[d]["status"] == "COMPLETE" for d in tasks[NEXT]["depends_on"] if d != TASK):
        raise RuntimeError("W02-17 has an incomplete dependency other than W02-16")
    if graph["global_denominator"] != 7565 or graph["openjarvis_obligations"] != 646 or graph.get("w02_obligation_count") != 47:
        raise RuntimeError("denominator/obligation drift")
    goal = read_json("GOAL_STATE.json")
    if goal["parity"]["total"] != 7565 or goal["parity"]["verified"] != 0:
        raise RuntimeError("parity drift")

    claim = read_json("sessions/20260922-w02-performance-baseline/CLAIM.json")
    if claim.get("claim_id") != CLAIM or claim.get("status") != "ACTIVE":
        raise RuntimeError("active P01 claim missing")
    if claim.get("base_head") != "9d5d283c1c4e9e1bcd662a7b35bdbbf9120fa6b8":
        raise RuntimeError("P01 claim base drift")

    durable = dict(report)
    durable.update({"date":"2026-09-22","evidence_id":EVIDENCE,"github_actions_run_id":run_id,"status":"PASS"})
    write_json("evidence/cp03/cp03-w02/W02-16/performance_baseline_report.json", durable)

    tasks[TASK]["status"] = "COMPLETE"
    tasks[TASK]["proof"] = [{
        "result":"PASS",
        "gate":"G5",
        "p01_evidence_id":EVIDENCE,
        "p02_evidence_id":"EVID-W02-RECOVERY-RETEST-20260922",
        "run_id":run_id,
        "validated_head":tested_head,
        "same_host":True,
        "samples_per_path":report["budget"]["samples_per_path"],
        "performance_threshold":"MEASUREMENT_ONLY_NO_POST_HOC_THRESHOLD",
        "parity_promotions":0,
    }]
    tasks[NEXT]["status"] = "READY"
    graph["first_executable_task"] = NEXT
    write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", graph)

    next_title = tasks[NEXT]["title"]
    state_path = ROOT / "STATE.md"
    state = state_path.read_text(encoding="utf-8")
    old='- Canonical task frontier: `W02-16 — Retest recovery performance` (`READY`)\n'
    new=f'- Canonical task frontier: `{NEXT} — {next_title}` (`READY`)\n'
    if old not in state:
        raise RuntimeError("STATE W02-16 frontier anchor missing")
    state_path.write_text(state.replace(old,new,1),encoding="utf-8")

    claim.update({"status":"RELEASED","event":"RELEASE","last_evidence_id":EVIDENCE,"validated_head":tested_head,"release_run_id":run_id})
    write_json("sessions/20260922-w02-performance-baseline/CLAIM.json", claim)
    write_json("sessions/20260922-w02-performance-baseline/RESULT.json", {
        "claim_id":CLAIM,"date":"2026-09-22","evidence_id":EVIDENCE,"result":"ADVANCED","task":TASK,
        "task_status":"COMPLETE","next_task":NEXT,"next_task_status":"READY","validated_head":tested_head,"github_actions_run_id":run_id,
        "p01_same_host_performance":"PASS","p02_recovery_retest":"PASS","parity_promotions":0,"global_denominator":7565,
    })

    ensure_unique("ledgers/EVIDENCE_LEDGER.ndjson","evidence_id",EVIDENCE)
    append("ledgers/EVIDENCE_LEDGER.ndjson", {
        "date":"2026-09-22","evidence_id":EVIDENCE,"task":TASK,"gate":"G5","result":"PASS","run_id":run_id,"validated_head":tested_head,
        "claim":"Fixed-budget same-host P01 baseline measured direct OpenJarvis stream_full versus the canonical AdapterFrame sidecar streaming path on the exact pinned qwen3:0.6b/llamacpp lane. Latency, TTFT, throughput and RSS were recorded for all fixed samples; no post-hoc threshold was introduced. Prior P02 recovery evidence remains PASS.",
        "direct_summary":report["summary"]["direct"],"adapted_summary":report["summary"]["adapted"],"adapted_over_direct":report["summary"]["adapted_over_direct"],
        "provider_egress_executions":0,"tool_executions":0,"parity_promotions":0,"verified_capabilities":0,"global_denominator":7565,"openjarvis_obligations":646,
    })
    append("ledgers/CLAIM_LEDGER.ndjson", {
        "canonical_task":TASK,"checkpoint":"CP03","claim_id":CLAIM,"date":"2026-09-22","event":"RELEASE","event_id":"CLAIM-W02-PERFORMANCE-20260922-RELEASE",
        "evidence_id":EVIDENCE,"owner":"chatgpt-gpt-5.6-sol","parent_wave":"CP03-W02","project_id":"CLEVER-JARVIS-001","status":"RELEASED","validated_head":tested_head,"wave_id":WAVE,
        "coordination":"P01 evidence and prior P02 evidence jointly close W02-16. Release the bounded claim; only W02-17 is opened READY according to the DAG."
    })
    append("ledgers/RUN_LOG.ndjson", {
        "checkpoint":"CP03","date":"2026-09-22","event":"CP03_W02_PERFORMANCE_BASELINE_COMPLETE","event_id":"RUN-W02-PERFORMANCE-20260922","evidence_id":EVIDENCE,
        "goal_id":"CLEVER-JARVIS-001","iteration":"I03","next_task":NEXT,"result":"ADVANCED","run_id":run_id,"validated_head":tested_head,
    })
    append("ledgers/WAVE_LEDGER.ndjson", {
        "canonical_task":TASK,"checkpoint":"CP03","date":"2026-09-22","event":"COMPLETE","event_id":"WAVE-W02-PERFORMANCE-20260922-COMPLETE","evidence_id":EVIDENCE,
        "next_task":NEXT,"parent_wave":"CP03-W02","result":"PASS","run_id":run_id,"task_status":"COMPLETE","validated_head":tested_head,"wave_id":WAVE,
    })
    ensure_unique("ledgers/DECISION_LEDGER.ndjson","decision_id","DEC-W02-PERFORMANCE-FIXED-BUDGET-20260922")
    append("ledgers/DECISION_LEDGER.ndjson", {
        "context":"W02-16 P01 same-host baseline","date":"2026-09-22","decision_id":"DEC-W02-PERFORMANCE-FIXED-BUDGET-20260922","evidence_id":EVIDENCE,"status":"ACCEPTED","task":TASK,
        "decision":"Freeze warmups, three samples per path, execution order, prompt, max output tokens, temperature, llama.cpp context/threads/parallelism and measurement fields before execution. Treat P01 as a descriptive baseline, not an optimization threshold or parity proof."
    })
    append("ledgers/RISK_LEDGER.ndjson", {
        "date":"2026-09-22","evidence_id":EVIDENCE,"risk_id":"RISK-W02-PERFORMANCE-BASELINE-PENDING-20260922","severity":"P2","status":"MITIGATED","task":TASK,
        "risk":"P01 same-host performance baseline was previously NOT_RUN.","mitigation":"Fixed-budget direct-vs-adapted baseline is now evidence-backed. This closes only the W02-16 P01 gap; supported-hardware release performance remains a later release concern and is not inferred from the CI host."
    })

    handoff_path=ROOT/"HANDOFF.md"
    handoff=handoff_path.read_text(encoding="utf-8")
    start=handoff.find("## Next executable\n")
    end=handoff.find("\n## W02-14 fallback",start)
    if start<0 or end<0:
        raise RuntimeError("HANDOFF next-executable section anchors missing")
    next_section=(f"## Next executable\n\n`{NEXT} — {next_title}` (`READY`).\n\n"
                  "W02-16 is evidence-backed COMPLETE: prior P02 recovery/flakiness remains PASS and P01 now has a fixed-budget same-host direct-vs-adapted baseline with latency, TTFT, memory and throughput recorded. W02-17 is the only newly opened READY DAG frontier. No parity promotion, denominator mutation, provider egress or tool execution occurred.\n")
    handoff=handoff[:start]+next_section+handoff[end:]
    marker="## W02-16 recovery + performance — COMPLETE"
    if marker not in handoff:
        d=report["summary"]["direct"]; a=report["summary"]["adapted"]; r=report["summary"]["adapted_over_direct"]
        handoff=handoff.rstrip()+f"\n\n{marker}\n\n- P02 evidence: `EVID-W02-RECOVERY-RETEST-20260922` remains PASS (20/20 repetitions; all 80 invocation records retained).\n- P01 evidence: `{EVIDENCE}` on exact tested head `{tested_head}` / run `{run_id}`. Fixed budget: 1 warmup + 3 measured samples per path, 32 max output tokens, temperature 0, fixed interleaved order.\n- Direct median: latency {d['latency_ms_median']:.3f} ms; TTFT {d['ttft_ms_median']:.3f} ms; throughput {d['throughput_tokens_per_s_median']:.3f} tok/s; client peak RSS {d['client_peak_rss_kib_max']} KiB.\n- Adapted median: latency {a['latency_ms_median']:.3f} ms; TTFT {a['ttft_ms_median']:.3f} ms; throughput {a['throughput_tokens_per_s_median']:.3f} tok/s; client peak RSS {a['client_peak_rss_kib_max']} KiB. Ratios adapted/direct: latency {r['latency_ratio']:.4f}, TTFT {r['ttft_ratio']:.4f}, throughput {r['throughput_ratio']:.4f}.\n- Measurement-only: no post-hoc threshold, no parity promotion, denominator 7565 unchanged, OpenJarvis obligations 646, provider egress 0, tool executions 0.\n- Claim `{CLAIM}` released. Exact next task: `{NEXT} — {next_title}`.\n"
    handoff_path.write_text(handoff,encoding="utf-8")


if __name__ == "__main__":
    main()
