from pathlib import Path
import unittest


WORKFLOW = Path('.github/workflows/cp03-w02-egress-budget.yml')


class W02EgressWorkflowRegressionTests(unittest.TestCase):
    def test_kernel_regression_installs_and_exports_mandatory_python_prerequisites(self) -> None:
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn("python -m pip install --disable-pip-version-check -r contracts/sdk/python/requirements.txt", text)
        marker = '      - name: Kernel regression (hermetic lane)\n'
        self.assertIn(marker, text)
        block = text.split(marker, 1)[1].split('      - name:', 1)[0]
        self.assertIn('CLEVER_TEST_PYTHON', block)
        self.assertIn('command -v python', block)
        self.assertIn('cargo test --locked --manifest-path kernel/Cargo.toml -p clever-kernel', block)
        self.assertIn('--skip real_openjarvis_sidecar_is_supervised_and_bridged_without_promotion', block)

    def test_native_openjarvis_regression_is_not_relabelled_as_pass(self) -> None:
        text = WORKFLOW.read_text(encoding='utf-8')
        marker = '      - name: Preserve native-lane classification\n'
        self.assertIn(marker, text)
        block = text.split(marker, 1)[1].split('      - name:', 1)[0]
        self.assertIn("W02-02", block)
        self.assertIn("native", block)
        self.assertIn("PASS", block)
        self.assertIn("parity_promotions", block)


if __name__ == '__main__':
    unittest.main()
