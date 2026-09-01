from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.cp03.baseline import PIN, build_report, parse_junit


def junit(path: Path, *, tests: int = 4, failures: int = 0, errors: int = 0, skipped: int = 0) -> None:
    path.write_text(
        f'<testsuite tests="{tests}" failures="{failures}" errors="{errors}" skipped="{skipped}" time="0.5"></testsuite>',
        encoding="utf-8",
    )


class Cp03BaselineTests(unittest.TestCase):
    def metadata(self) -> dict:
        return {
            "source_commit": PIN,
            "network_mode": "none",
            "read_only_root": True,
            "cap_drop_all": True,
            "no_new_privileges": True,
            "secrets_forwarded": False,
            "pythonpath": "/src/src",
            "selected_tests": ["tests/core/test_events.py"],
            "marker_expression": "not live and not cloud and not hub",
        }

    def test_parse_junit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "junit.xml"
            junit(path, tests=7, skipped=1)
            result = parse_junit(path)
            self.assertEqual(7, result["tests"])
            self.assertEqual(1, result["skipped"])

    def test_clean_hermetic_run_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "junit.xml"
            junit(path)
            report = build_report(junit=path, metadata=self.metadata(), exit_code=0)
            self.assertEqual("PASS", report["status"])
            self.assertTrue(report["invariants"]["not_run_is_not_pass"])

    def test_network_enabled_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "junit.xml"
            junit(path)
            metadata = self.metadata()
            metadata["network_mode"] = "bridge"
            report = build_report(junit=path, metadata=metadata, exit_code=0)
            self.assertEqual("FAIL", report["status"])
            self.assertIn("test execution was not network-disabled", report["errors"])

    def test_zero_tests_and_pytest_failure_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "junit.xml"
            junit(path, tests=0)
            report = build_report(junit=path, metadata=self.metadata(), exit_code=5)
            self.assertEqual("FAIL", report["status"])

    def test_missing_junit_is_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.xml"
            report = build_report(junit=path, metadata=self.metadata(), exit_code=4)
            self.assertEqual("FAIL", report["status"])
            self.assertEqual(0, report["results"]["tests"])
            self.assertTrue(any("junit report is missing" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
