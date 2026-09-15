from __future__ import annotations

import unittest
from unittest import mock

from scripts import release_gauntlet


class ReleaseGauntletTests(unittest.TestCase):
    def test_current_frontier_is_evidence_linked(self) -> None:
        result = release_gauntlet.validate_frontier()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["frontier"], "W02-06")
        self.assertEqual(result["parity_promotions"], 0)

    def test_changed_release_workflows_are_hardened(self) -> None:
        self.assertEqual(release_gauntlet.validate_workflows()["status"], "PASS")

    def test_unpinned_action_is_rejected(self) -> None:
        with self.assertRaisesRegex(release_gauntlet.GauntletError, "unpinned"):
            release_gauntlet.validate_workflow_text("steps:\n  - uses: actions/checkout@v4\n", "bad.yml")

    def test_pull_request_target_is_rejected(self) -> None:
        with self.assertRaisesRegex(release_gauntlet.GauntletError, "pull_request_target"):
            release_gauntlet.validate_workflow_text("pull_request_target:\n", "bad.yml")

    def test_write_workflow_without_cas_is_rejected(self) -> None:
        text = "permissions:\n  contents: write\nsteps:\n  - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n"
        with self.assertRaisesRegex(release_gauntlet.GauntletError, "CAS"):
            release_gauntlet.validate_workflow_text(text, "bad.yml")

    def test_missing_cargo_is_not_a_full_pass(self) -> None:
        passing = {"status": "PASS"}
        with (mock.patch.object(release_gauntlet, "validate_frontier", return_value=passing),
              mock.patch.object(release_gauntlet, "validate_workflows", return_value=passing),
              mock.patch.object(release_gauntlet, "run", return_value=passing),
              mock.patch.object(release_gauntlet.shutil, "which", return_value=None)):
            self.assertEqual(release_gauntlet.execute(require_rust=True)["status"], "BLOCKED")
            self.assertEqual(release_gauntlet.execute(require_rust=False)["status"], "PASS_WITH_RUST_BLOCKED")


if __name__ == "__main__":
    unittest.main()
