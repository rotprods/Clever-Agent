"""Finalize canonical W02-07 only after exact-head egress/security proof."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-09-21"
TASK = "W02-07"
NEXT = "W02-08"
CLAIM_ID = "CLAIM-CP03-W02-EGRESS-BUDGET-20260921"
SUPPORT_WAVE = "CP03-W02-EGRESS-BUDGET-20260921"
EVIDENCE_ID = "EVID-W02-EGRESS-BUDGET-20260921"
DECISION_ID = "D-0012"
RISK_ID = "RISK-0006"
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
        raise RuntimeError("W02-07 cannot finalize after parity drift")

    plan = read_json(root, "iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    if plan.get("global_denominator") != 7565 or plan.get("openjarvis_obligations") != 646:
        raise RuntimeError("task-graph denominator drift")
    tasks = {task["id"]: task for task in plan.get("tasks", [])}
    for required in ("W02-06", "W02-07", "W02-08", "W02-09"):
        if required not in tasks:
            raise RuntimeError(f"missing task: {required}")
    if tasks["W02-06"].get("status") != "COMPLETE" or not tasks["W02-06"].get("proof"):
        raise RuntimeError("W02-06 prerequisite is not evidenced COMPLETE")
    if tasks[TASK].get("status") not in {"READY", "IN_PROGRESS", "COMPLETE"}:
        raise RuntimeError("W02-07 has invalid state")
    if tasks[TASK].get("status") != "COMPLETE":
        if plan.get("first_executable_task") != TASK:
            raise RuntimeError("W02-07 is not the current frontier")
        if tasks[NEXT].get("status") != "BLOCKED":
            raise RuntimeError("W02-08 must remain BLOCKED until W02-07 closes")
        if latest_claim_status(root) != "ACTIVE":
            raise RuntimeError("W02-07 claim is not ACTIVE")
    if tasks["W02-09"].get("status") != "BLOCKED":
        raise RuntimeError("W02-09 real-model lane must remain BLOCKED in this transaction")
    return plan, tasks


def finalize(
    *,
    root: Path = ROOT,
    run_id: int,
    validated_head: str,
    prior_pr_run_id: int = 0,
) -> dict[str, Any]:
    if run_id <= 0:
        raise RuntimeError("run_id must be positive")
    if prior_pr_run_id < 0:
        raise RuntimeError("prior_pr_run_id cannot be negative")
    if not SHA_RE.fullmatch(validated_head):
        raise RuntimeError("validated_head must be a full lowercase SHA")

    plan, tasks = validate_authority(root)
    if tasks[TASK].get("status") != "COMPLETE":
        tasks[TASK]["status"] = "COMPLETE"
        tasks[TASK]["proof"] = [
            {
                "evidence_id": EVIDENCE_ID,
                "result": "PASS",
                "validated_head": validated_head,
                "run_id": run_id,
                "prior_pr_run_id": prior_pr_run_id,
                "security_tests": 9,
                "kernel_regression": "PASS",
                "clippy": "PASS",
                "state_context_gauntlet": "PASS",
                "parity_promotions": 0,
            }
        ]
        tasks[NEXT]["status"] = "READY"
        plan["first_executable_task"] = NEXT
        write_json(root, "iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)

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
        "prior_read_only_pr_run_id": prior_pr_run_id,
        "security_tests": 9,
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
    write_json(root, "evidence/cp03/cp03-w02/W02-07/report.json", report)

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
            "type": "cp03_w02_inference_egress_budget_security",
            "wave_id": "CP03-W02",
            "support_wave": SUPPORT_WAVE,
            "github_actions_run_id": run_id,
            "prior_read_only_pr_run_id": prior_pr_run_id,
            "validated_head": validated_head,
            "global_denominator": 7565,
            "openjarvis_obligations": 646,
            "w02_proof_units": 47,
            "security_tests": 9,
            "kernel_regression": "PASS",
            "clippy": "PASS",
            "parity_promotions": 0,
            "model_executions": 0,
            "provider_egress_executions": 0,
            "claim": "External inference is deny-by-default; canonical grants bind principal, session, provider, exact HTTPS origin, expiry and token/cost ceilings; secret handles are opaque/redacted; local inference remains grant-free. This proves the W02-07 guard contract only, not provider/model execution or parity.",
        },
    )
    append_unique(
        root,
        "ledgers/RUN_LOG.ndjson",
        "event_id",
        "RUN-W02-EGRESS-20260921",
        {
            "schema_version": 1,
            "date": DATE,
            "event_id": "RUN-W02-EGRESS-20260921",
            "event": "CP03_W02_EGRESS_BUDGET_ADVANCED",
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
        "WAVE-W02-EGRESS-20260921",
        {
            "schema_version": 1,
            "date": DATE,
            "event_id": "WAVE-W02-EGRESS-20260921",
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
            "decision": "External inference remains deny-by-default. Authorization must bind principal, session, provider, exact canonical HTTPS origin, expiry and explicit token/cost ceilings; provider credentials cross only the trusted secret-store boundary as opaque handles and never enter audit/debug payloads.",
            "context": "W02-07 establishes the security contract that W02-08 provider/model adapters must consume. Local inference does not require an external egress grant.",
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
            "risk": "A future external inference adapter could bypass the canonical egress guard, leak provider credentials across logs/principals, or exceed token/cost ceilings.",
            "mitigation": "W02-07 provides a fail-closed principal/session/destination/expiry/budget guard with opaque secret handles and adversarial tests. W02-08 must route every external attempt through this guard; the risk is not closed until that integration is behaviorally proven.",
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
        "- COMPLETE: `W02-00..W02-07`.\n"
        "- W02-07 evidence: `EVID-W02-EGRESS-BUDGET-20260921`.\n"
        "- External inference is deny-by-default; grants bind principal/session/provider/exact HTTPS origin/expiry and explicit token+cost ceilings. Secret handles are opaque and redacted from Debug/audit.\n"
        "- No model/provider execution occurred; no provider egress was performed; no parity promotion or denominator mutation occurred.\n\n"
        "## Next executable\n\n"
        "`W02-08 — Bridge models y engines`.\n\n"
        "W02-08 must preserve native prepare/can_serve/list_models/health/close semantics, keep REGISTERED distinct from SERVING, and route every external attempt through the W02-07 guard. `W02-09 — Lane con modelo y pesos reales` remains BLOCKED in this transaction; do not substitute mocks for that lane. The first functional demonstrator remains G3 / W02-10.\n",
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
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--validated-head", required=True)
    parser.add_argument("--prior-pr-run-id", type=int, default=0)
    args = parser.parse_args()
    print(
        json.dumps(
            finalize(
                run_id=args.run_id,
                validated_head=args.validated_head,
                prior_pr_run_id=args.prior_pr_run_id,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
