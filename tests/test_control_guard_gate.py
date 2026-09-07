import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location("gate", Path(__file__).resolve().parents[1] / "scripts/cp03/control_guard_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
class GateTests(unittest.TestCase):
    def test_valid_result(self):
        self.assertEqual(gate.parsed_results("test a ... ok\n", {"a"}), {"a": "ok"})
    def test_empty_is_not_pass(self):
        with self.assertRaises(ValueError): gate.parsed_results("", {"a"})
    def test_omitted_case(self):
        with self.assertRaises(ValueError): gate.parsed_results("test a ... ok\n", {"a", "b"})
    def test_ignored_case(self):
        with self.assertRaises(ValueError): gate.parsed_results("test a ... ignored\n", {"a"})
    def test_duplicate_case(self):
        with self.assertRaises(ValueError): gate.parsed_results("test a ... ok\ntest a ... ok\n", {"a"})
    def test_unexpected_case(self):
        with self.assertRaises(ValueError): gate.parsed_results("test b ... ok\n", {"a"})
    def test_compile_error_not_reproduction(self):
        with self.assertRaises(ValueError): gate.parsed_results("error[E0308]\ntest a ... FAILED\n", {"a"})
    def test_failed_case_is_retained(self):
        self.assertEqual(gate.parsed_results("test a ... FAILED\n", {"a"}), {"a": "FAILED"})
if __name__ == "__main__": unittest.main()
