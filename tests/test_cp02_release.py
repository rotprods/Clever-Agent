from __future__ import annotations

import unittest

from scripts.cp02.release import EXPECTED_DENOMINATOR, EXPECTED_OPENJARVIS, evaluate


class Cp02ReleaseTests(unittest.TestCase):
    def test_release_candidate_is_consistent(self) -> None:
        result = evaluate("test-head")
        self.assertEqual("PASS", result["status"], result["errors"])
        self.assertEqual(EXPECTED_DENOMINATOR, result["denominator"])
        self.assertEqual(EXPECTED_OPENJARVIS, result["openjarvis_obligations"])
        self.assertEqual(0, result["verified"])

    def test_release_refuses_migration_authority(self) -> None:
        result = evaluate("test-head")
        self.assertFalse(result["invariants"]["native_upstream_deletion_authorized"])
        self.assertFalse(result["invariants"]["migration_authorized"])


if __name__ == "__main__":
    unittest.main()
