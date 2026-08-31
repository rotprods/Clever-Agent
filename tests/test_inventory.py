from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.inventory.scan_repository import scan_repository
from scripts.upstream.ledger import UpstreamPin
from scripts.upstream.sync_upstreams import acquire


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repository, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


class StructuralInventoryTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[UpstreamPin, Path]:
        source = root / "source"
        source.mkdir()
        _git(source, "init", "--quiet")
        _git(source, "config", "user.email", "test@example.invalid")
        _git(source, "config", "user.name", "Inventory Test")
        files = {
            "package.json": json.dumps({"scripts": {"test": "vitest"}}),
            "src/server.ts": "export function serve() {}\n",
            "packages/sdk/package.json": json.dumps({"name": "sdk"}),
            "packages/sdk/src/index.ts": "export const sdk = true\n",
            "tests/server.test.ts": "test('server', () => {})\n",
            ".github/workflows/ci.yml": "name: ci\n",
            "docs/architecture.md": "# Architecture\n",
            "LICENSE": "MIT\n",
            "assets/model.bin": "not source\n",
        }
        for raw_path, content in files.items():
            path = source / raw_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        _git(source, "add", ".")
        _git(source, "commit", "--quiet", "-m", "fixture")
        commit = _git(source, "rev-parse", "HEAD")
        pin = UpstreamPin("fixture", "local/fixture", source.as_posix(), "master", commit, "MIT", "test", "adapter")
        cache = root / "cache"
        acquire(pin, cache)
        return pin, cache / pin.id

    def test_scan_uses_full_git_tree_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pin, repository = self._fixture(Path(tmp))
            first = scan_repository(repository, pin)
            second = scan_repository(repository, pin)
            self.assertEqual(first, second)
            self.assertEqual(first["tree_entry_count"], 9)
            paths = {row["path"] for row in first["files"]}
            self.assertIn("assets/model.bin", paths)
            self.assertIn("packages/sdk", first["package_workspace_roots"])
            self.assertIn("tests/server.test.ts", first["test_files"])
            self.assertIn(".github/workflows/ci.yml", first["ci_release_files"])
            self.assertIn("docs/architecture.md", first["doc_files"])
            self.assertIn("LICENSE", first["license_notice_files"])
            self.assertEqual(first["summary"]["languages"]["typescript"], 3)

    def test_scan_fails_closed_on_pin_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pin, repository = self._fixture(Path(tmp))
            wrong = UpstreamPin(
                pin.id,
                pin.repository,
                pin.url,
                pin.branch,
                "f" * 40,
                pin.license,
                pin.role,
                pin.integration,
            )
            with self.assertRaises(RuntimeError):
                scan_repository(repository, wrong)


if __name__ == "__main__":
    unittest.main()
