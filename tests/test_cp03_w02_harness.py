from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from scripts.cp03 import w02_harness


class W02HarnessTests(unittest.TestCase):
    def test_required_sets_are_unique_and_nonempty(self) -> None:
        self.assertEqual(len(set(w02_harness.ALL_REQUIRED)), len(w02_harness.ALL_REQUIRED))
        self.assertGreater(len(w02_harness.FAKE_REQUIRED), 0)
        self.assertEqual(len(w02_harness.NATIVE_REQUIRED), 1)

    def test_source_audit_rejects_silent_return(self) -> None:
        source = "\n".join(
            f"#[test]\nfn {name}() {{ {'return;' if name == w02_harness.ALL_REQUIRED[0] else 'assert!(true);'} }}"
            for name in w02_harness.ALL_REQUIRED
        ) + "\n// MANDATORY prerequisite\n"
        with self.assertRaises(w02_harness.HarnessError):
            w02_harness.audit_source(source)

    def test_source_audit_rejects_missing_test(self) -> None:
        source = "\n".join(
            f"#[test]\nfn {name}() {{ assert!(true); }}" for name in w02_harness.ALL_REQUIRED[:-1]
        ) + "\n// MANDATORY prerequisite\n"
        with self.assertRaises(w02_harness.HarnessError):
            w02_harness.audit_source(source)

    def test_source_audit_accepts_fail_closed_source(self) -> None:
        source = "\n".join(
            f"#[test]\nfn {name}() {{ assert!(true); }}" for name in w02_harness.ALL_REQUIRED
        ) + "\n// MANDATORY prerequisite\n"
        result = w02_harness.audit_source(source)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["silent_returns"], 0)

    def test_case_output_rejects_zero_tests(self) -> None:
        output = "test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 7 filtered out"
        with self.assertRaises(w02_harness.HarnessError):
            w02_harness.validate_case_output("case", 0, output)

    def test_case_output_rejects_ignored_test(self) -> None:
        output = "test case ... ignored\ntest result: ok. 0 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out"
        with self.assertRaises(w02_harness.HarnessError):
            w02_harness.validate_case_output("case", 0, output)

    def test_case_output_rejects_nonzero_exit(self) -> None:
        with self.assertRaises(w02_harness.HarnessError):
            w02_harness.validate_case_output("case", 101, "test result: FAILED")

    def test_case_output_rejects_timeout(self) -> None:
        with self.assertRaises(w02_harness.HarnessError):
            w02_harness.validate_case_output("case", 124, "", timed_out=True)

    def test_case_output_accepts_exact_one_test(self) -> None:
        output = "running 1 test\ntest case ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 6 filtered out"
        result = w02_harness.validate_case_output("case", 0, output)
        self.assertEqual(result["status"], "PASS")

    def test_preflight_missing_python_fails(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(w02_harness.HarnessError):
                w02_harness.preflight("fake")

    def test_preflight_relative_python_fails(self) -> None:
        with patch.dict(os.environ, {"CLEVER_TEST_PYTHON": "python3"}, clear=True):
            with self.assertRaises(w02_harness.HarnessError):
                w02_harness.preflight("fake")

    def test_preflight_fake_accepts_absolute_executable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            executable = Path(td) / "python"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            with patch.dict(os.environ, {"CLEVER_TEST_PYTHON": str(executable)}, clear=True):
                result = w02_harness.preflight("fake")
        self.assertEqual(result["CLEVER_TEST_PYTHON"], str(executable))

    def test_preflight_native_requires_docker_workspace_and_image(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            python = Path(td) / "python"
            python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            python.chmod(python.stat().st_mode | stat.S_IXUSR)
            with patch.dict(os.environ, {"CLEVER_TEST_PYTHON": str(python)}, clear=True):
                with self.assertRaises(w02_harness.HarnessError):
                    w02_harness.preflight("native")

    def test_repository_source_has_no_silent_required_return(self) -> None:
        report = w02_harness.audit_path(w02_harness.TEST_SOURCE)
        self.assertEqual(report["required_tests"], len(w02_harness.ALL_REQUIRED))

    def test_persisted_transition_is_unique_and_opens_only_w02_03(self) -> None:
        root = Path(__file__).resolve().parents[1]
        plan = json.loads(
            (root / "iterations/03/waves/CP03-W02/TASK_GRAPH.json").read_text(encoding="utf-8")
        )
        tasks = {row["id"]: row for row in plan["tasks"]}
        self.assertEqual(tasks["W02-02"]["status"], "COMPLETE")
        self.assertEqual(tasks["W02-03"]["status"], "READY")
        self.assertEqual(plan["first_executable_task"], "W02-03")
        proofs = [
            row for row in tasks["W02-02"].get("proof", [])
            if row.get("evidence_id") == "EVID-W02-HARNESS-20260909"
        ]
        self.assertEqual(len(proofs), 1)
        self.assertEqual(proofs[0]["fake_executed"], 6)
        self.assertEqual(proofs[0]["native_executed"], 1)
        self.assertEqual(proofs[0]["retest_executed"], 6)

        evidence = [
            json.loads(line)
            for line in (root / "ledgers/EVIDENCE_LEDGER.ndjson").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        matching = [row for row in evidence if row.get("evidence_id") == "EVID-W02-HARNESS-20260909"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["status"], "VERIFIED")
        self.assertEqual(matching[0]["parity_promotions"], 0)

        claims = [
            json.loads(line)
            for line in (root / "ledgers/CLAIM_LEDGER.ndjson").read_text(encoding="utf-8").splitlines()
            if line.strip() and json.loads(line).get("claim_id") == "CLAIM-CP03-W02-HARNESS-001"
        ]
        self.assertEqual(claims[-1]["status"], "RELEASED")
        handoff = (root / "HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("W02-03", handoff)
        goal = json.loads((root / "GOAL_STATE.json").read_text(encoding="utf-8"))
        self.assertEqual(goal["parity"]["total"], 7565)
        self.assertEqual(goal["parity"]["verified"], 0)


if __name__ == "__main__":
    unittest.main()
