from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.cp03.w02_recovery_retest import (
    PROBES,
    REPETITIONS,
    SEED_BASE,
    plan_digest,
    validate_report,
)


def synthetic_report() -> dict:
    rows = []
    for repetition in range(1, REPETITIONS + 1):
        seed = SEED_BASE + repetition
        for probe, command in PROBES:
            rows.append(
                {
                    "repetition": repetition,
                    "seed": seed,
                    "probe": probe,
                    "command": list(command),
                    "exit_code": 0,
                    "duration_ms": 1.0,
                    "stdout_sha256": "0" * 64,
                    "stderr_sha256": "0" * 64,
                    "stdout_tail": "",
                    "stderr_tail": "",
                }
            )
    return {
        "schema_version": 1,
        "task": "W02-16",
        "gate": "G5",
        "source_head": "deadbeef",
        "suite": "P02_REPEATED_RECOVERY",
        "suite_plan_sha256": plan_digest(),
        "repetitions_required": REPETITIONS,
        "repetitions_executed": REPETITIONS,
        "seed_base": SEED_BASE,
        "seeds": [SEED_BASE + index for index in range(1, REPETITIONS + 1)],
        "probe_names": [name for name, _ in PROBES],
        "invocations_expected": REPETITIONS * len(PROBES),
        "invocations_executed": REPETITIONS * len(PROBES),
        "failed_invocations": 0,
        "all_results_retained": True,
        "best_rerun_selection": False,
        "performance_baseline_same_host": "NOT_RUN",
        "performance_claims": 0,
        "provider_egress_executions": 0,
        "model_executions": 0,
        "tool_executions": 0,
        "parity_promotions": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "host": {"system": "test", "release": "test", "machine": "test"},
        "results": rows,
        "result": "PASS",
    }


class RecoveryRetestContract(unittest.TestCase):
    def test_exact_twenty_complete_matrix_is_accepted(self) -> None:
        validate_report(synthetic_report())

    def test_missing_repetition_record_is_rejected(self) -> None:
        report = synthetic_report()
        report["results"].pop()
        report["invocations_executed"] -= 1
        with self.assertRaisesRegex(ValueError, "retained"):
            validate_report(report)

    def test_failed_invocation_cannot_be_cherry_picked_away(self) -> None:
        report = synthetic_report()
        report["results"][0]["exit_code"] = 1
        report["failed_invocations"] = 1
        report["result"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "failing invocation"):
            validate_report(report)

    def test_performance_not_run_cannot_be_promoted_by_recovery_receipt(self) -> None:
        report = synthetic_report()
        report["performance_baseline_same_host"] = "PASS"
        report["performance_claims"] = 1
        with self.assertRaisesRegex(ValueError, "must not fabricate"):
            validate_report(report)

    def test_denominator_drift_is_rejected(self) -> None:
        report = copy.deepcopy(synthetic_report())
        report["global_denominator"] = 7564
        with self.assertRaisesRegex(ValueError, "drift"):
            validate_report(report)

    def test_release_finalizer_is_importable_when_executed_by_path(self) -> None:
        root = Path(__file__).resolve().parents[1]
        finalizer = root / "scripts/cp03/finalize_w02_recovery_retest.py"
        probe = (
            "import runpy; "
            f"runpy.run_path({str(finalizer)!r}, run_name='w02_16_finalizer_import_probe')"
        )
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=tempfile.gettempdir(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
