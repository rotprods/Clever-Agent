from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.cp01.profiles import supplement_repository_surfaces
from scripts.cp01.surfaces import extract_repository_surfaces, surface_summary
from scripts.upstream.ledger import UpstreamPin


class CP01BehavioralSurfaceTests(unittest.TestCase):
    def _pin(self, repo_id: str) -> UpstreamPin:
        return UpstreamPin(repo_id, f"fixture/{repo_id}", f"https://github.com/fixture/{repo_id}.git", "main", "a" * 40, "MIT", "test", "adapter")

    def test_python_routes_registrations_and_definitions_have_distinct_strength(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "src/openjarvis/agents/api.py"
            path.parent.mkdir(parents=True)
            path.write_text(
                "from fastapi import APIRouter\n"
                "router = APIRouter()\n"
                "@router.get('/agents')\n"
                "def list_agents(): return []\n"
                "class PlannerAgent: pass\n"
                "registry.register_tool('think')\n",
                encoding="utf-8",
            )
            rows = extract_repository_surfaces(root, self._pin("openjarvis"))
            kinds = {row["surface_kind"] for row in rows}
            self.assertIn("http_route", kinds)
            self.assertIn("registry_registration", kinds)
            self.assertTrue(any(row["name"] == "PlannerAgent" and row["evidence_strength"] == "DEFINITION" for row in rows))
            self.assertTrue(any(row["promotion_status"] == "BEHAVIOR_MAPPED" for row in rows if row["surface_kind"] == "http_route"))

    def test_typescript_plugin_contribution_is_registration_not_definition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "extensions/demo/index.ts"
            path.parent.mkdir(parents=True)
            path.write_text(
                "export function registerDemo(api: any) {\n"
                "  api.registerTool('browser.search', { run() {} });\n"
                "  api.registerChannel('telegram', {});\n"
                "  api.registerGatewayMethod('health', () => true);\n"
                "}\n",
                encoding="utf-8",
            )
            rows = extract_repository_surfaces(root, self._pin("openclaw"))
            registered = [row for row in rows if row["evidence_strength"] == "REGISTRATION"]
            self.assertGreaterEqual(len(registered), 3)
            self.assertTrue(all(row["promotion_status"] == "BEHAVIOR_MAPPED" for row in registered))
            self.assertTrue(any(row["runtime_owner"] == "openclaw:extensions:demo" for row in registered))

    def test_clicky_profile_completes_native_boundary_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "leanring-buddy/CompanionManager.swift"
            path.parent.mkdir(parents=True)
            path.write_text(
                "final class CompanionManager {\n"
                "  func startListening() {}\n"
                "  func captureScreen() {}\n"
                "  func speakResponse() {}\n"
                "  func pointAtTarget() {}\n"
                "}\n",
                encoding="utf-8",
            )
            generic = extract_repository_surfaces(root, self._pin("clicky"))
            profiled = supplement_repository_surfaces(root, self._pin("clicky"))
            self.assertGreaterEqual(len([row for row in generic if row["surface_kind"] == "native_action"]), 3)
            names = {row["name"] for row in profiled if row["surface_kind"] == "native_action"}
            self.assertTrue({"startListening", "captureScreen", "speakResponse", "pointAtTarget"}.issubset(names))
            self.assertTrue(all(row["promotion_status"] == "DISCOVERED_CANDIDATE" for row in profiled))

    def test_test_files_are_not_product_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "tests/test_routes.py"
            path.parent.mkdir(parents=True)
            path.write_text("@router.get('/fake')\ndef test_fake(): pass\n", encoding="utf-8")
            rows = extract_repository_surfaces(root, self._pin("omi"))
            self.assertEqual(rows, [])

    def test_summary_is_deterministic(self) -> None:
        rows = [
            {"source_repo": "a", "family": "tool", "surface_kind": "definition", "evidence_strength": "DEFINITION"},
            {"source_repo": "a", "family": "tool", "surface_kind": "registry_registration", "evidence_strength": "REGISTRATION"},
        ]
        self.assertEqual(surface_summary(rows), surface_summary(list(reversed(rows))))


if __name__ == "__main__":
    unittest.main()
