from pathlib import Path
import unittest


WORKFLOW = Path('.github/workflows/cp03-w02-egress-budget.yml')


class W02EgressWorkflowRegressionTests(unittest.TestCase):
    def test_kernel_regression_exports_mandatory_python_prerequisite(self) -> None:
        text = WORKFLOW.read_text(encoding='utf-8')
        marker = '      - name: Kernel regression\n'
        self.assertIn(marker, text)
        block = text.split(marker, 1)[1].split('      - name:', 1)[0]
        self.assertIn('CLEVER_TEST_PYTHON', block)
        self.assertIn('command -v python', block)
        self.assertIn('cargo test --locked --manifest-path kernel/Cargo.toml -p clever-kernel', block)


if __name__ == '__main__':
    unittest.main()
