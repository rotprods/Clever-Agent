"""Planning integrity tests. These do not certify inference or upstream parity."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("w02_plan_validator", ROOT / "scripts/cp03/validate_w02_plan.py")
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class W02PlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan, self.findings, self.cos = copy.deepcopy(MOD.load(ROOT))

    def check(self):
        return MOD.validate(self.plan, self.findings, self.cos)

    def invalid(self, message: str) -> None:
        with self.assertRaisesRegex(ValueError, message):
            self.check()

    def task(self, task_id: str):
        return next(row for row in self.plan["tasks"] if row["id"] == task_id)

    def test_valid_plan(self):
        self.assertEqual(self.check()["task_count"], 20)

    def test_validator_does_not_claim_runtime_proof(self):
        self.assertEqual(self.check()["runtime_tests_executed_by_this_validator"], 0)
        self.assertEqual(self.check()["parity_promotions"], 0)

    def test_global_denominator_locked(self):
        self.plan["global_denominator"] = 1
        self.invalid("canonical field")

    def test_upstream_pin_locked(self):
        self.plan["upstream_commit"] = "main"
        self.invalid("canonical field")

    def test_parent_scope_locked(self):
        self.plan["parent_task"] = "CP03-003"
        self.invalid("canonical field")

    def test_w02_count_is_present_after_scope_lock_and_bounds_remain_enforced(self):
        self.assertEqual(self.plan["w02_obligation_count"], 47)
        self.plan["w02_obligation_count"] = 647
        self.invalid("obligation count")

    def test_duplicate_task_rejected(self):
        self.plan["tasks"].append(copy.deepcopy(self.plan["tasks"][0]))
        self.invalid("duplicate task")

    def test_missing_dependency_rejected(self):
        self.task("W02-01")["depends_on"] = ["W02-99"]
        self.invalid("missing dependency")

    def test_cycle_rejected(self):
        # Keep the current frontier out of READY while constructing the cycle so
        # the validator reaches its cycle detector instead of failing earlier on
        # false-ready dependency semantics.
        self.task("W02-03")["status"] = "BLOCKED"
        self.task("W02-03")["depends_on"] = ["W02-04"]
        self.invalid("cycle")

    def test_self_dependency_rejected(self):
        self.task("W02-03")["depends_on"] = ["W02-03"]
        self.invalid("self dependency")

    def test_false_ready_rejected(self):
        # W02-04 depends on current READY task W02-03, so it cannot itself be READY.
        self.task("W02-04")["status"] = "READY"
        self.invalid("false-ready")

    def test_completion_without_evidence_rejected(self):
        # W02-03 is the current READY task and has no proof yet.
        self.task("W02-03")["status"] = "COMPLETE"
        self.invalid("without proof")

    def test_missing_acceptance_rejected(self):
        self.task("W02-03")["acceptance_tests"] = []
        self.invalid("acceptance_tests")

    def test_path_traversal_rejected(self):
        self.task("W02-00")["evidence_path"] = "evidence/cp03/cp03-w02/../../secret"
        self.invalid("unsafe evidence")

    def test_unmapped_finding_rejected(self):
        self.findings["findings"][0]["resolved_by"] = ["W02-99"]
        self.invalid("unmapped finding")

    def test_findings_source_drift_rejected(self):
        self.findings["source_sha"] = "0" * 40
        self.invalid("source drift")

    def test_dimension_drift_rejected(self):
        self.cos["dimensions"].pop()
        self.invalid("COS20D drift")

    def test_unmapped_dimension_rejected(self):
        self.cos["dimensions"][0]["tasks"] = []
        self.invalid("unmapped COS")

    def test_invalid_first_task_rejected(self):
        self.plan["first_executable_task"] = "W02-19"
        self.invalid("first executable")

    def test_current_frontier_is_w02_03(self):
        self.assertEqual(self.plan["first_executable_task"], "W02-03")
        self.assertEqual(self.task("W02-02")["status"], "COMPLETE")
        self.assertTrue(self.task("W02-02")["proof"])
        self.assertEqual(self.task("W02-03")["status"], "READY")
        self.assertEqual(self.task("W02-03")["proof"], [])

    def test_deterministic_validation(self):
        self.assertEqual(self.check(), self.check())


if __name__ == "__main__":
    unittest.main()
