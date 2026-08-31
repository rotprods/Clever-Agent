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
            path.write_text("from fastapi import APIRouter\nrouter = APIRouter()\n@router.get('/agents')\ndef list_agents(): return []\ndef helper(): return 1\nclass PlannerAgent: pass\nregistry.register_tool('think')\n", encoding="utf-8")
            rows = extract_repository_surfaces(root, self._pin("openjarvis"))
            kinds = {row["surface_kind"] for row in rows}
            self.assertIn("http_route", kinds)
            self.assertIn("registry_registration", kinds)
            self.assertTrue(any(row["name"] == "PlannerAgent" and row["evidence_strength"] == "DEFINITION" for row in rows))
            self.assertFalse(any(row["name"] == "helper" for row in rows))
            self.assertTrue(any(row["promotion_status"] == "BEHAVIOR_MAPPED" for row in rows if row["surface_kind"] == "http_route"))

    def test_typescript_plugin_contribution_is_registration_not_definition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "extensions/demo/index.ts"
            path.parent.mkdir(parents=True)
            path.write_text("export function registerDemo(api: any) {\n api.registerTool('browser.search', { run() {} });\n api.registerChannel('telegram', {});\n api.registerGatewayMethod('health', () => true);\n}\n", encoding="utf-8")
            rows = extract_repository_surfaces(root, self._pin("openclaw"))
            registered = [row for row in rows if row["evidence_strength"] == "REGISTRATION"]
            self.assertGreaterEqual(len(registered), 3)
            self.assertTrue(all(row["promotion_status"] == "BEHAVIOR_MAPPED" for row in registered))
            self.assertTrue(any(row["runtime_owner"] == "openclaw:extensions:demo" for row in registered))

    def test_clicky_profile_promotes_native_boundary_without_generic_path_inflation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "leanring-buddy/CompanionManager.swift"
            path.parent.mkdir(parents=True)
            path.write_text("final class CompanionManager {\n func startListening() {}\n func captureScreen() {}\n func speakResponse() {}\n func pointAtTarget() {}\n func helper() {}\n}\n", encoding="utf-8")
            generic = extract_repository_surfaces(root, self._pin("clicky"))
            profiled = supplement_repository_surfaces(root, self._pin("clicky"))
            self.assertFalse(any(row["name"] == "helper" for row in generic))
            names = {row["name"] for row in profiled if row["surface_kind"] == "native_action"}
            self.assertTrue({"startListening", "captureScreen", "speakResponse", "pointAtTarget"}.issubset(names))
            self.assertTrue(all(row["evidence_strength"] == "PROFILED_BOUNDARY" for row in profiled))
            self.assertTrue(all(row["promotion_status"] == "BEHAVIOR_MAPPED" for row in profiled))

    def test_test_files_are_not_product_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "tests/test_routes.py"
            path.parent.mkdir(parents=True)
            path.write_text("@router.get('/fake')\ndef test_fake(): pass\n", encoding="utf-8")
            self.assertEqual(extract_repository_surfaces(root, self._pin("omi")), [])

    def test_summary_tracks_promotion_status(self) -> None:
        rows = [
            {"source_repo": "a", "family": "tool", "surface_kind": "definition", "evidence_strength": "DEFINITION", "promotion_status": "DISCOVERED_CANDIDATE"},
            {"source_repo": "a", "family": "tool", "surface_kind": "registry_registration", "evidence_strength": "REGISTRATION", "promotion_status": "BEHAVIOR_MAPPED"},
        ]
        summary = surface_summary(rows)
        self.assertEqual(summary, surface_summary(list(reversed(rows))))
        self.assertEqual(summary["by_promotion_status"], {"BEHAVIOR_MAPPED": 1, "DISCOVERED_CANDIDATE": 1})


if __name__ == "__main__":
    unittest.main()
