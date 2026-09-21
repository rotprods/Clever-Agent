from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.cp03.finalize_w02_real_model import (
    CLAIM_ID,
    DECISION_ID,
    EVIDENCE_ID,
    MODEL_SHA256,
    MODEL_SIZE,
    RISK_ID,
    finalize,
)

HEAD = "a" * 40
RUN_ID = 12345


def write_json(root: Path, path: str, value: dict) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rows(root: Path, path: str) -> list[dict]:
    target = root / path
    if not target.exists():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


class W02RealModelFinalizerTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
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
            "inventory/cp03/W02_REAL_MODEL_LANE.json",
            {
                "upstream": {"commit": "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"},
                "artifact": {"sha256": MODEL_SHA256, "size_bytes": MODEL_SIZE},
                "counters": {
                    "verified_capabilities": 0,
                    "parity_promotions": 0,
                    "model_executions": 0,
                    "provider_egress_executions": 0,
                },
            },
        )
        write_json(
            root,
            "iterations/03/waves/CP03-W02/TASK_GRAPH.json",
            {
                "global_denominator": 7565,
                "openjarvis_obligations": 646,
                "first_executable_task": "W02-09",
                "tasks": [
                    {"id": "W02-01", "status": "COMPLETE", "proof": [{"result": "PASS"}]},
                    {"id": "W02-02", "status": "COMPLETE", "proof": [{"result": "PASS"}]},
                    {"id": "W02-08", "status": "COMPLETE", "proof": [{"result": "PASS"}]},
                    {"id": "W02-09", "status": "READY", "proof": [], "depends_on": ["W02-01", "W02-02"]},
                    {"id": "W02-10", "status": "BLOCKED", "proof": [], "depends_on": ["W02-08", "W02-09"]},
                ],
            },
        )
        claim = root / "ledgers/CLAIM_LEDGER.ndjson"
        claim.parent.mkdir(parents=True, exist_ok=True)
        claim.write_text(
            json.dumps({"schema_version": 1, "claim_id": CLAIM_ID, "status": "ACTIVE"}) + "\n",
            encoding="utf-8",
        )
        write_json(
            root,
            "sessions/20260921-w02-real-model/CLAIM.json",
            {"schema_version": 1, "claim_id": CLAIM_ID, "status": "ACTIVE"},
        )
        receipt = root / "receipt.json"
        write_json(
            root,
            "receipt.json",
            {
                "project_id": "CLEVER-JARVIS-001",
                "checkpoint": "CP03",
                "parent_wave": "CP03-W02",
                "task": "W02-09",
                "status": "PASS",
                "validated_head": HEAD,
                "github_actions_run_id": RUN_ID,
                "openjarvis_commit": "72033b8ec288aa067ce4530ff9d96bf231e9c4e5",
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
            },
        )
        return receipt

    def test_finalize_marks_only_w02_09_complete_and_opens_w02_10(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.fixture(root)
            report = finalize(root=root, run_id=RUN_ID, validated_head=HEAD, receipt_path=receipt)
            graph = json.loads((root / "iterations/03/waves/CP03-W02/TASK_GRAPH.json").read_text())
            tasks = {row["id"]: row for row in graph["tasks"]}
            self.assertEqual(tasks["W02-09"]["status"], "COMPLETE")
            self.assertEqual(tasks["W02-10"]["status"], "READY")
            self.assertEqual(graph["first_executable_task"], "W02-10")
            self.assertEqual(tasks["W02-09"]["proof"][0]["artifact_sha256"], MODEL_SHA256)
            self.assertEqual(report["next_task"], "W02-10")
            self.assertEqual(report["model_executions"], 0)
            self.assertEqual(report["parity_promotions"], 0)
            self.assertEqual(report["verified_capabilities"], 0)
            self.assertEqual(report["global_denominator"], 7565)

            self.assertEqual(rows(root, "ledgers/EVIDENCE_LEDGER.ndjson")[0]["evidence_id"], EVIDENCE_ID)
            self.assertEqual(rows(root, "ledgers/DECISION_LEDGER.ndjson")[0]["decision_id"], DECISION_ID)
            self.assertEqual(rows(root, "ledgers/RISK_LEDGER.ndjson")[0]["risk_id"], RISK_ID)
            self.assertEqual(rows(root, "ledgers/CLAIM_LEDGER.ndjson")[-1]["status"], "RELEASED")
            claim = json.loads((root / "sessions/20260921-w02-real-model/CLAIM.json").read_text())
            self.assertEqual(claim["status"], "RELEASED")
            self.assertIn("W02-10 — Inferencia unary end-to-end", (root / "HANDOFF.md").read_text())

    def test_finalize_is_idempotent_for_ledgers(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.fixture(root)
            finalize(root=root, run_id=RUN_ID, validated_head=HEAD, receipt_path=receipt)
            finalize(root=root, run_id=RUN_ID, validated_head=HEAD, receipt_path=receipt)
            self.assertEqual(len(rows(root, "ledgers/EVIDENCE_LEDGER.ndjson")), 1)
            self.assertEqual(len(rows(root, "ledgers/DECISION_LEDGER.ndjson")), 1)
            self.assertEqual(len(rows(root, "ledgers/RISK_LEDGER.ndjson")), 1)
            releases = [r for r in rows(root, "ledgers/CLAIM_LEDGER.ndjson") if r.get("status") == "RELEASED"]
            self.assertEqual(len(releases), 1)

    def test_receipt_with_execution_or_digest_drift_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.fixture(root)
            data = json.loads(receipt.read_text())
            data["model_executions"] = 1
            receipt.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError, "model_executions"):
                finalize(root=root, run_id=RUN_ID, validated_head=HEAD, receipt_path=receipt)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.fixture(root)
            data = json.loads(receipt.read_text())
            data["artifact_sha256"] = "0" * 64
            receipt.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError, "artifact_sha256"):
                finalize(root=root, run_id=RUN_ID, validated_head=HEAD, receipt_path=receipt)

    def test_incomplete_dependency_keeps_transition_fail_closed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.fixture(root)
            graph_path = root / "iterations/03/waves/CP03-W02/TASK_GRAPH.json"
            graph = json.loads(graph_path.read_text())
            for row in graph["tasks"]:
                if row["id"] == "W02-02":
                    row["status"] = "BLOCKED"
            graph_path.write_text(json.dumps(graph))
            with self.assertRaisesRegex(RuntimeError, "prerequisite"):
                finalize(root=root, run_id=RUN_ID, validated_head=HEAD, receipt_path=receipt)


if __name__ == "__main__":
    unittest.main()
