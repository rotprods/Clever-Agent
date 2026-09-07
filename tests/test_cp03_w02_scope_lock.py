from __future__ import annotations
import copy, unittest
from pathlib import Path
from scripts.cp03 import w02_facets, w02_scope_lock

ROOT = Path(__file__).resolve().parents[1]

class ScopeLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lock = w02_scope_lock.load_lock(ROOT)
        cls.facets = w02_facets.compile_facets(ROOT)
        cls.receipt = w02_scope_lock.validate_lock(cls.lock, cls.facets)
    def mutate(self, fn):
        lock = copy.deepcopy(self.lock); fn(lock); return lock
    def test_repository_lock_is_valid(self):
        self.assertEqual(self.receipt["status"], "PASS"); self.assertTrue(self.receipt["scope_frozen"])
    def test_exact_scope_counts(self):
        self.assertEqual((self.receipt["w02_proof_units"], self.receipt["w02_owned_capabilities"], self.receipt["w02_shared_capabilities"]), (47,37,10))
    def test_denominator_and_parity_unchanged(self):
        self.assertEqual((self.receipt["global_denominator"], self.receipt["openjarvis_obligations"], self.receipt["verified"], self.receipt["parity_promotions"]), (7565,646,0,0))
    def test_shared_terminal_is_forbidden(self): self.assertTrue(self.receipt["shared_terminal_forbidden"])
    def test_review_does_not_claim_human_review(self):
        self.assertFalse(self.receipt["human_review"]); self.assertEqual(self.receipt["review_type"], "DETERMINISTIC_CLEAN_ROOM_VALIDATION")
    def test_proof_id_tamper_rejected(self):
        lock=self.mutate(lambda x: x["proof_unit_ids"].pop())
        with self.assertRaises(w02_scope_lock.ScopeLockError): w02_scope_lock.validate_lock(lock,self.facets)
    def test_owned_shared_overlap_rejected(self):
        def fn(x): x["owned_ids"][0]=x["shared_ids"][0]
        with self.assertRaises(w02_scope_lock.ScopeLockError): w02_scope_lock.validate_lock(self.mutate(fn),self.facets)
    def test_hash_tamper_rejected(self):
        def fn(x): x["artifact_product_hashes"]["W02_PROOF_UNITS.json"]="0"*64
        with self.assertRaises(w02_scope_lock.ScopeLockError): w02_scope_lock.validate_lock(self.mutate(fn),self.facets)
    def test_pin_drift_rejected(self):
        with self.assertRaises(w02_scope_lock.ScopeLockError): w02_scope_lock.validate_lock(self.mutate(lambda x:x.__setitem__("source_commit","bad")),self.facets)
    def test_denominator_drift_rejected(self):
        with self.assertRaises(w02_scope_lock.ScopeLockError): w02_scope_lock.validate_lock(self.mutate(lambda x:x.__setitem__("global_denominator",7564)),self.facets)
    def test_parity_promotion_rejected(self):
        with self.assertRaises(w02_scope_lock.ScopeLockError): w02_scope_lock.validate_lock(self.mutate(lambda x:x["semantics"].__setitem__("parity_promotions",1)),self.facets)
    def test_shared_terminal_override_rejected(self):
        with self.assertRaises(w02_scope_lock.ScopeLockError): w02_scope_lock.validate_lock(self.mutate(lambda x:x["semantics"].__setitem__("shared_terminal_forbidden",False)),self.facets)
    def test_fake_human_review_rejected(self):
        with self.assertRaises(w02_scope_lock.ScopeLockError): w02_scope_lock.validate_lock(self.mutate(lambda x:x["review"].__setitem__("human_review",True)),self.facets)
    def test_wrong_facet_evidence_rejected(self):
        with self.assertRaises(w02_scope_lock.ScopeLockError): w02_scope_lock.validate_lock(self.mutate(lambda x:x["review"].__setitem__("source_facet_run_id",0)),self.facets)
    def test_engine_method_mapping_has_eight_unique_tests(self):
        methods=self.facets["method_matrix"]; self.assertEqual(len(methods),8); self.assertEqual(len({m["canonical_test_id"] for m in methods}),8)

if __name__ == "__main__": unittest.main()
