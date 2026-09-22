from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from scripts.cp03 import w02_parity_graph as graph

ROOT = Path(__file__).resolve().parents[1]


class W02ParityGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = graph.compile_root(ROOT)

    def test_frozen_scope_and_denominators_are_preserved(self) -> None:
        summary = self.result["summary"]
        self.assertEqual(summary["global_denominator"], 7565)
        self.assertEqual(summary["openjarvis_obligations"], 646)
        self.assertEqual(summary["w02_proof_units"], 47)
        self.assertEqual(summary["owned"], 37)
        self.assertEqual(summary["shared"], 10)
        self.assertEqual(summary["parity_promotions"], 0)
        self.assertEqual(summary["verified_capabilities"], 0)
        self.assertEqual(len(self.result["rows"]), 47)

    def test_current_matrix_has_one_candidate_and_no_parity_promotion(self) -> None:
        rows = self.result["rows"]
        self.assertTrue(all(row["canonical_parity_status"] == "UNVERIFIED" for row in rows))
        self.assertTrue(all(row["verified"] is False for row in rows))
        self.assertTrue(all(row["parity_promotion"] is False for row in rows))
        self.assertEqual(sum(row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE" for row in rows), 1)
        self.assertEqual(sum(row["w02_evidence_state"] == "UNBOUND" for row in rows), 46)
        self.assertEqual(sum(row["ownership"] == "OWNED" for row in rows), 37)
        self.assertEqual(sum(row["ownership"] == "SHARED" for row in rows), 10)
        candidate = next(row for row in rows if row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE")
        self.assertEqual(candidate["capability_id"], "cap_49014a3c03b104c8ec2f4ca1")
        self.assertEqual(candidate["binding"]["evidence_id"], "EVID-W02-UNARY-INFERENCE-20260921")
        self.assertFalse(candidate["binding"]["terminal"])

    def test_graph_projects_all_four_planes_without_promotion(self) -> None:
        value = self.result["graph"]
        candidate_count = self.result["summary"]["binding_counts"]["EVIDENCE_BACKED_CANDIDATE"]
        self.assertEqual(
            value["authority_order"],
            ["P0_SOURCE_EVIDENCE", "P1_SEMANTIC_SURFACE", "P2_COS20D_DECISION", "P3_AGENT_CONTEXT"],
        )
        self.assertEqual(value["parity_promotions"], 0)
        self.assertEqual(value["verified_capabilities"], 0)
        self.assertEqual(len(value["nodes"]), 47 * 4 + candidate_count)
        self.assertEqual(len(value["edges"]), 47 * 3 + candidate_count)
        evidence_nodes = [node for node in value["nodes"] if node["id"].startswith("EVIDENCE:")]
        support_edges = [edge for edge in value["edges"] if edge["type"] == "supports_candidate"]
        self.assertEqual(len(evidence_nodes), candidate_count)
        self.assertEqual(len(support_edges), candidate_count)

    def test_seed_binding_preserves_real_fallback_not_run_lane(self) -> None:
        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        fallback = evidence["EVID-W02-FALLBACK-ADAPTER-20260922"]
        self.assertEqual(fallback["real_openjarvis_fallback_model_execution"], "NOT_RUN")
        candidate = next(row for row in self.result["rows"] if row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE")
        self.assertNotEqual(candidate["binding"]["evidence_id"], "EVID-W02-FALLBACK-ADAPTER-20260922")

    def test_forged_evidence_id_is_rejected(self) -> None:
        cid = self.result["rows"][0]["capability_id"]
        binding = {
            "capability_id": cid,
            "evidence_id": "EVID-FORGED",
            "test_id": "E01",
            "validated_head": "a" * 40,
            "expected_fields": {"result": "PASS"},
        }
        with self.assertRaisesRegex(graph.ParityGraphError, "unknown/forged evidence_id"):
            graph.validate_binding(
                binding,
                proof_unit_ids={cid},
                shared_ids=set(),
                evidence_catalog={},
                task_proofs={},
            )

    def test_foreign_sha_is_rejected(self) -> None:
        cid = self.result["rows"][0]["capability_id"]
        evidence_id = "EVID-SYNTHETIC"
        binding = {
            "capability_id": cid,
            "evidence_id": evidence_id,
            "test_id": "E01",
            "validated_head": "b" * 40,
            "expected_fields": {"result": "PASS"},
        }
        evidence = {evidence_id: {"evidence_id": evidence_id, "result": "PASS", "validated_head": "a" * 40}}
        proofs = {evidence_id: {"evidence_id": evidence_id, "result": "PASS", "validated_head": "a" * 40}}
        with self.assertRaisesRegex(graph.ParityGraphError, "foreign/stale evidence SHA"):
            graph.validate_binding(
                binding,
                proof_unit_ids={cid},
                shared_ids=set(),
                evidence_catalog=evidence,
                task_proofs=proofs,
            )

    def test_not_run_blocked_platform_gated_and_waiver_never_satisfy_binding(self) -> None:
        cid = self.result["rows"][0]["capability_id"]
        for state in ("NOT_RUN", "BLOCKED", "PLATFORM_GATED", "SKIPPED", "WAIVED", "UNKNOWN"):
            with self.subTest(state=state):
                evidence_id = f"EVID-{state}"
                binding = {
                    "capability_id": cid,
                    "evidence_id": evidence_id,
                    "test_id": "E02",
                    "validated_head": "a" * 40,
                    "expected_fields": {"lane": "PASS"},
                }
                evidence = {
                    evidence_id: {
                        "evidence_id": evidence_id,
                        "result": "PASS",
                        "validated_head": "a" * 40,
                        "lane": state,
                    }
                }
                proofs = {evidence_id: {"evidence_id": evidence_id, "result": "PASS", "validated_head": "a" * 40}}
                with self.assertRaises(graph.ParityGraphError):
                    graph.validate_binding(
                        binding,
                        proof_unit_ids={cid},
                        shared_ids=set(),
                        evidence_catalog=evidence,
                        task_proofs=proofs,
                    )

    def test_shared_capability_cannot_be_terminal(self) -> None:
        shared = next(row for row in self.result["rows"] if row["ownership"] == "SHARED")
        cid = shared["capability_id"]
        evidence_id = "EVID-SHARED"
        binding = {
            "capability_id": cid,
            "evidence_id": evidence_id,
            "test_id": "E02",
            "validated_head": "a" * 40,
            "expected_fields": {"lane": "PASS"},
            "terminal": True,
        }
        evidence = {
            evidence_id: {
                "evidence_id": evidence_id,
                "result": "PASS",
                "validated_head": "a" * 40,
                "lane": "PASS",
            }
        }
        proofs = {evidence_id: {"evidence_id": evidence_id, "result": "PASS", "validated_head": "a" * 40}}
        with self.assertRaisesRegex(graph.ParityGraphError, "shared W02 capability cannot be terminal"):
            graph.validate_binding(
                binding,
                proof_unit_ids={cid},
                shared_ids={cid},
                evidence_catalog=evidence,
                task_proofs=proofs,
            )

    def test_positive_binding_is_only_a_candidate_not_a_promotion(self) -> None:
        owned = next(row for row in self.result["rows"] if row["ownership"] == "OWNED")
        cid = owned["capability_id"]
        evidence_id = "EVID-POSITIVE"
        binding = {
            "capability_id": cid,
            "evidence_id": evidence_id,
            "test_id": "G6-SYNTHETIC",
            "validated_head": "a" * 40,
            "expected_fields": {"lane": "PASS"},
            "terminal": True,
        }
        evidence = {
            evidence_id: {
                "evidence_id": evidence_id,
                "result": "PASS",
                "validated_head": "a" * 40,
                "lane": "PASS",
            }
        }
        proofs = {evidence_id: {"evidence_id": evidence_id, "result": "PASS", "validated_head": "a" * 40}}
        validated = graph.validate_binding(
            binding,
            proof_unit_ids={cid},
            shared_ids=set(),
            evidence_catalog=evidence,
            task_proofs=proofs,
        )
        self.assertEqual(validated["binding_state"], "EVIDENCE_BACKED_CANDIDATE")
        self.assertIs(validated["parity_promotion"], False)

    def test_compiler_does_not_mutate_capability_ledger(self) -> None:
        path = ROOT / graph.CAPABILITY_LEDGER_PATH
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        graph.compile_root(ROOT)
        after = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_products_are_deterministic(self) -> None:
        first = graph.products(graph.compile_root(ROOT))
        second = graph.products(graph.compile_root(ROOT))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
