"""Finalize W02-09 only after exact-head real-weight and offline-integrity proof."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-09-21"
TASK = "W02-09"
NEXT = "W02-10"
CLAIM_ID = "CLAIM-CP03-W02-REAL-MODEL-20260921"
SUPPORT_WAVE = "CP03-W02-REAL-MODEL-20260921"
EVIDENCE_ID = "EVID-W02-REAL-MODEL-20260921"
DECISION_ID = "D-0015"
RISK_ID = "RISK-0009"
OPENJARVIS_PIN = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"
MODEL_SHA256 = "9acfc1e001311f34b4252001b626f2e466d592a42065f66571bff3790d4e1b14"
MODEL_SIZE = 484220320
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def read_json(root: Path, path: str | Path) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def write_json(root: Path, path: str | Path, value: dict[str, Any]) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rows(root: Path, path: str) -> list[dict[str, Any]]:
    target = root / path
    if not target.exists():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_unique(root: Path, path: str, key: str, value: str, row: dict[str, Any]) -> None:
    if any(existing.get(key) == value for existing in rows(root, path)):
        return
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def latest_claim_status(root: Path) -> str | None:
    status = None
    for row in rows(root, "ledgers/CLAIM_LEDGER.ndjson"):
        if row.get("claim_id") == CLAIM_ID and row.get("status"):
            status = str(row["status"])
    return status


def validate_receipt(receipt: dict[str, Any], *, run_id: int, validated_head: str) -> None:
    expected = {
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "parent_wave": "CP03-W02",
        "task": TASK,
        "status": "PASS",
        "validated_head": validated_head,
        "github_actions_run_id": run_id,
        "openjarvis_commit": OPENJARVIS_PIN,
        "engine": "llamacpp",
        "runtime_repository": "ggml-org/llama.cpp",
        "runtime_commit": "391fac16460f15233a7740550d858ac96df3419d",
        "runtime_executed": False,
        "model_id": "qwen3:0.6b",
        "base_model_revision": "66b95ce14c07166297fcbfb54aa20441af8f9d75",
        "license": "Apache-2.0",
        "artifact_repository": "bartowski/Qwen_Qwen3-0.6B-GGUF",
        "artifact_revision": "7bcae0bc7b0606f1e948f8cdb31b98a2c10635db",
        "artifact_filename": "Qwen_Qwen3-0.6B-Q4_K_M.gguf",
        "artifact_size_bytes": MODEL_SIZE,
        "artifact_sha256": MODEL_SHA256,
        "offline_verification": "PASS",
        "model_executions": 0,
        "provider_egress_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise RuntimeError(f"receipt mismatch for {key}: {receipt.get(key)!r} != {value!r}")


def validate_authority(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    lock = read_json(root, "inventory/cp03/W02_SCOPE_LOCK.json")
    if (
        lock.get("w02_proof_units"),
        lock.get("w02_owned_capabilities"),
        lock.get("w02_shared_capabilities"),
    ) != (47, 37, 10):
        raise RuntimeError("W02 scope lock drift")
    if lock.get("global_denominator") != 7565 or lock.get("openjarvis_obligations") != 646:
        raise RuntimeError("denominator drift")

    goal = read_json(root, "GOAL_STATE.json")
    if goal.get("parity", {}).get("total") != 7565 or goal.get("parity", {}).get("verified") != 0:
        raise RuntimeError("W02-09 cannot finalize after parity drift")

    manifest = read_json(root, "inventory/cp03/W02_REAL_MODEL_LANE.json")
    if manifest.get("upstream", {}).get("commit") != OPENJARVIS_PIN:
        raise RuntimeError("OpenJarvis pin drift")
    if manifest.get("artifact", {}).get("sha256") != MODEL_SHA256:
        raise RuntimeError("model artifact digest drift")
    if manifest.get("artifact", {}).get("size_bytes") != MODEL_SIZE:
        raise RuntimeError("model artifact size drift")
    counters = manifest.get("counters", {})
    if counters.get("verified_capabilities") != 0 or counters.get("parity_promotions") != 0:
        raise RuntimeError("W02-09 manifest contains forbidden parity promotion")
    if counters.get("model_executions") != 0 or counters.get("provider_egress_executions") != 0:
        raise RuntimeError("W02-09 manifest contains forbidden execution counters")

    plan = read_json(root, "iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    if plan.get("global_denominator") != 7565 or plan.get("openjarvis_obligations") != 646:
        raise RuntimeError("task-graph denominator drift")
    tasks = {task["id"]: task for task in plan.get("tasks", [])}
    if TASK not in tasks or NEXT not in tasks:
        raise RuntimeError("W02-09/W02-10 task missing")
    for dep in tasks[TASK].get("depends_on", []):
        if tasks.get(dep, {}).get("status") != "COMPLETE" or not tasks[dep].get("proof"):
            raise RuntimeError(f"W02-09 prerequisite is not evidenced COMPLETE: {dep}")
    if tasks[TASK].get("status") not in {"READY", "IN_PROGRESS", "COMPLETE"}:
        raise RuntimeError("W02-09 has invalid state")
    if tasks[TASK].get("status") != "COMPLETE":
        if plan.get("first_executable_task") != TASK:
            raise RuntimeError("W02-09 is not the current frontier")
        if latest_claim_status(root) != "ACTIVE":
            raise RuntimeError("W02-09 claim is not ACTIVE")
        if tasks[NEXT].get("status") != "BLOCKED":
            raise RuntimeError("W02-10 must remain BLOCKED until W02-09 closes")
    return plan, tasks


def finalize(*, root: Path = ROOT, run_id: int, validated_head: str, receipt_path: Path) -> dict[str, Any]:
    if run_id <= 0:
        raise RuntimeError("run_id must be positive")
    if not SHA_RE.fullmatch(validated_head):
        raise RuntimeError("validated_head must be a full lowercase SHA")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    validate_receipt(receipt, run_id=run_id, validated_head=validated_head)
    plan, tasks = validate_authority(root)

    if tasks[TASK].get("status") != "COMPLETE":
        tasks[TASK]["status"] = "COMPLETE"
        tasks[TASK]["proof"] = [
            {
                "evidence_id": EVIDENCE_ID,
                "result": "PASS",
                "validated_head": validated_head,
                "run_id": run_id,
                "lane": "L2_REAL_MODEL_PINNED_WEIGHTS",
                "engine": "llamacpp",
                "model_id": "qwen3:0.6b",
                "artifact_size_bytes": MODEL_SIZE,
                "artifact_sha256": MODEL_SHA256,
                "offline_verification": "PASS",
                "runtime_executed": False,
                "model_executions": 0,
                "provider_egress_executions": 0,
                "parity_promotions": 0,
            }
        ]
        next_deps = tasks[NEXT].get("depends_on", [])
        if all(tasks.get(dep, {}).get("status") == "COMPLETE" for dep in next_deps):
            tasks[NEXT]["status"] = "READY"
            plan["first_executable_task"] = NEXT
        else:
            missing = [dep for dep in next_deps if tasks.get(dep, {}).get("status") != "COMPLETE"]
            raise RuntimeError(f"W02-10 dependencies unexpectedly incomplete: {missing}")
        write_json(root, "iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

    write_json(root, "evidence/cp03/cp03-w02/W02-09/real_model_receipt.json", receipt)
    report = {
        "schema_version": 1,
        "date": DATE,
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "parent_wave": "CP03-W02",
        "support_wave": SUPPORT_WAVE,
        "task": TASK,
        "status": "PASS",
        "validated_head": validated_head,
        "github_actions_run_id": run_id,
        "lane": "L2_REAL_MODEL_PINNED_WEIGHTS",
        "openjarvis_commit": OPENJARVIS_PIN,
        "engine": "llamacpp",
        "runtime_commit": "391fac16460f15233a7740550d858ac96df3419d",
        "runtime_executed": False,
        "model_id": "qwen3:0.6b",
        "license": "Apache-2.0",
        "artifact_revision": receipt["artifact_revision"],
        "artifact_size_bytes": MODEL_SIZE,
        "artifact_sha256": MODEL_SHA256,
        "offline_verification": "PASS",
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "verified_capabilities": 0,
        "parity_promotions": 0,
        "model_executions": 0,
        "provider_egress_executions": 0,
        "next_task": NEXT,
    }
    write_json(root, "evidence/cp03/cp03-w02/W02-09/report.json", report)

    append_unique(
        root,
        "ledgers/EVIDENCE_LEDGER.ndjson",
        "evidence_id",
        EVIDENCE_ID,
        {
            "schema_version": 1,
            "date": DATE,
            "evidence_id": EVIDENCE_ID,
            "status": "VERIFIED",
            "type": "cp03_w02_real_model_pinned_weights",
            "wave_id": "CP03-W02",
            "support_wave": SUPPORT_WAVE,
            "github_actions_run_id": run_id,
            "validated_head": validated_head,
            "global_denominator": 7565,
            "openjarvis_obligations": 646,
            "w02_proof_units": 47,
            "engine": "llamacpp",
            "model_id": "qwen3:0.6b",
            "artifact_size_bytes": MODEL_SIZE,
            "artifact_sha256": MODEL_SHA256,
            "offline_verification": "PASS",
            "runtime_executed": False,
            "model_executions": 0,
            "provider_egress_executions": 0,
            "parity_promotions": 0,
            "claim": "Immutable real Qwen3 0.6B Q4_K_M GGUF weights were acquired only under explicit acquisition grant, verified by exact size/SHA-256/GGUF magic, then re-verified in a network-none container. This closes W02-09 artifact readiness only; no model inference, provider execution or capability parity promotion occurred.",
        },
    )
    append_unique(
        root,
        "ledgers/RUN_LOG.ndjson",
        "event_id",
        "RUN-W02-REAL-MODEL-20260921",
        {
            "schema_version": 1,
            "date": DATE,
            "event_id": "RUN-W02-REAL-MODEL-20260921",
            "event": "CP03_W02_REAL_MODEL_ADVANCED",
            "goal_id": "CLEVER-JARVIS-001",
            "checkpoint": "CP03",
            "iteration": "I03",
            "wave_id": "CP03-W02",
            "support_wave": SUPPORT_WAVE,
            "status": "ADVANCED",
            "evidence_id": EVIDENCE_ID,
            "next_task": NEXT,
            "K": 47,
            "parity_promotions": 0,
        },
    )
    append_unique(
        root,
        "ledgers/WAVE_LEDGER.ndjson",
        "event_id",
        "WAVE-W02-REAL-MODEL-20260921",
        {
            "schema_version": 1,
            "date": DATE,
            "event_id": "WAVE-W02-REAL-MODEL-20260921",
            "wave_id": SUPPORT_WAVE,
            "parent_wave": "CP03-W02",
            "iteration": "I03",
            "checkpoint": "CP03",
            "event": "VERIFICATION",
            "status": "COMPLETE",
            "evidence_id": EVIDENCE_ID,
            "next_task": NEXT,
        },
    )
    append_unique(
        root,
        "ledgers/DECISION_LEDGER.ndjson",
        "decision_id",
        DECISION_ID,
        {
            "schema_version": 1,
            "date": DATE,
            "decision_id": DECISION_ID,
            "status": "ACCEPTED",
            "decision": "Use OpenJarvis catalog model qwen3:0.6b with the llamacpp engine for the first L2 real-model lane, pinning the base-model revision, llama.cpp runtime commit and a Q4_K_M GGUF artifact by immutable revision, exact byte size and SHA-256. Acquisition is an explicit network phase; integrity verification is repeated offline. W02-09 never executes inference.",
            "context": "This is the smallest portable real-weight lane that satisfies G2 artifact readiness while preserving the W02-10 boundary between model materialization and actual unary inference.",
            "evidence_id": EVIDENCE_ID,
        },
    )
    append_unique(
        root,
        "ledgers/RISK_LEDGER.ndjson",
        "risk_id",
        RISK_ID,
        {
            "schema_version": 1,
            "date": DATE,
            "risk_id": RISK_ID,
            "status": "MITIGATING",
            "severity": "HIGH",
            "risk": "External model artifacts can drift, be replaced, truncate in transit or be confused with mocks, creating false real-model evidence or supply-chain exposure.",
            "mitigation": "Pin repository revision, exact filename, byte size and SHA-256; require GGUF magic; download to a partial file only under explicit grant; atomically promote only after verification; repeat verification with network disabled; never commit weights to Git; W02-10 must consume this exact pinned identity.",
            "evidence_id": EVIDENCE_ID,
        },
    )

    if latest_claim_status(root) != "RELEASED":
        target = root / "ledgers/CLAIM_LEDGER.ndjson"
        with target.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "schema_version": 1,
                        "date": DATE,
                        "claim_id": CLAIM_ID,
                        "event": "RELEASE",
                        "wave_id": SUPPORT_WAVE,
                        "owner": "chatgpt-gpt-5.6-sol",
                        "status": "RELEASED",
                        "release_evidence_id": EVIDENCE_ID,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )

    claim_path = root / "sessions/20260921-w02-real-model/CLAIM.json"
    if claim_path.exists():
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        claim["status"] = "RELEASED"
        claim["release_evidence_id"] = EVIDENCE_ID
        claim_path.write_text(json.dumps(claim, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    write_json(
        root,
        "sessions/20260921-w02-real-model/FINALIZATION.json",
        {
            "schema_version": 1,
            "date": DATE,
            "task": TASK,
            "status": "COMPLETE",
            "evidence_id": EVIDENCE_ID,
            "validated_head": validated_head,
            "github_actions_run_id": run_id,
            "next_task": NEXT,
            "parity_promotions": 0,
            "model_executions": 0,
        },
    )

    (root / "HANDOFF.md").write_text(
        "# HANDOFF — CP03-W02\n\n"
        "- Checkpoint: `CP03`; iteration: `I03`; parent wave `CP03-W02` remains `IN_PROGRESS`.\n"
        "- Frozen proof scope: **K=47 = 37 owned + 10 shared**; global denominator 7,565; OpenJarvis obligations 646; VERIFIED 0.\n"
        "- COMPLETE: `W02-00..W02-09`.\n"
        "- W02-09 evidence: `EVID-W02-REAL-MODEL-20260921`.\n"
        "- Real L2 lane: OpenJarvis `qwen3:0.6b` → `llamacpp`; base revision `66b95ce14c07166297fcbfb54aa20441af8f9d75`; runtime commit `391fac16460f15233a7740550d858ac96df3419d`.\n"
        "- Real GGUF artifact: `Qwen_Qwen3-0.6B-Q4_K_M.gguf`, 484220320 bytes, SHA-256 `9acfc1e001311f34b4252001b626f2e466d592a42065f66571bff3790d4e1b14`; controlled acquisition followed by network-none verification PASS.\n"
        "- Missing/corrupt/mock artifacts remain fail-closed. No model inference or provider egress occurred; parity promotions 0; denominator unchanged.\n\n"
        "## Next executable\n\n"
        "`W02-10 — Inferencia unary end-to-end`.\n\n"
        "W02-10 is now the sole READY G3 frontier. It must execute the first real unary inference through Rust → canonical contract → OpenJarvis sidecar → pinned native engine/model and prove correlated terminal output. It must consume the exact W02-09 model identity/digest; a mock or a floating/redownloaded artifact cannot satisfy G3. M1 does not close W02.\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--validated-head", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    report = finalize(root=args.root, run_id=args.run_id, validated_head=args.validated_head, receipt_path=args.receipt)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
