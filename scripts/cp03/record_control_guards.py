"""Persist a scoped support advance without closing W02 or promoting parity."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
SESSION = "sessions/20260907-w02-control-guards"
CLAIM = "CLAIM-W02-CONTROL-20260907"
EVIDENCE = "EVID-W02-CONTROL-20260907"
WAVE = "CP03-W02-CONTROL-01"
OUT = "evidence/cp03/cp03-w02/control-guards"
def load(path): return json.loads((ROOT / path).read_text())
def save(path, value):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
def append(path, record):
    with (ROOT / path).open("a") as handle:
        handle.write(json.dumps({"schema_version": 1, "date": datetime.now(timezone.utc).date().isoformat(), **record}, sort_keys=True) + "\n")
def rebuild(): subprocess.run([sys.executable, "scripts/context/build_context_pack.py"], cwd=ROOT, check=True)
def begin():
    assert load("EXECUTION_STATE.json")["next_wave"] == "CP03-W02", "frontier drift"
    rows = [json.loads(line) for line in (ROOT / "ledgers/CLAIM_LEDGER.ndjson").read_text().splitlines() if line.strip()]
    latest = {row["claim_id"]: row for row in rows}
    assert not [row for row in latest.values() if row.get("status") == "ACTIVE"], "active claim needs reconciliation"
    scope = ["kernel/crates/clever-kernel/src/adapter.rs", "kernel/crates/clever-kernel/tests/**", "adapters/openjarvis/sidecar.py", "scripts/cp03/*control*", "tests/test_control_guard_gate.py", "tests/test_cp03_w02_plan.py", "CP03-W02 scoped evidence/task/context persistence"]
    append("ledgers/CLAIM_LEDGER.ndjson", {"claim_id": CLAIM, "wave_id": WAVE, "parent_wave": "CP03-W02", "owner": "chatgpt-execution", "scope": scope, "status": "ACTIVE"})
    append("ledgers/RUN_LOG.ndjson", {"event": "WORK_STARTED", "wave_id": WAVE, "checkpoint": "CP03", "iteration": "I03", "status": "IN_PROGRESS", "source_sha": os.environ["GITHUB_SHA"]})
    rebuild()
def finish():
    gate = load(".cache/control-guards/GATE.json")
    native = load(".cache/control-guards/NATIVE.json")
    assert gate["status"] == native["status"] == "PASS"
    assert gate["repair"] is True and gate["parity_promotions"] == 0
    for name, digest in gate["subject_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, "source changed after tests"
    shutil.copytree(ROOT / ".cache/control-guards", ROOT / OUT, dirs_exist_ok=True)
    proof = f"{OUT}/GATE.json"
    append("ledgers/EVIDENCE_LEDGER.ndjson", {"evidence_id": EVIDENCE, "status": "VERIFIED", "type": "control_protocol_regression", "paths": [proof, f"{OUT}/NATIVE.json"], "github_actions_run_id": int(os.environ["GITHUB_RUN_ID"]), "input_sha_before_repair": gate["input_sha"], "subject_sha256": gate["subject_sha256"], "claim": "13 runtime regressions reproduced; 15 control tests pass and repeat; missing interpreter fails; real pinned native registry regression passes. Not inference/capability parity."})
    append("ledgers/CLAIM_LEDGER.ndjson", {"claim_id": CLAIM, "wave_id": WAVE, "status": "RELEASED", "release_evidence_id": EVIDENCE})
    append("ledgers/RUN_LOG.ndjson", {"event": "CONTROL_GUARDS_ADVANCED", "wave_id": WAVE, "status": "ADVANCED", "evidence_id": EVIDENCE, "canonical_frontier": "CP03-W02"})
    append("ledgers/WAVE_LEDGER.ndjson", {"wave_id": WAVE, "parent_wave": "CP03-W02", "status": "COMPLETE", "evidence_id": EVIDENCE, "scope": "harness and correlated atomic control guards only"})
    append("ledgers/RISK_LEDGER.ndjson", {"risk_id": "RISK-W02-BOUNDED-IO", "severity": "HIGH", "status": "OPEN", "risk": "Aggregate receive queue, blocking writes and teardown are not yet bounded; actual inference cancellation and container cleanup remain unproven.", "mitigation": "W02-03/04/12 remain open; do not expose streaming or claim G1/M1/M2."})
    path = "iterations/03/waves/CP03-W02/TASK_GRAPH.json"
    plan = load(path)
    by_id = {task["id"]: task for task in plan["tasks"]}
    for tid in ("W02-00", "W02-02"):
        by_id[tid]["status"] = "COMPLETE"
        by_id[tid]["proof"] = [proof, f"{OUT}/NATIVE.json"]
    for tid in ("W02-01", "W02-03"): by_id[tid]["status"] = "READY"
    by_id["W02-05"]["proof"] = [proof]
    by_id["W02-05"]["note"] = "Control/atomicity fixes tested as harness support. Still BLOCKED by W02-03; no dependency bypass or task closure."
    plan["status"] = "IN_PROGRESS"
    plan["first_executable_task"] = "W02-01"
    save(path, plan)
    # Negative planning fixtures must not depend on the repository staying PLANNED forever.
    p = ROOT / "tests/test_cp03_w02_plan.py"
    s = p.read_text()
    before = "        self.plan, self.findings, self.cos = copy.deepcopy(MOD.load(ROOT))"
    assert s.count(before) == 1
    s = s.replace(before, before + '\n        for task in self.plan["tasks"]:\n            task["status"] = "READY" if task["id"] == "W02-00" else "BLOCKED"\n            task["proof"] = []\n        self.plan["first_executable_task"] = "W02-00"\n        self.plan["w02_obligation_count"] = None', 1)
    s = s.replace("    def test_valid_plan(self):", "    def test_repository_plan_is_valid(self):\n        self.assertEqual(MOD.validate(*MOD.load(ROOT))[\"status\"], \"PASS\")\n\n    def test_valid_plan(self):", 1)
    p.write_text(s)
    dag = load(".agentic/context/NEXT_ACTIONS.json")
    for task in dag["tasks"]:
        if task["id"] == "CP03-002": task["status"] = "IN_PROGRESS"
    save(".agentic/context/NEXT_ACTIONS.json", dag)
    tasks = (ROOT / "TASKS.md").read_text().replace("**CP03-002 / CP03-W02 — Map models, engines and inference behavior through canonical contracts.** Status: `READY`.", "**CP03-002 / CP03-W02 — Map models, engines and inference behavior through canonical contracts.** Status: `IN_PROGRESS`.")
    tasks += f"\nW02 control support: W02-00/02 complete with `{EVIDENCE}`; W02-01 and W02-03 READY. W02-05 has partial proof only and remains gated. No real-model inference or parity promotion.\n"
    (ROOT / "TASKS.md").write_text(tasks)
    (ROOT / "HANDOFF.md").write_text(f"# HANDOFF — CP03-W02 control regression milestone\n\nCP03 / I03 / CP03-002 / CP03-W02 remains IN_PROGRESS.\nScoped support: {WAVE}; evidence {EVIDENCE}, `{proof}`.\n13 reproduced runtime failures, 15 passing control tests plus explicit retest, strict harness and real pinned native registry test. Tested source identity is subject_sha256, not the input SHA before repair.\nW02-00/02 complete. W02-05 has partial proof only and remains blocked by W02-03. Aggregate queue, writes, teardown, container cleanup and inference cancellation remain unproven.\n\nNext: /empezarproyecto; validate state/context/plan; claim W02-01 obligation selection or non-conflicting W02-03 bounded I/O. Preserve 7565/646 and zero VERIFIED. No new model ran. Branch protection remains an administrative release prerequisite.\n\nExact post-repair commit requires read-only Control Guard Regression before merge. Inspect `{OUT}/`, control_guard_gate.py, task graph, registry/sidecar changes. Claims released.\n")
    save(f"{SESSION}/RESULT.json", {"status": "ADVANCED", "wave": WAVE, "evidence_id": EVIDENCE, "tasks_completed": ["W02-00", "W02-02"], "partial_task": "W02-05", "remaining_gaps": gate["remaining_gaps"], "parity_promotions": 0})
    save("graphs/cp03/w02-control-guards.json", {"schema_version": 1, "plane": "P2_COS20D_DECISION", "source_truth_unchanged": True, "wave": WAVE, "dimensions": ["D01_PROVENANCE_EVIDENCE", "D06_INTERFACE_CONTRACTS", "D07_STATE_DATA", "D13_FAILURE_RECOVERY", "D15_TEST_EVAL_PARITY"], "links": [{"source": p, "sha256": h, "tested_by": "kernel/crates/clever-kernel/tests/control_guards.rs", "evidence": proof} for p, h in gate["subject_sha256"].items()], "open_risk": "RISK-W02-BOUNDED-IO", "migration_authorized": False})
    (ROOT / ".github/workflows/cp03-w02-control-repair.yml").unlink()
    rebuild()
if __name__ == "__main__": {"begin": begin, "finish": finish}[sys.argv[1]]()
