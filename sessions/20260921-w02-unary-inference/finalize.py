from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = "W02-10"
NEXT = "W02-11"
CLAIM = "CLAIM-CP03-W02-UNARY-INFERENCE-20260921"
EVIDENCE = "EVID-W02-UNARY-INFERENCE-20260921"
WAVE = "CP03-W02-UNARY-INFERENCE-20260921"
MODEL_SHA = "9acfc1e001311f34b4252001b626f2e466d592a42065f66571bff3790d4e1b14"


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


def update_plan_test() -> None:
    path = ROOT / "tests/test_cp03_w02_plan.py"
    text = path.read_text(encoding="utf-8")
    if 'expected = "W02-11"' in text and 'self.task("W02-11")["status"], "READY"' in text:
        return
    old = '''        else:\n            self.assertEqual(weights["status"], "COMPLETE")\n            self.assertTrue(weights["proof"])\n            self.assertEqual(unary["status"], "READY")\n            self.assertFalse(unary["proof"])\n            self.assertEqual(self.plan["first_executable_task"], "W02-10")\n'''
    new = '''        elif unary["status"] == "READY":\n            self.assertEqual(weights["status"], "COMPLETE")\n            self.assertTrue(weights["proof"])\n            self.assertFalse(unary["proof"])\n            self.assertEqual(self.plan["first_executable_task"], "W02-10")\n        else:\n            self.assertEqual(unary["status"], "COMPLETE")\n            self.assertTrue(unary["proof"])\n            self.assertEqual(self.task("W02-11")["status"], "READY")\n            self.assertEqual(self.plan["first_executable_task"], "W02-11")\n'''
    if old not in text:
        raise RuntimeError("plan-test unary frontier anchor missing")
    text = text.replace(old, new, 1)
    old2 = '''        else:\n            expected = "W02-10"\n'''
    new2 = '''        elif unary["status"] == "READY":\n            expected = "W02-10"\n        else:\n            expected = "W02-11"\n'''
    if old2 not in text:
        raise RuntimeError("plan-test expected frontier anchor missing")
    text = text.replace(old2, new2, 1)
    marker = '''        elif expected == "W02-10":\n            self.assertEqual(weights["status"], "COMPLETE")\n            self.assertTrue(weights["proof"])\n            self.assertEqual(unary["status"], "READY")\n            self.assertFalse(unary["proof"])\n'''
    expanded = marker + '''        elif expected == "W02-11":\n            self.assertEqual(unary["status"], "COMPLETE")\n            self.assertTrue(unary["proof"])\n            self.assertEqual(self.task("W02-11")["status"], "READY")\n'''
    if marker not in text:
        raise RuntimeError("plan-test W02-10 branch anchor missing")
    path.write_text(text.replace(marker, expanded, 1), encoding="utf-8")


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
        "gate": "G3",
        "status": "PASS",
        "validated_head": head,
        "github_actions_run_id": run_id,
        "openjarvis_commit": "72033b8ec288aa067ce4530ff9d96bf231e9c4e5",
        "engine": "llamacpp",
        "runtime_commit": "391fac16460f15233a7740550d858ac96df3419d",
        "model_id": "qwen3:0.6b",
        "artifact_filename": "Qwen_Qwen3-0.6B-Q4_K_M.gguf",
        "artifact_size_bytes": 484220320,
        "artifact_sha256": MODEL_SHA,
        "correlated_chunk_terminal": True,
        "invalid_input_pre_engine_test": "PASS",
        "runtime_executed": True,
        "model_executions": 1,
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "streaming_executions": 0,
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
    if not (lock["global_denominator"] == 7565 and lock["openjarvis_obligations"] == 646 and lock["w02_proof_units"] == 47):
        raise RuntimeError("scope lock drift")
    if goal["parity"]["total"] != 7565 or goal["parity"]["verified"] != 0:
        raise RuntimeError("parity drift")
    if plan["global_denominator"] != 7565 or plan["openjarvis_obligations"] != 646:
        raise RuntimeError("task graph denominator drift")
    tasks = {task["id"]: task for task in plan["tasks"]}
    task = tasks[TASK]
    if plan["first_executable_task"] != TASK or task["status"] != "READY" or task["proof"]:
        raise RuntimeError("W02-10 is not the exact READY frontier")
    if not all(tasks[dep]["status"] == "COMPLETE" and tasks[dep]["proof"] for dep in task["depends_on"]):
        raise RuntimeError("W02-10 dependency proof missing")
    if latest_claim_status() != "ACTIVE":
        raise RuntimeError("W02-10 claim is not ACTIVE")

    task["status"] = "COMPLETE"
    task["proof"] = [{
        "evidence_id": EVIDENCE,
        "result": "PASS",
        "validated_head": head,
        "run_id": run_id,
        "gate": "G3",
        "engine": "llamacpp",
        "model_id": "qwen3:0.6b",
        "artifact_sha256": MODEL_SHA,
        "runtime_executed": True,
        "model_executions": 1,
        "correlated_chunk_terminal": True,
        "invalid_input_pre_engine_test": "PASS",
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "streaming_executions": 0,
        "parity_promotions": 0,
    }]
    if tasks[NEXT]["status"] != "BLOCKED" or tasks[NEXT]["proof"]:
        raise RuntimeError("W02-11 pre-transition state invalid")
    if not all(tasks[dep]["status"] == "COMPLETE" for dep in tasks[NEXT]["depends_on"]):
        raise RuntimeError("W02-11 dependencies are not complete")
    tasks[NEXT]["status"] = "READY"
    plan["first_executable_task"] = NEXT
    write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

    write_json("evidence/cp03/cp03-w02/W02-10/receipt.json", receipt)
    report = dict(receipt)
    report.update({"date": "2026-09-21", "evidence_id": EVIDENCE, "support_wave": WAVE, "next_task": NEXT})
    write_json("evidence/cp03/cp03-w02/W02-10/report.json", report)
    write_json("sessions/20260921-w02-unary-inference/RESULT.json", {
        "schema_version": 1, "date": "2026-09-21", "claim_id": CLAIM, "wave_id": WAVE,
        "task": TASK, "status": "COMPLETE", "evidence_id": EVIDENCE, "validated_head": head,
        "github_actions_run_id": run_id, "next_task": NEXT,
    })

    append_unique("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE, {
        "schema_version": 1, "date": "2026-09-21", "evidence_id": EVIDENCE, "status": "VERIFIED",
        "type": "cp03_w02_real_unary_inference", "wave_id": "CP03-W02", "support_wave": WAVE,
        "github_actions_run_id": run_id, "validated_head": head, "engine": "llamacpp", "model_id": "qwen3:0.6b",
        "artifact_sha256": MODEL_SHA, "runtime_executed": True, "model_executions": 1,
        "correlated_chunk_terminal": True, "invalid_input_pre_engine_test": "PASS",
        "provider_egress_executions": 0, "tool_executions": 0, "streaming_executions": 0,
        "parity_promotions": 0, "verified_capabilities": 0, "global_denominator": 7565,
        "openjarvis_obligations": 646, "w02_proof_units": 47,
        "claim": "Exact-head G3 proves one real unary inference through Rust, canonical protobuf transport, OpenJarvis sidecar, pinned native llamacpp and exact W02-09 real GGUF. M1 only; no W02 closure or parity promotion.",
    })
    append_unique("ledgers/RUN_LOG.ndjson", "event_id", "RUN-W02-UNARY-20260921", {
        "schema_version": 1, "date": "2026-09-21", "event_id": "RUN-W02-UNARY-20260921",
        "event": "CP03_W02_UNARY_INFERENCE_ADVANCED", "goal_id": "CLEVER-JARVIS-001", "checkpoint": "CP03",
        "iteration": "I03", "wave_id": "CP03-W02", "support_wave": WAVE, "status": "ADVANCED",
        "evidence_id": EVIDENCE, "next_task": NEXT, "K": 47, "parity_promotions": 0,
    })
    append_unique("ledgers/WAVE_LEDGER.ndjson", "event_id", "WAVE-W02-UNARY-20260921", {
        "schema_version": 1, "date": "2026-09-21", "event_id": "WAVE-W02-UNARY-20260921", "wave_id": WAVE,
        "parent_wave": "CP03-W02", "iteration": "I03", "checkpoint": "CP03", "event": "VERIFICATION",
        "status": "COMPLETE", "evidence_id": EVIDENCE, "next_task": NEXT,
    })
    append_unique("ledgers/DECISION_LEDGER.ndjson", "decision_id", "D-0016", {
        "schema_version": 1, "date": "2026-09-21", "decision_id": "D-0016", "status": "ACCEPTED",
        "decision": "G3 unary inference is a single-flight loopback-only OpenJarvis llamacpp lane bound to the exact W02-09 model artifact; Rust retains admission, identity, correlation and terminal validation and output is validated structurally rather than by exact prose.",
        "context": "Minimum real M1 proof without prematurely implementing streaming, cancellation, fallback, tools or parity promotion.",
        "evidence_id": EVIDENCE,
    })
    append_unique("ledgers/RISK_LEDGER.ndjson", "risk_id", "RISK-0010", {
        "schema_version": 1, "date": "2026-09-21", "risk_id": "RISK-0010", "status": "MITIGATING", "severity": "HIGH",
        "risk": "A successful unary CPU/loopback G3 lane can be misread as complete inference parity or proof of streaming, cancellation, external-provider effects and platform-specific behavior.",
        "mitigation": "Record G3 as M1 only; keep parity promotions at zero; open only W02-11; preserve exact runtime/model digests and zero counters for provider egress, tools and streaming.",
        "evidence_id": EVIDENCE,
    })
    with (ROOT / "ledgers/CLAIM_LEDGER.ndjson").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"schema_version": 1, "date": "2026-09-21", "claim_id": CLAIM, "event": "RELEASE", "owner": "chatgpt-gpt-5.6-sol", "status": "RELEASED", "release_evidence_id": EVIDENCE, "wave_id": WAVE}, sort_keys=True, separators=(",", ":")) + "\n")

    handoff_path = ROOT / "HANDOFF.md"
    handoff = handoff_path.read_text(encoding="utf-8")
    handoff = handoff.replace('- COMPLETE: `W02-00..W02-09`.', '- COMPLETE: `W02-00..W02-10`.')
    marker = '- W02-09 evidence: `EVID-W02-REAL-MODEL-20260921`.'
    if 'EVID-W02-UNARY-INFERENCE-20260921' not in handoff:
        handoff = handoff.replace(marker, marker + '\n- W02-10 G3 evidence: `EVID-W02-UNARY-INFERENCE-20260921`; one real model execution, correlated unary chunk+terminal, provider egress 0, tool executions 0, parity promotions 0.')
    old = '''## Next executable\n\n`W02-10 — Inferencia unary end-to-end`.\n\nW02-10 is now the sole READY G3 frontier. It must execute the first real unary inference through Rust → canonical contract → OpenJarvis sidecar → pinned native engine/model and prove correlated terminal output. It must consume the exact W02-09 model identity/digest; a mock or a floating/redownloaded artifact cannot satisfy G3. M1 does not close W02.'''
    new = '''## Next executable\n\n`W02-11 — Stream y stream_full`.\n\nW02-10/M1 is evidence-backed COMPLETE but does not close W02. W02-11 is the sole READY G4 frontier and must prove fragmented/coalesced streaming semantics, UTF-8 boundaries, sequence integrity and exactly one terminal without converting EOF, duplicates or reordering into false success. Cancellation and later G4 tasks remain BLOCKED by the DAG.'''
    if old not in handoff:
        raise RuntimeError("HANDOFF frontier anchor missing")
    handoff_path.write_text(handoff.replace(old, new, 1), encoding="utf-8")
    update_plan_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
