from __future__ import annotations

import copy
import unittest

from scripts.cp03.w02_performance_baseline import BUDGET, _request, _summary, validate


class W02PerformanceBaselineTests(unittest.TestCase):
    def sample(self, path: str, latency: float, ttft: float, tokens: int = 8) -> dict:
        return {
            "path": path,
            "latency_ms": latency,
            "ttft_ms": ttft,
            "output_tokens": tokens,
            "throughput_tokens_per_s": tokens / (latency / 1000.0),
            "peak_rss_kib": {"client": 1000, "llama_server": 2000},
        }

    def report(self) -> dict:
        samples = [
            self.sample("direct", 100, 20),
            self.sample("adapted", 110, 25),
            self.sample("adapted", 120, 30),
            self.sample("direct", 90, 18),
            self.sample("direct", 95, 19),
            self.sample("adapted", 115, 28),
        ]
        return {
            "schema_version": 1,
            "task": "W02-16",
            "suite": "P01_SAME_HOST_PERFORMANCE_BASELINE",
            "result": "PASS",
            "budget": copy.deepcopy(BUDGET),
            "same_host": True,
            "paths": ["direct_openjarvis_stream_full", "canonical_adapterframe_sidecar_stream"],
            "samples": samples,
            "summary": _summary(samples),
            "performance_threshold": "MEASUREMENT_ONLY_NO_POST_HOC_THRESHOLD",
            "provider_egress_executions": 0,
            "tool_executions": 0,
            "parity_promotions": 0,
            "global_denominator": 7565,
            "openjarvis_obligations": 646,
        }

    def test_budget_is_fixed_and_balanced_before_measurement(self) -> None:
        self.assertEqual(BUDGET["warmups_per_path"], 1)
        self.assertEqual(BUDGET["samples_per_path"], 3)
        self.assertEqual(BUDGET["order"].count("direct"), 3)
        self.assertEqual(BUDGET["order"].count("adapted"), 3)
        self.assertEqual(BUDGET["max_output_tokens"], 32)

    def test_request_is_streaming_bounded_and_local_lane(self) -> None:
        request = _request("unit")
        self.assertTrue(request.config.stream)
        self.assertEqual(request.config.max_output_tokens, 32)
        self.assertEqual(request.engine_id, "llamacpp")
        self.assertEqual(request.model_id, "qwen3:0.6b")
        self.assertEqual(len(request.inputs), 1)

    def test_summary_keeps_direct_and_adapted_samples_separate(self) -> None:
        report = self.report()
        self.assertEqual(report["summary"]["direct"]["sample_count"], 3)
        self.assertEqual(report["summary"]["adapted"]["sample_count"], 3)
        self.assertGreater(report["summary"]["adapted_over_direct"]["latency_ratio"], 0)

    def test_validator_accepts_complete_measurement_only_baseline(self) -> None:
        validate(self.report())

    def test_validator_rejects_post_hoc_budget_mutation(self) -> None:
        report = self.report()
        report["budget"]["samples_per_path"] = 2
        with self.assertRaises(AssertionError):
            validate(report)

    def test_validator_rejects_false_green_or_authority_delta(self) -> None:
        for key in ("provider_egress_executions", "tool_executions", "parity_promotions"):
            report = self.report()
            report[key] = 1
            with self.assertRaises(AssertionError, msg=key):
                validate(report)

    def test_validator_rejects_missing_memory_or_ttft_evidence(self) -> None:
        report = self.report()
        report["samples"][0]["peak_rss_kib"]["client"] = 0
        with self.assertRaises(AssertionError):
            validate(report)
        report = self.report()
        report["samples"][0]["ttft_ms"] = 0
        with self.assertRaises(AssertionError):
            validate(report)


if __name__ == "__main__":
    unittest.main()
