from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.cp01.baselines import discover_repo_baselines
from scripts.cp01.supply_chain import _license_paths, _lockfiles
from scripts.upstream.ledger import UpstreamPin


class CP01BaselineSupplyChainTests(unittest.TestCase):
    def pin(self, repo_id: str = "openclaw") -> UpstreamPin:
        return UpstreamPin(repo_id, f"fixture/{repo_id}", f"https://github.com/fixture/{repo_id}.git", "main", "a" * 40, "MIT", "test", "adapter")

    def test_package_scripts_are_discovered_but_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps({"scripts": {"test": "vitest", "build": "tsc", "start": "node app.js"}}), encoding="utf-8")
            rows = discover_repo_baselines(root, self.pin(), {"test_files": [], "manifests": ["package.json"]})
            self.assertEqual({row["name"] for row in rows}, {"build", "test"})
            self.assertTrue(all(row["execution_status"] == "NOT_RUN" for row in rows))
            self.assertTrue(all(row["classification"] == "UNTRUSTED_EXECUTION_GATED" for row in rows))

    def test_hardware_classification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            firmware = root / "firmware/package.json"
            firmware.parent.mkdir()
            firmware.write_text(json.dumps({"scripts": {"test": "west test"}}), encoding="utf-8")
            rows = discover_repo_baselines(root, self.pin("omi"), {"test_files": [], "manifests": ["firmware/package.json"]})
            self.assertEqual(rows[0]["classification"], "HARDWARE_GATED")

    def test_xcode_project_is_platform_gated_not_not_applicable(self) -> None:
        rows = discover_repo_baselines(
            Path("."),
            self.pin("clicky"),
            {"test_files": [], "manifests": ["leanring-buddy/leanring-buddy.xcodeproj/project.pbxproj"]},
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "xcode-project")
        self.assertEqual(rows[0]["classification"], "PLATFORM_GATED")
        self.assertEqual(rows[0]["execution_status"], "NOT_RUN")
        self.assertIn("xcodebuild -project leanring-buddy/leanring-buddy.xcodeproj -list", rows[0]["command"])

    def test_lockfile_and_license_inventory_is_tree_based(self) -> None:
        paths = ["LICENSE", "NOTICE.md", "pnpm-lock.yaml", "packages/a/package.json", "firmware/west.yml", "licenses/vendor.txt"]
        self.assertIn("pnpm-lock.yaml", _lockfiles(paths))
        self.assertIn("LICENSE", _license_paths(paths))
        self.assertIn("NOTICE.md", _license_paths(paths))
        self.assertIn("licenses/vendor.txt", _license_paths(paths))


if __name__ == "__main__":
    unittest.main()
