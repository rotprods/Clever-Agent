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
        # Block both G1 tasks before introducing a cycle so the validator reaches cycle
        # detection rather than failing earlier on READY dependency semantics.
        self.task("W02-04")["status"] = "BLOCKED"
        self.task("W02-05")["status"] = "BLOCKED"
        self.task("W02-04")["depends_on"] = ["W02-05"]
        self.task("W02-05")["depends_on"] = ["W02-04"]
        self.invalid("cycle")

    def test_self_dependency_rejected(self):
        self.task("W02-04")["depends_on"] = ["W02-04"]
        self.invalid("self dependency")

    def test_false_ready_rejected(self):
        original = copy.deepcopy(self.plan)
        for dependency in ("W02-04", "W02-05"):
            with self.subTest(incomplete_dependency=dependency):
                self.plan = copy.deepcopy(original)
                self.task(dependency)["status"] = "BLOCKED"
                self.task("W02-06")["status"] = "READY"
                self.invalid("false-ready")

    def test_inference_contracts_require_teardown_and_atomic_registry(self):
        self.assertTrue(
            {"W02-04", "W02-05"}.issubset(self.task("W02-06")["depends_on"])
        )

    def test_inference_can_be_ready_after_both_g1_dependencies_complete(self):
        # Synthetic in-memory evidence exercises the transition, never persisted truth.
        for task_id in ("W02-04", "W02-05"):
            self.task(task_id)["status"] = "COMPLETE"
            self.task(task_id)["proof"] = [{"fixture": "planning-test-only"}]
        self.task("W02-06")["status"] = "READY"
        self.plan["first_executable_task"] = "W02-06"
        self.assertEqual(self.check()["first_executable_task"], "W02-06")

    def test_completion_without_evidence_rejected(self):
        # W02-04 is the current first executable task and has no proof yet.
        self.task("W02-04")["status"] = "COMPLETE"
        self.invalid("without proof")

    def test_missing_acceptance_rejected(self):
        self.task("W02-04")["acceptance_tests"] = []
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

    def test_current_frontier_is_executable_and_g1_completion_is_evidenced(self):
        frontier = self.task(self.plan["first_executable_task"])
        self.assertIn(frontier["status"], {"READY", "IN_PROGRESS"})
        for task_id in ("W02-03", "W02-04", "W02-05"):
            task = self.task(task_id)
            if task["status"] == "COMPLETE":
                self.assertTrue(task["proof"], task_id)
        if self.task("W02-04")["status"] != "COMPLETE":
            self.assertEqual(self.task("W02-06")["status"], "BLOCKED")

    def test_deterministic_validation(self):
        self.assertEqual(self.check(), self.check())


if __name__ == "__main__":
    unittest.main()
