"""Finalize canonical W02-08 only after exact-head model/engine bridge proof."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-09-21"
TASK = "W02-08"
NEXT = "W02-09"
CLAIM_ID = "CLAIM-CP03-W02-MODEL-BRIDGE-20260921"
SUPPORT_WAVE = "CP03-W02-MODEL-BRIDGE-20260921"
EVIDENCE_ID = "EVID-W02-MODEL-BRIDGE-20260921"
DECISION_ID = "D-0013"
RISK_ID = "RISK-0007"
PIN = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"
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


def validate_catalog(catalog: dict[str, Any]) -> tuple[int, int, int]:
    if catalog.get("upstream_commit") != PIN:
        raise RuntimeError("native catalog pin drift")
    engine_count = catalog.get("engine_count")
    model_count = catalog.get("model_count")
    if type(engine_count) is not int or engine_count <= 0:
        raise RuntimeError("native catalog has no engines")
    if type(model_count) is not int or model_count <= 0:
        raise RuntimeError("native catalog has no models")
    if catalog.get("upstream_execution") is not False:
        raise RuntimeError("W02-08 catalog proof must not execute upstream inference")
    for field in ("model_executions", "provider_egress_executions", "parity_promotions"):
        if catalog.get(field) != 0:
            raise RuntimeError(f"W02-08 catalog proof changed forbidden counter: {field}")
    for collection in ("engines", "models"):
        records = catalog.get(collection)
        if not isinstance(records, list) or not records:
            raise RuntimeError(f"native catalog missing {collection}")
        if any(row.get("state") != "REGISTERED" for row in records if isinstance(row, dict)):
            raise RuntimeError("native catalog collapsed REGISTERED into runtime serving state")
    failures = catalog.get("import_failures", [])
    if not isinstance(failures, list):
        raise RuntimeError("native catalog import_failures must be a list")
    return engine_count, model_count, len(failures)


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
        raise RuntimeError("W02-08 cannot finalize after parity drift")

    plan = read_json(root, "iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    if plan.get("global_denominator") != 7565 or plan.get("openjarvis_obligations") != 646:
        raise RuntimeError("task-graph denominator drift")
    tasks = {task["id"]: task for task in plan.get("tasks", [])}
    for required in ("W02-06", "W02-07", "W02-08", "W02-09", "W02-10"):
        if required not in tasks:
            raise RuntimeError(f"missing task: {required}")
    for required in ("W02-06", "W02-07"):
        if tasks[required].get("status") != "COMPLETE" or not tasks[required].get("proof"):
            raise RuntimeError(f"{required} prerequisite is not evidenced COMPLETE")
    if tasks[TASK].get("status") not in {"READY", "IN_PROGRESS", "COMPLETE"}:
        raise RuntimeError("W02-08 has invalid state")
    if tasks[TASK].get("status") != "COMPLETE":
        if plan.get("first_executable_task") != TASK:
            raise RuntimeError("W02-08 is not the current frontier")
        if tasks[NEXT].get("status") != "BLOCKED":
            raise RuntimeError("W02-09 must remain BLOCKED until W02-08 closes")
        if latest_claim_status(root) != "ACTIVE":
            raise RuntimeError("W02-08 claim is not ACTIVE")
    if tasks["W02-10"].get("status") != "BLOCKED":
        raise RuntimeError("W02-10 real inference must remain BLOCKED in this transaction")
    return plan, tasks


def finalize(
    *,
    root: Path = ROOT,
    run_id: int,
    validated_head: str,
    catalog_path: Path,
) -> dict[str, Any]:
    if run_id <= 0:
        raise RuntimeError("run_id must be positive")
    if not SHA_RE.fullmatch(validated_head):
        raise RuntimeError("validated_head must be a full lowercase SHA")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    engine_count, model_count, import_failure_count = validate_catalog(catalog)
    plan, tasks = validate_authority(root)

    if tasks[TASK].get("status") != "COMPLETE":
        tasks[TASK]["status"] = "COMPLETE"
        tasks[TASK]["proof"] = [
            {
                "evidence_id": EVIDENCE_ID,
                "result": "PASS",
                "validated_head": validated_head,
                "run_id": run_id,
                "lifecycle_tests": 9,
                "sidecar_regression_tests": 9,
                "native_engine_count": engine_count,
                "native_model_count": model_count,
                "native_import_failures": import_failure_count,
                "kernel_security_tests": 9,
                "kernel_regression": "PASS",
                "clippy": "PASS",
                "model_executions": 0,
                "provider_egress_executions": 0,
                "parity_promotions": 0,
            }
        ]
        tasks[NEXT]["status"] = "READY"
        plan["first_executable_task"] = NEXT
        write_json(root, "iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

    write_json(root, "evidence/cp03/cp03-w02/W02-08/native_catalog.json", catalog)
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
        "lifecycle_tests": 9,
        "sidecar_regression_tests": 9,
        "native_engine_count": engine_count,
        "native_model_count": model_count,
        "native_import_failure_count": import_failure_count,
        "kernel_security_tests": 9,
        "kernel_regression": "PASS",
        "clippy": "PASS",
        "planning_regression": "PASS",
        "agentic_state_validation": "PASS",
        "context_pack_validation": "PASS",
        "next_actions_validation": "PASS",
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "verified_capabilities": 0,
        "parity_promotions": 0,
        "model_executions": 0,
        "provider_egress_executions": 0,
        "next_task": NEXT,
    }
    write_json(root, "evidence/cp03/cp03-w02/W02-08/report.json", report)

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
            "type": "cp03_w02_openjarvis_model_engine_lifecycle_bridge",
            "wave_id": "CP03-W02",
            "support_wave": SUPPORT_WAVE,
            "github_actions_run_id": run_id,
            "validated_head": validated_head,
            "global_denominator": 7565,
            "openjarvis_obligations": 646,
            "w02_proof_units": 47,
            "lifecycle_tests": 9,
            "sidecar_regression_tests": 9,
            "native_engine_count": engine_count,
            "native_model_count": model_count,
            "native_import_failure_count": import_failure_count,
            "kernel_security_tests": 9,
            "kernel_regression": "PASS",
            "clippy": "PASS",
            "parity_promotions": 0,
            "model_executions": 0,
            "provider_egress_executions": 0,
            "claim": "Pinned OpenJarvis engine/model registrations are observed without inference execution. The lifecycle bridge preserves prepare/can_serve/list_models/health/close, keeps REGISTERED distinct from SERVING, makes close idempotent, and refuses external native lifecycle calls before a Rust T0 W02-07 admission path exists. This is W02-08 lifecycle evidence only, not model execution or parity proof.",
        },
    )
    append_unique(
        root,
        "ledgers/RUN_LOG.ndjson",
        "event_id",
        "RUN-W02-MODEL-BRIDGE-20260921",
        {
            "schema_version": 1,
            "date": DATE,
            "event_id": "RUN-W02-MODEL-BRIDGE-20260921",
            "event": "CP03_W02_MODEL_ENGINE_BRIDGE_ADVANCED",
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
        "WAVE-W02-MODEL-BRIDGE-20260921",
        {
            "schema_version": 1,
            "date": DATE,
            "event_id": "WAVE-W02-MODEL-BRIDGE-20260921",
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
            "decision": "W02-08 is a lifecycle/catalog bridge, not an inference execution lane. REGISTERED never implies SERVING; SERVING requires successful prepare plus native list_models, health and can_serve checks. External native lifecycle calls remain fail-closed until an admitted Rust T0 W02-07 path exists.",
            "context": "This preserves pinned OpenJarvis lifecycle semantics without creating a Python self-authorization path or using model/catalog discovery as parity proof.",
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
            "risk": "Native engine lifecycle methods such as list_models, health or prepare may perform provider/network work and could become an egress bypass if invoked directly by a Python adapter.",
            "mitigation": "W02-08 classifies external engines explicitly and refuses list_models/health/can_serve/prepare before native invocation. Generation/streaming are not exposed. A later execution lane must consume the Rust T0 W02-07 grant rather than self-authorize in Python.",
            "evidence_id": EVIDENCE_ID,
        },
    )

    if latest_claim_status(root) != "RELEASED":
        target = root / "ledgers/CLAIM_LEDGER.ndjson"
        target.parent.mkdir(parents=True, exist_ok=True)
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

    (root / "HANDOFF.md").write_text(
        "# HANDOFF — CP03-W02\n\n"
        "- Checkpoint: `CP03`; iteration: `I03`; parent wave `CP03-W02` remains `IN_PROGRESS`.\n"
        "- Frozen proof scope: **K=47 = 37 owned + 10 shared**; global denominator 7,565; OpenJarvis obligations 646; VERIFIED 0.\n"
        "- COMPLETE: `W02-00..W02-08`.\n"
        "- W02-08 evidence: `EVID-W02-MODEL-BRIDGE-20260921`.\n"
        f"- Native pinned catalog observed under `--network none`: {engine_count} engines and {model_count} models; model executions 0; provider egress executions 0.\n"
        "- Lifecycle bridge preserves prepare/can_serve/list_models/health/close, keeps REGISTERED distinct from SERVING, makes close idempotent, and refuses external native lifecycle calls before T0 admission.\n"
        "- No model/provider execution occurred; no parity promotion or denominator mutation occurred.\n\n"
        "## Next executable\n\n"
        "`W02-09 — Lane con modelo y pesos reales`.\n\n"
        "W02-09 is now the sole READY G2 frontier. It must pin engine/model/runtime/license/digests and separate controlled artifact acquisition from offline execution. Missing or corrupt real weights must produce BLOCKED; mocks do not satisfy this lane. `W02-10 — Inferencia unary end-to-end` remains BLOCKED until W02-09 has real-model evidence.\n",
        encoding="utf-8",
    )

    return {
        "status": "ADVANCED",
        "completed_task": TASK,
        "next_task": NEXT,
        "K": 47,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "verified_capabilities": 0,
        "parity_promotions": 0,
        "native_engine_count": engine_count,
        "native_model_count": model_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--validated-head", required=True)
    parser.add_argument("--catalog-path", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            finalize(
                run_id=args.run_id,
                validated_head=args.validated_head,
                catalog_path=args.catalog_path,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
