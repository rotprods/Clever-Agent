from __future__ import annotations

import unittest

from scripts.cp01.capabilities import compile_capabilities, denominator_report, gauntlet


def surface(surface_id: str, repo: str, name: str = "health", interface: dict | None = None) -> dict:
    return {
        "surface_id": surface_id,
        "source_repo": repo,
        "source_commit": "a" * 40,
        "family": "api_protocol",
        "surface_kind": "http_route",
        "name": name,
        "runtime_owner": f"{repo}:api",
        "interface": interface or {"method": "GET", "path": "/health"},
        "source_path": "src/api.py",
        "line": 10,
        "evidence_strength": "ROUTE_OR_PROTOCOL",
        "promotion_status": "BEHAVIOR_MAPPED",
    }


class CP01CapabilityTests(unittest.TestCase):
    def test_each_surface_maps_to_one_stable_capability(self) -> None:
        rows = [surface("surf_" + "1" * 24, "openjarvis"), surface("surf_" + "2" * 24, "openclaw")]
        first = compile_capabilities(rows)
        second = compile_capabilities(list(reversed(rows)))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)
        self.assertEqual({row["source_surface_id"] for row in first}, {row["surface_id"] for row in rows})

    def test_cross_repo_same_interface_is_candidate_not_deduped(self) -> None:
        rows = [surface("surf_" + "1" * 24, "openjarvis"), surface("surf_" + "2" * 24, "openclaw")]
        caps = compile_capabilities(rows)
        report = denominator_report(caps)
        self.assertEqual(report["denominator"], 2)
        self.assertFalse(report["rules"]["cross_repo_auto_dedupe"])
        self.assertEqual(len(report["cross_repo_equivalence_candidates"]), 1)
        self.assertTrue(all(row["equivalence_status"] == "UNPROVEN" for row in caps))

    def test_gauntlet_rejects_surface_loss(self) -> None:
        rows = [surface("surf_" + "1" * 24, "openjarvis"), surface("surf_" + "2" * 24, "openclaw")]
        caps = compile_capabilities(rows[:1])
        self.assertEqual(gauntlet(rows, caps)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
