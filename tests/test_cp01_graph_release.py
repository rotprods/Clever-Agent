from __future__ import annotations

import unittest

from scripts.cp01.graph_gauntlet import CORE_20D, build_graph, gauntlet
from scripts.cp01.release import _contract_requirements


class CP01GraphReleaseTests(unittest.TestCase):
    def fixture(self):
        surface = {
            "surface_id": "surf_" + "1" * 24,
            "source_repo": "openjarvis",
            "source_commit": "a" * 40,
            "family": "tool",
            "surface_kind": "registry_registration",
            "source_path": "src/tools.py",
            "evidence_strength": "REGISTRATION",
            "promotion_status": "BEHAVIOR_MAPPED",
            "interface": {"registrar": "registerTool"},
            "state_effects": ["state"],
            "permissions": ["permission"],
            "lifecycle": ["register"],
            "failure_semantics": ["retry"],
            "platform_constraints": ["desktop_server"],
        }
        capability = {
            "capability_id": "cap_" + "2" * 24,
            "source_surface_id": surface["surface_id"],
            "source_repo": "openjarvis",
            "family": "tool",
            "surface_kind": "registry_registration",
            "runtime_owner": "openjarvis:tools",
            "parity_status": "UNVERIFIED",
            "equivalence_status": "UNPROVEN",
            "evidence_strength": "REGISTRATION",
        }
        baselines = {"status": "PASS", "sources": [{"source_repo": "openjarvis"}], "baselines": [{"source_repo": "openjarvis", "manifest_path": "pyproject.toml", "name": "tests", "classification": "UNTRUSTED_EXECUTION_GATED", "execution_status": "NOT_RUN", "command": "pytest"}]}
        supply = {"status": "PASS", "sources": [{"source_repo": "openjarvis", "declared_license": "MIT", "license_verification": {"status": "VERIFIED_DECLARATION_MATCH"}, "counts": {"lockfiles": 1}}]}
        return surface, capability, baselines, supply

    def test_graph_preserves_capability_surface_owner_and_20d_pressure(self) -> None:
        surface, capability, baselines, supply = self.fixture()
        graph = build_graph([capability], [surface], baselines, supply)
        relations = {edge["relation"] for edge in graph["edges"]}
        self.assertTrue({"exposes", "implemented_by", "registered_via", "owned_by", "persists_to", "permissioned_by", "executes_on", "recovers_via"}.issubset(relations))
        self.assertTrue(CORE_20D.issubset(set(graph["cos20d_pressure"][capability["capability_id"]])))

    def test_candidate_surface_remains_in_graph_without_capability(self) -> None:
        surface, capability, baselines, supply = self.fixture()
        candidate = dict(surface)
        candidate["surface_id"] = "surf_" + "3" * 24
        candidate["promotion_status"] = "DISCOVERED_CANDIDATE"
        candidate["evidence_strength"] = "DEFINITION"
        graph = build_graph([capability], [surface, candidate], baselines, supply)
        candidate_node = f"surface:{candidate['surface_id']}"
        self.assertTrue(any(node["id"] == candidate_node for node in graph["nodes"]))
        self.assertFalse(any(edge["target"] == candidate_node and edge["relation"] == "implemented_by" for edge in graph["edges"]))

    def test_gauntlet_detects_repo_coverage_mismatch(self) -> None:
        surface, capability, baselines, supply = self.fixture()
        graph = build_graph([capability], [surface], baselines, supply)
        self.assertEqual(gauntlet(graph, [capability], [surface], baselines, supply)["status"], "FAIL")

    def test_contract_requirements_are_evidence_pressured(self) -> None:
        capabilities = [{"family": "memory_persistence"}, {"family": "device_wearable"}, {"family": "tool"}]
        rows = {row["id"]: row for row in _contract_requirements(capabilities)}
        self.assertTrue(rows["C02-MEMORY"]["required"])
        self.assertTrue(rows["C02-EMBODIMENT"]["required"])
        self.assertGreater(rows["C02-ACTION"]["evidence_count"], 0)


if __name__ == "__main__":
    unittest.main()
