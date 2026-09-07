import unittest
from scripts.cp03.control_gate import preflight, validate_single


class ControlGateTests(unittest.TestCase):
    def test_absent_interpreter_fails(self):
        with self.assertRaises(ValueError):
            preflight({})

    def test_relative_interpreter_fails(self):
        with self.assertRaises(ValueError):
            preflight({"CLEVER_TEST_PYTHON": "python"})

    def test_empty_result_fails(self):
        with self.assertRaises(ValueError):
            validate_single("named", 0, "")

    def test_zero_tests_fails(self):
        with self.assertRaises(ValueError):
            validate_single("named", 0, "test named ... ok\ntest result: ok. 0 passed; 0 failed; 0 ignored;")

    def test_ignored_test_fails(self):
        with self.assertRaises(ValueError):
            validate_single("named", 0, "test named ... ignored\ntest result: ok. 0 passed; 0 failed; 1 ignored;")

    def test_wrong_name_fails(self):
        with self.assertRaises(ValueError):
            validate_single("named", 0, "test other ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored;")

    def test_failed_exit_fails(self):
        with self.assertRaises(ValueError):
            validate_single("named", 1, "test named ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored;")

    def test_valid_pass(self):
        validate_single("named", 0, "test named ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored;")

    def test_build_failure_is_not_red(self):
        with self.assertRaises(ValueError):
            validate_single("named", 101, "error: missing crate", True)

    def test_panic_without_assertion_is_not_red(self):
        with self.assertRaises(ValueError):
            validate_single("named", 101, "test named ... FAILED\nthread panicked at import error\ntest result: FAILED. 0 passed; 1 failed; 0 ignored;", True)

    def test_assertion_is_valid_red(self):
        validate_single("named", 101, "test named ... FAILED\nthread panicked at assertion failed\ntest result: FAILED. 0 passed; 1 failed; 0 ignored;", True)


if __name__ == "__main__":
    unittest.main()
