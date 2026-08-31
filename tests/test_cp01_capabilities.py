from __future__ import annotations

import unittest

from scripts.cp01.capabilities import compile_capabilities, denominator_report, gauntlet


def surface(surface_id: str, repo: str, name: str = "health", interface: dict | None = None, promotion: str = "BEHAVIOR_MAPPED", strength: str = "ROUTE_OR_PROTOCOL") -> dict:
    return {"surface_id": surface_id, "source_repo": repo, "source_commit": "a" * 40, "family": "api_protocol", "surface_kind": "http_route", "name": name, "runtime_owner": f"{repo}:api", "interface": interface or {"method": "GET", "path": "/health"}, "source_path": "src/api.py", "line": 10, "evidence_strength": strength, "promotion_status": promotion}


class CP01CapabilityTests(unittest.TestCase):
    def test_each_behavior_mapped_surface_maps_to_one_stable_capability(self) -> None:
        rows = [surface("surf_" + "1" * 24, "openjarvis"), surface("surf_" + "2" * 24, "openclaw")]
        first = compile_capabilities(rows)
        second = compile_capabilities(list(reversed(rows)))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)

    def test_candidate_definition_is_accounted_but_not_denominator_capability(self) -> None:
        mapped = surface("surf_" + "1" * 24, "openjarvis")
        candidate = surface("surf_" + "2" * 24, "openjarvis", name="ToolRegistry", promotion="DISCOVERED_CANDIDATE", strength="DEFINITION")
        rows = [mapped, candidate]
        caps = compile_capabilities(rows)
        check = gauntlet(rows, caps)
        report = denominator_report(caps, source_surface_count=2, deferred_candidate_count=1)
        self.assertEqual(len(caps), 1)
        self.assertEqual(check["status"], "PASS")
        self.assertEqual(report["source_surface_count"], 2)
        self.assertEqual(report["denominator"], 1)
        self.assertEqual(report["deferred_candidate_surface_count"], 1)

    def test_cross_repo_same_interface_is_candidate_not_deduped(self) -> None:
        rows = [surface("surf_" + "1" * 24, "openjarvis"), surface("surf_" + "2" * 24, "openclaw")]
        caps = compile_capabilities(rows)
        report = denominator_report(caps, 2, 0)
        self.assertEqual(report["denominator"], 2)
        self.assertFalse(report["rules"]["cross_repo_auto_dedupe"])
        self.assertEqual(len(report["cross_repo_equivalence_candidates"]), 1)

    def test_gauntlet_rejects_eligible_surface_loss(self) -> None:
        rows = [surface("surf_" + "1" * 24, "openjarvis"), surface("surf_" + "2" * 24, "openclaw")]
        caps = compile_capabilities(rows[:1])
        self.assertEqual(gauntlet(rows, caps)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
