from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / ".github/workflows/cp03-w02-control-port.yml"
MODEL = ROOT / ".github/workflows/cp03-w02-model-bridge.yml"
UNARY_REAL_TEST = "real_openjarvis_unary_inference_uses_pinned_llamacpp_lane"


class UnaryReleaseRegressionTests(unittest.TestCase):
    def test_legacy_control_gauntlets_do_not_execute_real_model_lane_without_prerequisites(self) -> None:
        text = CONTROL.read_text(encoding="utf-8")
        skip = f"--skip {UNARY_REAL_TEST}"
        self.assertGreaterEqual(
            text.count(skip),
            2,
            "both W02-05 push and PR regression lanes must exclude the separately-proven real-model test",
        )

    def test_model_bridge_regression_excludes_real_model_lane_without_prerequisites(self) -> None:
        text = MODEL.read_text(encoding="utf-8")
        self.assertIn(f"--skip {UNARY_REAL_TEST}", text)

    def test_model_bridge_state_gate_tracks_dag_frontier_instead_of_stale_w02_09(self) -> None:
        text = MODEL.read_text(encoding="utf-8")
        self.assertNotIn("graph['first_executable_task']=='W02-09'", text)
        self.assertNotIn("tasks['W02-09']['status']=='READY'", text)
        self.assertNotIn("tasks['W02-10']['status']=='BLOCKED'", text)
        self.assertIn("frontier_id=graph['first_executable_task']", text)
        self.assertIn("frontier['status']=='READY'", text)
        self.assertIn("tasks['W02-10']['status']=='COMPLETE'", text)


if __name__ == "__main__":
    unittest.main()
