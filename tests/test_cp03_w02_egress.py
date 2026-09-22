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
        self.assertIn('--skip real_openjarvis_unary_inference_uses_pinned_llamacpp_lane', block)

    def test_historical_hermetic_lane_never_executes_native_real_model_tests(self) -> None:
        text = WORKFLOW.read_text(encoding='utf-8')
        marker = '      - name: Kernel regression (hermetic lane)\n'
        block = text.split(marker, 1)[1].split('      - name:', 1)[0]
        self.assertIn('--skip real_openjarvis_sidecar_is_supervised_and_bridged_without_promotion', block)
        self.assertIn('--skip real_openjarvis_unary_inference_uses_pinned_llamacpp_lane', block)
        self.assertNotIn('CLEVER_OPENJARVIS_SRC=', block)

    def test_native_openjarvis_regression_is_not_relabelled_as_pass(self) -> None:
        text = WORKFLOW.read_text(encoding='utf-8')
        marker = '      - name: Preserve native-lane classification\n'
        self.assertIn(marker, text)
        block = text.split(marker, 1)[1].split('      - name:', 1)[0]
        self.assertIn("W02-02", block)
        self.assertIn("native", block)
        self.assertIn("PASS", block)
        self.assertIn("parity_promotions", block)

    def test_frontier_guard_is_dag_relative_not_pinned_to_historical_w02_07(self) -> None:
        text = WORKFLOW.read_text(encoding='utf-8')
        marker = '      - name: Protect parity denominator and legal W02 frontier\n'
        self.assertIn(marker, text)
        block = text.split(marker, 1)[1]
        self.assertIn("goal['parity']['total']==7565", block)
        self.assertIn("goal['parity']['verified']==0", block)
        self.assertIn("task['W02-07']['status']=='COMPLETE'", block)
        self.assertIn("frontier_id=task_graph['first_executable_task']", block)
        self.assertIn("frontier['status'] in {'READY','IN_PROGRESS'}", block)
        self.assertIn("task[dep]['status']=='COMPLETE' and task[dep]['proof']", block)
        self.assertNotIn("first_executable_task']=='W02-07'", block)
        self.assertNotIn("task['W02-07']['status']=='READY'", block)


if __name__ == '__main__':
    unittest.main()
