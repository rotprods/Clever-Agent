from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from scripts.cp03 import w02_parity_graph as graph

ROOT = Path(__file__).resolve().parents[1]
SEED_CAPABILITY_ID = "cap_49014a3c03b104c8ec2f4ca1"
OLLAMA_CAPABILITY_ID = "cap_a5ae164f941b35e6fafd357c"
LITELLM_CAPABILITY_ID = "cap_149d7cf3bf745e7bea3fa1b0"
CLOUD_CAPABILITY_ID = "cap_49e508ee1377a8861a33b2f0"
OLLAMA_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_ollama_registry_binding_is_capability_specific_and_evidence_backed"
)
LITELLM_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_litellm_registry_binding_is_capability_specific_and_evidence_backed"
)
CLOUD_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cloud_registry_binding_is_capability_specific_and_evidence_backed"
)


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

    def test_current_matrix_has_four_candidates_and_no_parity_promotion(self) -> None:
        rows = self.result["rows"]
        self.assertTrue(all(row["canonical_parity_status"] == "UNVERIFIED" for row in rows))
        self.assertTrue(all(row["verified"] is False for row in rows))
        self.assertTrue(all(row["parity_promotion"] is False for row in rows))
        self.assertEqual(sum(row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE" for row in rows), 4)
        self.assertEqual(sum(row["w02_evidence_state"] == "UNBOUND" for row in rows), 43)
        self.assertEqual(sum(row["ownership"] == "OWNED" for row in rows), 37)
        self.assertEqual(sum(row["ownership"] == "SHARED" for row in rows), 10)
        candidates = {
            row["capability_id"]: row
            for row in rows
            if row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE"
        }
        self.assertEqual(
            set(candidates),
            {SEED_CAPABILITY_ID, OLLAMA_CAPABILITY_ID, LITELLM_CAPABILITY_ID, CLOUD_CAPABILITY_ID},
        )
        seed = candidates[SEED_CAPABILITY_ID]
        self.assertEqual(seed["binding"]["evidence_id"], "EVID-W02-UNARY-INFERENCE-20260921")
        self.assertFalse(seed["binding"]["terminal"])
        ollama = candidates[OLLAMA_CAPABILITY_ID]
        self.assertEqual(ollama["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(ollama["binding"]["terminal"])
        litellm = candidates[LITELLM_CAPABILITY_ID]
        self.assertEqual(litellm["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(litellm["binding"]["terminal"])
        cloud = candidates[CLOUD_CAPABILITY_ID]
        self.assertEqual(cloud["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cloud["binding"]["terminal"])

    def test_ollama_registry_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == OLLAMA_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/ollama.py")
        self.assertEqual(row["source_line"], 106)
        self.assertEqual(row["name"], "ollama")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], OLLAMA_TEST_ID)
        self.assertFalse(binding["terminal"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog = json.loads(
            (ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8")
        )
        matches = [engine for engine in catalog["engines"] if engine["key"] == "ollama"]
        self.assertEqual(
            matches,
            [
                {
                    "implementation": "openjarvis.engine.ollama.OllamaEngine",
                    "key": "ollama",
                    "native_type": "ABCMeta",
                    "state": "REGISTERED",
                }
            ],
        )
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_litellm_registry_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == LITELLM_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/litellm.py")
        self.assertEqual(row["source_line"], 16)
        self.assertEqual(row["name"], "litellm")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], LITELLM_TEST_ID)
        self.assertFalse(binding["terminal"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog = json.loads(
            (ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8")
        )
        matches = [engine for engine in catalog["engines"] if engine["key"] == "litellm"]
        self.assertEqual(
            matches,
            [
                {
                    "implementation": "openjarvis.engine.litellm.LiteLLMEngine",
                    "key": "litellm",
                    "native_type": "ABCMeta",
                    "state": "REGISTERED",
                }
            ],
        )
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_cloud_registry_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLOUD_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/cloud.py")
        self.assertEqual(row["source_line"], 323)
        self.assertEqual(row["name"], "cloud")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLOUD_TEST_ID)
        self.assertFalse(binding["terminal"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog = json.loads(
            (ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8")
        )
        matches = [engine for engine in catalog["engines"] if engine["key"] == "cloud"]
        self.assertEqual(
            matches,
            [
                {
                    "implementation": "openjarvis.engine.cloud.CloudEngine",
                    "key": "cloud",
                    "native_type": "ABCMeta",
                    "state": "REGISTERED",
                }
            ],
        )
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

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
        candidate = next(row for row in self.result["rows"] if row["capability_id"] == SEED_CAPABILITY_ID)
        self.assertEqual(candidate["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")
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
