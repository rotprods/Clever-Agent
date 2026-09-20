from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "ledgers/CLAIM_LEDGER.ndjson"
RUN_LOG = ROOT / "ledgers/RUN_LOG.ndjson"
CLAIM_ID = "CLAIM-CP03-W02-EGRESS-BUDGET-001"
WAVE_ID = "CP03-W02-EGRESS-BUDGET-20260921"
SCOPE = [
    "kernel/crates/clever-kernel/src/inference_policy.rs",
    "kernel/crates/clever-kernel/src/lib.rs",
    "kernel/crates/clever-kernel/tests/inference_policy.rs",
    "tests/test_cp03_w02_egress_budget.py",
    ".github/workflows/cp03-w02-egress-budget.yml",
    "scripts/cp03/w02_egress_budget_claim.py",
    "iterations/03/waves/CP03-W02/TASK_GRAPH.json",
    "ledgers/CLAIM_LEDGER.ndjson",
    "ledgers/EVIDENCE_LEDGER.ndjson",
    "ledgers/RUN_LOG.ndjson",
    "ledgers/WAVE_LEDGER.ndjson",
    "ledgers/DECISION_LEDGER.ndjson",
    "ledgers/RISK_LEDGER.ndjson",
    "HANDOFF.md",
    ".agentic/context/CURRENT_CONTEXT.json",
    ".agentic/context/CURRENT_CONTEXT.md",
    "evidence/cp03/cp03-w02/W02-07/**",
]


def latest_claim_rows() -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for raw in LEDGER.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        claim_id = row.get("claim_id")
        if claim_id:
            previous = latest.get(claim_id, {})
            merged = dict(previous)
            merged.update(row)
            latest[claim_id] = merged
    return latest


def run_event_exists(event_id: str) -> bool:
    for raw in RUN_LOG.read_text(encoding="utf-8").splitlines():
        if raw.strip() and json.loads(raw).get("event_id") == event_id:
            return True
    return False


def main() -> int:
    latest = latest_claim_rows()
    if latest.get(CLAIM_ID, {}).get("status") == "ACTIVE":
        print(f"claim already active: {CLAIM_ID}")
        return 0

    overlapping = []
    our_scope = set(SCOPE)
    for claim_id, row in latest.items():
        if row.get("status") != "ACTIVE":
            continue
        overlap = sorted(our_scope.intersection(row.get("scope") or []))
        if overlap:
            overlapping.append((claim_id, overlap))
    if overlapping:
        raise SystemExit(f"active claim overlap: {overlapping}")

    row = {
        "schema_version": 1,
        "date": "2026-09-21",
        "claim_id": CLAIM_ID,
        "wave_id": WAVE_ID,
        "parent_wave": "CP03-W02",
        "canonical_task": "W02-07",
        "owner": "chatgpt-gpt-5.6-sol",
        "scope": SCOPE,
        "coordination": (
            "Canonical W02-07 only: deny-by-default remote inference egress, trusted destination grant binding, "
            "principal/session isolation, opaque secret handles, token/cost ceilings, redacted audit evidence, and exact-head finalization. "
            "No model execution, W02-08 bridge, W02-09 model acquisition, denominator mutation, parity promotion, tool execution, or native state migration."
        ),
        "status": "ACTIVE",
    }
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    event_id = "RUN-W02-EGRESS-BUDGET-WORK-STARTED-20260921"
    if not run_event_exists(event_id):
        event = {
            "schema_version": 1,
            "date": "2026-09-21",
            "event_id": event_id,
            "event": "WORK_STARTED",
            "goal_id": "CLEVER-JARVIS-001",
            "checkpoint": "CP03",
            "iteration": "I03",
            "wave_id": "CP03-W02",
            "support_wave": WAVE_ID,
            "task": "W02-07",
            "status": "IN_PROGRESS",
            "parity_promotions": 0,
        }
        with RUN_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")

    print(f"activated {CLAIM_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
