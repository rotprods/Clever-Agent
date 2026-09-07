from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

from scripts.cp03 import w02_facets, w02_scope

ROOT = Path(__file__).resolve().parents[1]

class W02FacetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scope = w02_scope.compile_root(ROOT)
        cls.policy = json.loads((ROOT / w02_facets.POLICY).read_text(encoding="utf-8"))
        cls.engine = json.loads((ROOT / w02_facets.SCOPE_ENGINE).read_text(encoding="utf-8"))
        cls.result = w02_facets.compile_from(cls.scope, cls.policy, cls.engine)

    def compile_policy(self, mutate=None):
        policy=copy.deepcopy(self.policy)
        if mutate:
            mutate(policy)
        return w02_facets.compile_from(self.scope, policy, self.engine)

    def test_review_is_complete_but_not_self_frozen(self):
        s=self.result["summary"]
        self.assertEqual(s["cross_wave_review_resolved"],52)
        self.assertTrue(s["freeze_ready"])
        self.assertFalse(s["scope_frozen"])
        self.assertFalse(s["independent_review_observed"])
        self.assertEqual(s["parity_promotions"],0)

    def test_k_is_split_between_owned_and_shared(self):
        s=self.result["summary"]
        self.assertEqual(s["K_w02_proof_units"],47)
        self.assertEqual(s["K_w02_owned_capabilities"],37)
        self.assertEqual(s["K_w02_shared_capabilities"],10)
        self.assertEqual(set(self.result["owned_ids"]) & set(self.result["shared_ids"]),set())
        self.assertEqual(set(self.result["owned_ids"]) | set(self.result["shared_ids"]),set(self.result["w02_ids"]))

    def test_denominators_are_immutable(self):
        s=self.result["summary"]
        self.assertEqual(s["global_denominator"],7565)
        self.assertEqual(s["openjarvis_obligations"],646)
        self.assertEqual(s["verified"],0)
        self.assertEqual(s["parity_promotions"],0)

    def test_all_original_shared_records_are_reviewed_once(self):
        original={r["capability_id"] for r in self.scope["allocations"] if r["disposition"]=="CROSS_WAVE_REVIEW"}
        reviewed={r["capability_id"] for r in self.result["facet_rows"] if r["source_disposition"]=="CROSS_WAVE_REVIEW"}
        self.assertEqual(reviewed,original)
        self.assertEqual(len(reviewed),52)

    def test_hidden_websocket_inference_dependency_is_recovered(self):
        cid="cap_4d6bc214e2e94a84923b87c0"
        row=next(r for r in self.result["facet_rows"] if r["capability_id"]==cid)
        self.assertEqual(row["source_disposition"],"OTHER_CP03_WAVE")
        self.assertEqual(row["source_path"],"src/openjarvis/server/api_routes.py")
        self.assertEqual(row["source_line"],683)
        self.assertIn("W02",row["facets"])
        self.assertFalse(row["full_capability_verified_in_w02_allowed"])

    def test_shared_capability_cannot_be_fully_verified_in_w02(self):
        shared=[r for r in self.result["facet_rows"] if r["w02_terminal_ownership"]=="SHARED"]
        self.assertTrue(shared)
        self.assertTrue(all(not r["full_capability_verified_in_w02_allowed"] for r in shared))

    def test_w02_owned_review_records_may_reach_terminal_after_their_own_tests(self):
        owned=[r for r in self.result["facet_rows"] if r["w02_terminal_ownership"]=="OWNED"]
        self.assertEqual(len(owned),5)
        self.assertTrue(all(r["facets"]==["W02"] for r in owned))
        self.assertTrue(all(r["full_capability_verified_in_w02_allowed"] for r in owned))

    def test_route_mount_review_covers_exact_lines(self):
        routes=self.policy["route_mounts"]
        self.assertEqual(len(routes),29)
        byid={r["capability_id"]:r for r in self.scope["allocations"]}
        for cid,spec in routes.items():
            self.assertEqual(byid[cid]["surface_kind"],"route_mount")
            self.assertEqual(byid[cid]["source_line"],spec["line"])

    def test_chat_completion_is_multifacet(self):
        row=next(r for r in self.result["facet_rows"] if r["capability_id"]=="cap_56358709cbc328e25ed1afff")
        self.assertEqual(row["facets"],["W02","W03","W04","W05"])
        self.assertEqual(row["w02_terminal_ownership"],"SHARED")

    def test_engine_method_matrix_is_exact(self):
        matrix={r["method"]:r for r in self.result["method_matrix"]}
        self.assertEqual(set(matrix),{"generate","stream","stream_full","list_models","health","can_serve","close","prepare"})
        self.assertEqual(matrix["can_serve"]["semantic_kind"],"default_true")
        self.assertEqual(matrix["prepare"]["semantic_kind"],"default_noop")
        self.assertEqual(matrix["close"]["semantic_kind"],"default_noop")
        self.assertEqual(matrix["stream_full"]["semantic_kind"],"default_wrapper")
        for method in ("generate","stream","stream_full"):
            self.assertIn("L2_REAL_MODEL",matrix[method]["required_lanes"])

    def test_engine_method_tests_are_distinct(self):
        ids=[r["canonical_test_id"] for r in self.result["method_matrix"]]
        self.assertEqual(len(ids),len(set(ids)))

    def test_engine_contract_does_not_mutate_denominator_for_missing_method_surfaces(self):
        self.assertTrue(all(not r["denominator_mutation_required"] for r in self.result["method_matrix"]))
        self.assertTrue(all(not r["parity_promotion_before_test"] for r in self.result["method_matrix"]))

    def test_unknown_facet_wave_is_rejected(self):
        def mutate(p): p["explicit"]["cap_575541e84f43f012a9239ad2"]["facets"]=["W99"]
        with self.assertRaises(w02_facets.FacetError):
            self.compile_policy(mutate)

    def test_missing_shared_mapping_is_rejected(self):
        def mutate(p): del p["explicit"]["cap_575541e84f43f012a9239ad2"]
        with self.assertRaises(w02_facets.FacetError):
            self.compile_policy(mutate)

    def test_wrong_route_line_is_rejected(self):
        def mutate(p): p["route_mounts"]["cap_21e74bd335b9db6e37998c79"]["line"]=999
        with self.assertRaises(w02_facets.FacetError):
            self.compile_policy(mutate)

    def test_parity_promotion_is_rejected(self):
        def mutate(p): p["parity_promotions"]=1
        with self.assertRaises(w02_facets.FacetError):
            self.compile_policy(mutate)

    def test_denominator_drift_is_rejected(self):
        def mutate(p): p["global_denominator"]=7564
        with self.assertRaises(w02_facets.FacetError):
            self.compile_policy(mutate)

    def test_engine_blob_drift_is_rejected(self):
        def mutate(p): p["engine_contract"]["source_blob_sha"]="0"*40
        with self.assertRaises(w02_facets.FacetError):
            self.compile_policy(mutate)

    def test_duplicate_engine_test_id_is_rejected(self):
        def mutate(p):
            p["engine_contract"]["methods"]["stream"]["test_id"]=p["engine_contract"]["methods"]["generate"]["test_id"]
        with self.assertRaises(w02_facets.FacetError):
            self.compile_policy(mutate)

    def test_additional_dependency_must_match_original_allocation(self):
        def mutate(p): p["additional_w02_dependencies"]["cap_4d6bc214e2e94a84923b87c0"]["expected_original_disposition"]="W02_CORE"
        with self.assertRaises(w02_facets.FacetError):
            self.compile_policy(mutate)

    def test_products_are_deterministic(self):
        a=w02_facets.products(self.result)
        b=w02_facets.products(w02_facets.compile_from(self.scope,copy.deepcopy(self.policy),copy.deepcopy(self.engine)))
        self.assertEqual(a,b)

if __name__=="__main__":
    unittest.main()
