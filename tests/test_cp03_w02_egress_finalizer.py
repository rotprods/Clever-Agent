from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.cp03.finalize_w02_egress import (
    CLAIM_ID,
    DECISION_ID,
    EVIDENCE_ID,
    RISK_ID,
    finalize,
)


def write_json(root: Path, path: str, value: dict) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rows(root: Path, path: str) -> list[dict]:
    target = root / path
    if not target.exists():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


class W02EgressFinalizerTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        write_json(
            root,
            "inventory/cp03/W02_SCOPE_LOCK.json",
            {
                "w02_proof_units": 47,
                "w02_owned_capabilities": 37,
                "w02_shared_capabilities": 10,
                "global_denominator": 7565,
                "openjarvis_obligations": 646,
            },
        )
        write_json(root, "GOAL_STATE.json", {"parity": {"total": 7565, "verified": 0}})
        write_json(
            root,
            "iterations/03/waves/CP03-W02/TASK_GRAPH.json",
            {
                "global_denominator": 7565,
                "openjarvis_obligations": 646,
                "first_executable_task": "W02-07",
                "tasks": [
                    {"id": "W02-06", "status": "COMPLETE", "proof": [{"result": "PASS"}]},
                    {"id": "W02-07", "status": "READY", "proof": []},
                    {"id": "W02-08", "status": "BLOCKED", "proof": []},
                    {"id": "W02-09", "status": "BLOCKED", "proof": []},
                ],
            },
        )
        claim = root / "ledgers/CLAIM_LEDGER.ndjson"
        claim.parent.mkdir(parents=True, exist_ok=True)
        claim.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "date": "2026-09-21",
                    "claim_id": CLAIM_ID,
                    "wave_id": "CP03-W02-EGRESS-BUDGET-20260921",
                    "status": "ACTIVE",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )

    def test_finalize_advances_only_w02_07_and_is_idempotent(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            head = "a" * 40
            first = finalize(root=root, run_id=123, validated_head=head, prior_pr_run_id=122)
            self.assertEqual(first["completed_task"], "W02-07")
            self.assertEqual(first["next_task"], "W02-08")
            self.assertEqual(first["parity_promotions"], 0)

            graph = json.loads((root / "iterations/03/waves/CP03-W02/TASK_GRAPH.json").read_text())
            tasks = {item["id"]: item for item in graph["tasks"]}
            self.assertEqual(graph["first_executable_task"], "W02-08")
            self.assertEqual(tasks["W02-07"]["status"], "COMPLETE")
            self.assertEqual(tasks["W02-07"]["proof"][0]["evidence_id"], EVIDENCE_ID)
            self.assertEqual(tasks["W02-08"]["status"], "READY")
            self.assertEqual(tasks["W02-09"]["status"], "BLOCKED")

            self.assertEqual(rows(root, "ledgers/EVIDENCE_LEDGER.ndjson")[0]["evidence_id"], EVIDENCE_ID)
            self.assertEqual(rows(root, "ledgers/DECISION_LEDGER.ndjson")[0]["decision_id"], DECISION_ID)
            self.assertEqual(rows(root, "ledgers/RISK_LEDGER.ndjson")[0]["risk_id"], RISK_ID)
            self.assertEqual(rows(root, "ledgers/RISK_LEDGER.ndjson")[0]["status"], "MITIGATING")
            self.assertEqual(rows(root, "ledgers/CLAIM_LEDGER.ndjson")[-1]["status"], "RELEASED")
            report = json.loads((root / "evidence/cp03/cp03-w02/W02-07/report.json").read_text())
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["validated_head"], head)
            self.assertEqual(report["provider_egress_executions"], 0)
            self.assertIn("W02-08", (root / "HANDOFF.md").read_text())

            second = finalize(root=root, run_id=123, validated_head=head, prior_pr_run_id=122)
            self.assertEqual(second, first)
            self.assertEqual(len([row for row in rows(root, "ledgers/EVIDENCE_LEDGER.ndjson") if row.get("evidence_id") == EVIDENCE_ID]), 1)
            self.assertEqual(len([row for row in rows(root, "ledgers/DECISION_LEDGER.ndjson") if row.get("decision_id") == DECISION_ID]), 1)
            self.assertEqual(len([row for row in rows(root, "ledgers/RISK_LEDGER.ndjson") if row.get("risk_id") == RISK_ID]), 1)
            self.assertEqual(len([row for row in rows(root, "ledgers/CLAIM_LEDGER.ndjson") if row.get("status") == "RELEASED"]), 1)

    def test_finalize_refuses_parity_drift(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            write_json(root, "GOAL_STATE.json", {"parity": {"total": 7565, "verified": 1}})
            with self.assertRaisesRegex(RuntimeError, "parity drift"):
                finalize(root=root, run_id=1, validated_head="b" * 40)

    def test_finalize_refuses_to_open_w02_09(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            graph_path = root / "iterations/03/waves/CP03-W02/TASK_GRAPH.json"
            graph = json.loads(graph_path.read_text())
            next(item for item in graph["tasks"] if item["id"] == "W02-09")["status"] = "READY"
            write_json(root, "iterations/03/waves/CP03-W02/TASK_GRAPH.json", graph)
            with self.assertRaisesRegex(RuntimeError, "W02-09"):
                finalize(root=root, run_id=1, validated_head="c" * 40)


if __name__ == "__main__":
    unittest.main()
