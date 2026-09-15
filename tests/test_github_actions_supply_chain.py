from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.security.audit_github_actions import audit


ROOT = Path(__file__).resolve().parents[1]


class GitHubActionsSupplyChainTests(unittest.TestCase):
    def test_repository_has_only_immutable_external_action_refs(self) -> None:
        report = audit(ROOT)
        self.assertEqual("PASS", report["status"], report["violations"])
        self.assertEqual(0, report["mutable_references"])
        self.assertGreater(report["external_action_references"], 0)

    def test_named_step_with_mutable_ref_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "unsafe.yml").write_text(
                "steps:\n  - name: unsafe\n    uses: actions/checkout@v4\n",
                encoding="utf-8",
            )
            report = audit(root)
        self.assertEqual("FAIL", report["status"])
        self.assertEqual(1, report["mutable_references"])

    def test_local_actions_are_not_external_supply_chain_refs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "local.yml").write_text(
                "steps:\n  - uses: ./actions/local\n",
                encoding="utf-8",
            )
            report = audit(root)
        self.assertEqual("PASS", report["status"])
        self.assertEqual(0, report["external_action_references"])


if __name__ == "__main__":
    unittest.main()
