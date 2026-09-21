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
        self.task("W02-07")["status"] = "BLOCKED"
        self.task("W02-08")["status"] = "BLOCKED"
        self.task("W02-07")["depends_on"] = ["W02-08"]
        self.task("W02-08")["depends_on"] = ["W02-07"]
        self.invalid("cycle")

    def test_self_dependency_rejected(self):
        self.task("W02-07")["depends_on"] = ["W02-07"]
        self.invalid("self dependency")

    def test_false_ready_rejected(self):
        self.task("W02-07")["status"] = "BLOCKED"
        self.task("W02-08")["status"] = "READY"
        self.invalid("false-ready")

    def test_inference_contracts_require_teardown_and_atomic_registry(self):
        self.assertTrue(
            {"W02-04", "W02-05"}.issubset(self.task("W02-06")["depends_on"])
        )

    def test_g2_egress_frontier_transition_is_consistent(self):
        self.assertEqual(self.task("W02-06")["status"], "COMPLETE")
        self.assertTrue(self.task("W02-06")["proof"])
        egress = self.task("W02-07")
        bridge = self.task("W02-08")
        if egress["status"] == "READY":
            self.assertFalse(egress["proof"])
            self.assertEqual(bridge["status"], "BLOCKED")
            self.assertEqual(self.plan["first_executable_task"], "W02-07")
        else:
            self.assertEqual(egress["status"], "COMPLETE")
            self.assertTrue(egress["proof"])
            self.assertEqual(bridge["status"], "READY")
            self.assertEqual(self.plan["first_executable_task"], "W02-08")
        self.assertEqual(self.check()["first_executable_task"], self.plan["first_executable_task"])

    def test_completion_without_evidence_rejected(self):
        self.task("W02-07")["status"] = "COMPLETE"
        self.task("W02-07")["proof"] = []
        self.invalid("without proof")

    def test_missing_acceptance_rejected(self):
        self.task("W02-07")["acceptance_tests"] = []
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

    def test_current_frontier_and_prior_gates_are_evidenced(self):
        for task_id in ("W02-03", "W02-04", "W02-05", "W02-06"):
            task = self.task(task_id)
            self.assertEqual(task["status"], "COMPLETE", task_id)
            self.assertTrue(task["proof"], task_id)
        egress = self.task("W02-07")
        bridge = self.task("W02-08")
        expected = "W02-07" if egress["status"] == "READY" else "W02-08"
        self.assertEqual(self.plan["first_executable_task"], expected)
        self.assertEqual(self.check()["first_executable_task"], expected)
        if expected == "W02-08":
            self.assertEqual(egress["status"], "COMPLETE")
            self.assertTrue(egress["proof"])
            self.assertEqual(bridge["status"], "READY")
        else:
            self.assertEqual(bridge["status"], "BLOCKED")

    def test_only_one_g2_frontier_is_ready(self):
        ready = [task["id"] for task in self.plan["tasks"] if task.get("status") == "READY"]
        self.assertIn(self.plan["first_executable_task"], ready)
        if self.plan["first_executable_task"] in {"W02-07", "W02-08"}:
            self.assertEqual([item for item in ready if item in {"W02-07", "W02-08"}], [self.plan["first_executable_task"]])

    def test_deterministic_validation(self):
        self.assertEqual(self.check(), self.check())


if __name__ == "__main__":
    unittest.main()
