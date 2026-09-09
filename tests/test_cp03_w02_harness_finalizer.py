from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.cp03 import finalize_w02_harness


class HarnessFinalizerTests(unittest.TestCase):
    def _write_lane(self, root: Path, lane: str, count: int, *, parity: int = 0) -> None:
        folder = root / "evidence/cp03/cp03-w02/W02-02" / lane
        folder.mkdir(parents=True, exist_ok=True)
        ids = [f"test-{i}" for i in range(count)]
        (folder / "report.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "executed_count": count,
                    "executed_test_ids": ids,
                    "required_test_ids": ids,
                    "failed": 0,
                    "ignored": 0,
                    "parity_promotions": parity,
                }
            ),
            encoding="utf-8",
        )
        (folder / "results.junit.xml").write_text(
            f'<testsuite tests="{count}" failures="0" skipped="0"></testsuite>',
            encoding="utf-8",
        )

    def _root(self) -> tempfile.TemporaryDirectory[str]:
        return tempfile.TemporaryDirectory()

    def test_validate_reports_requires_all_three_lanes(self) -> None:
        with self._root() as td:
            root = Path(td)
            self._write_lane(root, "fake", 6)
            with patch.object(finalize_w02_harness, "ROOT", root):
                with self.assertRaises(RuntimeError):
                    finalize_w02_harness.validate_reports(root)

    def test_validate_reports_rejects_parity_promotion(self) -> None:
        with self._root() as td:
            root = Path(td)
            self._write_lane(root, "fake", 6, parity=1)
            self._write_lane(root, "native", 1)
            self._write_lane(root, "retest", 6)
            red = root / "evidence/cp03/cp03-w02/W02-02/red/audit.log"
            red.parent.mkdir(parents=True, exist_ok=True)
            red.write_text("silent return paths", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                finalize_w02_harness.validate_reports(root)

    def test_validate_reports_rejects_skipped_junit(self) -> None:
        with self._root() as td:
            root = Path(td)
            for lane, count in {"fake": 6, "native": 1, "retest": 6}.items():
                self._write_lane(root, lane, count)
            (root / "evidence/cp03/cp03-w02/W02-02/native/results.junit.xml").write_text(
                '<testsuite tests="1" failures="0" skipped="1"></testsuite>', encoding="utf-8"
            )
            red = root / "evidence/cp03/cp03-w02/W02-02/red/audit.log"
            red.parent.mkdir(parents=True, exist_ok=True)
            red.write_text("silent return paths", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                finalize_w02_harness.validate_reports(root)

    def test_validate_reports_accepts_complete_evidence(self) -> None:
        with self._root() as td:
            root = Path(td)
            for lane, count in {"fake": 6, "native": 1, "retest": 6}.items():
                self._write_lane(root, lane, count)
            red = root / "evidence/cp03/cp03-w02/W02-02/red/audit.log"
            red.parent.mkdir(parents=True, exist_ok=True)
            red.write_text("historical audit: silent return paths", encoding="utf-8")
            reports = finalize_w02_harness.validate_reports(root)
            self.assertEqual(set(reports), {"fake", "native", "retest"})

    def test_latest_claim_status_uses_last_event(self) -> None:
        with self._root() as td:
            root = Path(td)
            ledger = root / "ledgers/CLAIM_LEDGER.ndjson"
            ledger.parent.mkdir(parents=True, exist_ok=True)
            ledger.write_text(
                '{"claim_id":"x","status":"ACTIVE"}\n'
                '{"claim_id":"x","status":"RELEASED"}\n',
                encoding="utf-8",
            )
            with patch.object(finalize_w02_harness, "ROOT", root):
                self.assertEqual(finalize_w02_harness.latest_claim_status("x"), "RELEASED")

    def _workflow(self) -> str:
        return (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/cp03-w02-harness-finalize.yml"
        ).read_text(encoding="utf-8")

    def test_workflow_normalizes_upload_digest_to_canonical_sha256_form(self) -> None:
        workflow = self._workflow()
        self.assertIn(
            "--artifact-digest 'sha256:${{ steps.proof.outputs.artifact-digest }}'",
            workflow,
        )
        self.assertNotIn(
            "--artifact-digest '${{ steps.proof.outputs.artifact-digest }}'",
            workflow,
        )

    def test_workflow_enumerates_untracked_files_instead_of_parent_directory(self) -> None:
        workflow = self._workflow()
        self.assertIn("'--porcelain=v1','-uall'", workflow)
        self.assertNotIn("'--porcelain=v1','-unormal'", workflow)
        self.assertIn("generated_prefix='evidence/cp03/cp03-w02/W02-02/'", workflow)


if __name__ == "__main__":
    unittest.main()
