from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.cp02.release import EXPECTED_DENOMINATOR, EXPECTED_OPENJARVIS, evaluate

ROOT = Path(__file__).resolve().parents[1]


class Cp02ReleaseTests(unittest.TestCase):
    def test_release_candidate_is_consistent(self) -> None:
        # CP02 is historical after the CP02 -> CP03 transition.  Re-running its
        # pre-transition evaluator against live CP03 state must fail closed;
        # the persisted, immutable release receipt is the historical proof.
        result = json.loads((ROOT / "evidence/cp02/release/CP02_RELEASE.json").read_text())
        self.assertEqual("PASS", result["status"], result["errors"])
        self.assertEqual(EXPECTED_DENOMINATOR, result["denominator"])
        self.assertEqual(EXPECTED_OPENJARVIS, result["openjarvis_obligations"])
        self.assertEqual(0, result["verified"])

    def test_release_refuses_migration_authority(self) -> None:
        result = json.loads((ROOT / "evidence/cp02/release/CP02_RELEASE.json").read_text())
        self.assertFalse(result["invariants"]["native_upstream_deletion_authorized"])
        self.assertFalse(result["invariants"]["migration_authorized"])

    def test_historical_evaluator_rejects_live_cp03_state(self) -> None:
        result = evaluate("test-head")
        self.assertEqual("FAIL", result["status"])
        self.assertIn("goal is not at CP02/I02", result["errors"])


if __name__ == "__main__":
    unittest.main()
