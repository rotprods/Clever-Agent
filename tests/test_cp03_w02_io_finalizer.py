from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.cp03 import finalize_w02_io


HEAD = "a" * 40
DIGEST = "sha256:" + "b" * 64


class W02IOFinalizerTests(unittest.TestCase):
    def _write_json(self, root: Path, path: str, payload: dict) -> None:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _root(self) -> tempfile.TemporaryDirectory[str]:
        return tempfile.TemporaryDirectory()

    def _build_root(self, root: Path) -> None:
        self._write_json(
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
        self._write_json(
            root,
            "GOAL_STATE.json",
            {"parity": {"total": 7565, "verified": 0}},
        )
        tasks = [
            {"id": "W02-02", "status": "COMPLETE", "depends_on": [], "proof": [{"evidence_id": "old"}]},
            {"id": "W02-03", "status": "READY", "depends_on": ["W02-02"], "proof": []},
            {"id": "W02-04", "status": "BLOCKED", "depends_on": ["W02-03"], "proof": []},
            {"id": "W02-05", "status": "BLOCKED", "depends_on": ["W02-03"], "proof": []},
            {"id": "W02-06", "status": "BLOCKED", "depends_on": ["W02-05"], "proof": []},
        ]
        self._write_json(
            root,
            "iterations/03/waves/CP03-W02/TASK_GRAPH.json",
            {
                "wave": "CP03-W02",
                "w02_obligation_count": 47,
                "first_executable_task": "W02-03",
                "status": "IN_PROGRESS",
                "tasks": tasks,
            },
        )
        ledger_dir = root / "ledgers"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        (ledger_dir / "CLAIM_LEDGER.ndjson").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "claim_id": finalize_w02_io.CLAIM_ID,
                    "wave_id": finalize_w02_io.SUPPORT_WAVE,
                    "status": "ACTIVE",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        for name in ("EVIDENCE_LEDGER.ndjson", "RUN_LOG.ndjson", "WAVE_LEDGER.ndjson"):
            (ledger_dir / name).write_text("", encoding="utf-8")

        evidence = root / finalize_w02_io.EVIDENCE_ROOT
        (evidence / "tests").mkdir(parents=True, exist_ok=True)
        report = {
            "schema_version": 1,
            "status": "PASS",
            "validated_head": HEAD,
            "executed_test_ids": list(finalize_w02_io.REQUIRED_TESTS),
            "required_test_ids": list(finalize_w02_io.REQUIRED_TESTS),
            "executed_count": len(finalize_w02_io.REQUIRED_TESTS),
            "failed": 0,
            "ignored": 0,
            "parity_promotions": 0,
        }
        (evidence / "report.json").write_text(json.dumps(report), encoding="utf-8")
        (evidence / "results.junit.xml").write_text(
            '<testsuite tests="3" failures="0" skipped="0"></testsuite>',
            encoding="utf-8",
        )
        (evidence / "parity.json").write_text(
            json.dumps({"source_repo": "openjarvis", "total": 646, "verified": 0}),
            encoding="utf-8",
        )
        (evidence / "clippy.log").write_text("Finished dev profile\n", encoding="utf-8")
        for test_id in finalize_w02_io.REQUIRED_TESTS:
            (evidence / "tests" / f"{test_id}.log").write_text(
                "running 1 test\n"
                f"test {test_id} ... ok\n"
                "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 99 filtered out\n",
                encoding="utf-8",
            )

    def _finalize(self, root: Path):
        with patch.object(finalize_w02_io, "ROOT", root):
            return finalize_w02_io.finalize(
                run_id=123,
                validated_head=HEAD,
                artifact_id=456,
                artifact_digest=DIGEST,
            )

    def test_transition_completes_only_w02_03_and_opens_04_05(self) -> None:
        with self._root() as td:
            root = Path(td)
            self._build_root(root)
            result = self._finalize(root)
            self.assertEqual(result["completed_task"], "W02-03")
            self.assertEqual(result["next_task"], "W02-04")
            plan = json.loads(
                (root / "iterations/03/waves/CP03-W02/TASK_GRAPH.json").read_text(encoding="utf-8")
            )
            tasks = {row["id"]: row for row in plan["tasks"]}
            self.assertEqual(tasks["W02-03"]["status"], "COMPLETE")
            self.assertEqual(tasks["W02-04"]["status"], "READY")
            self.assertEqual(tasks["W02-05"]["status"], "READY")
            self.assertEqual(tasks["W02-06"]["status"], "BLOCKED")
            self.assertEqual(plan["first_executable_task"], "W02-04")
            self.assertEqual(tasks["W02-03"]["proof"][0]["evidence_id"], finalize_w02_io.EVIDENCE_ID)

    def test_rejects_parity_drift(self) -> None:
        with self._root() as td:
            root = Path(td)
            self._build_root(root)
            self._write_json(root, "GOAL_STATE.json", {"parity": {"total": 7565, "verified": 1}})
            with self.assertRaisesRegex(RuntimeError, "parity/denominator drift"):
                self._finalize(root)

    def test_rejects_scope_lock_drift(self) -> None:
        with self._root() as td:
            root = Path(td)
            self._build_root(root)
            lock = json.loads((root / "inventory/cp03/W02_SCOPE_LOCK.json").read_text(encoding="utf-8"))
            lock["w02_proof_units"] = 46
            self._write_json(root, "inventory/cp03/W02_SCOPE_LOCK.json", lock)
            with self.assertRaisesRegex(RuntimeError, "scope lock drift"):
                self._finalize(root)

    def test_rejects_incomplete_w02_02_prerequisite(self) -> None:
        with self._root() as td:
            root = Path(td)
            self._build_root(root)
            path = root / "iterations/03/waves/CP03-W02/TASK_GRAPH.json"
            plan = json.loads(path.read_text(encoding="utf-8"))
            plan["tasks"][0]["status"] = "READY"
            self._write_json(root, "iterations/03/waves/CP03-W02/TASK_GRAPH.json", plan)
            with self.assertRaisesRegex(RuntimeError, "prerequisite W02-02"):
                self._finalize(root)

    def test_evidence_and_release_are_idempotent(self) -> None:
        with self._root() as td:
            root = Path(td)
            self._build_root(root)
            self._finalize(root)
            self._finalize(root)
            evidence_rows = [
                json.loads(line)
                for line in (root / "ledgers/EVIDENCE_LEDGER.ndjson").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(
                sum(row.get("evidence_id") == finalize_w02_io.EVIDENCE_ID for row in evidence_rows),
                1,
            )
            claim_rows = [
                json.loads(line)
                for line in (root / "ledgers/CLAIM_LEDGER.ndjson").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            releases = [
                row
                for row in claim_rows
                if row.get("claim_id") == finalize_w02_io.CLAIM_ID and row.get("status") == "RELEASED"
            ]
            self.assertEqual(len(releases), 1)

    def test_rejects_wrong_evidence_head(self) -> None:
        with self._root() as td:
            root = Path(td)
            self._build_root(root)
            evidence = root / finalize_w02_io.EVIDENCE_ROOT / "report.json"
            report = json.loads(evidence.read_text(encoding="utf-8"))
            report["validated_head"] = "c" * 40
            evidence.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "report head"):
                self._finalize(root)


if __name__ == "__main__":
    unittest.main()
