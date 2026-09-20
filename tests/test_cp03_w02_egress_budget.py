from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class W02EgressBudgetTests(unittest.TestCase):
    def test_frontier_is_w02_07_or_its_evidence_backed_successor(self) -> None:
        graph = json.loads(
            (ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json").read_text(encoding="utf-8")
        )
        self.assertEqual(graph["global_denominator"], 7565)
        self.assertEqual(graph["openjarvis_obligations"], 646)
        tasks = {row["id"]: row for row in graph["tasks"]}
        self.assertEqual(tasks["W02-06"]["status"], "COMPLETE")
        self.assertEqual(tasks["W02-07"]["depends_on"], ["W02-06"])
        if tasks["W02-07"]["status"] == "READY":
            self.assertEqual(graph["first_executable_task"], "W02-07")
            self.assertEqual(tasks["W02-08"]["status"], "BLOCKED")
        else:
            self.assertEqual(tasks["W02-07"]["status"], "COMPLETE")
            self.assertTrue(tasks["W02-07"]["proof"])
            self.assertEqual(graph["first_executable_task"], "W02-08")
            self.assertEqual(tasks["W02-08"]["status"], "READY")
        self.assertEqual(tasks["W02-09"]["status"], "BLOCKED")

    def test_inference_wire_payload_cannot_self_grant_egress_or_budget(self) -> None:
        proto = (ROOT / "contracts/proto/clever/v1/inference.proto").read_text(encoding="utf-8")
        match = re.search(r"message InferenceRequest \{(?P<body>.*?)\n\}", proto, re.DOTALL)
        self.assertIsNotNone(match)
        body = match.group("body")
        for forbidden in ("destination", "endpoint", "grant_id", "secret_handle", "cost_microunits"):
            self.assertNotIn(forbidden, body)
        self.assertIn("PrincipalRef principal", body)
        self.assertIn("string session_id", body)
        self.assertIn("InferenceConfig config", body)

    def test_kernel_admission_is_fail_closed_and_binds_all_authority_dimensions(self) -> None:
        source = (ROOT / "kernel/crates/clever-kernel/src/inference_policy.rs").read_text(encoding="utf-8")
        required = (
            "RemoteGrantRequired",
            "GrantPrincipalMismatch",
            "GrantSessionMismatch",
            "DestinationNotAllowed",
            "SecretHandleMismatch",
            "InputTokenBudgetExceeded",
            "OutputTokenBudgetExceeded",
            "TotalTokenBudgetExceeded",
            "CostBudgetExceeded",
            "validate_remote_destination(destination)?",
            "same_principal(request_principal, &grant.principal)",
            "request.session_id != grant.session_id",
            "destination != &grant.destination",
            "estimated_input_tokens > grant.max_input_tokens",
            "config.max_output_tokens > grant.max_output_tokens",
            "estimated_cost_microunits > grant.max_cost_microunits",
        )
        for token in required:
            self.assertIn(token, source)

    def test_secret_handle_is_opaque_and_debug_redacted(self) -> None:
        source = (ROOT / "kernel/crates/clever-kernel/src/inference_policy.rs").read_text(encoding="utf-8")
        self.assertIn('formatter.write_str("SecretHandle(<redacted>)")', source)
        self.assertNotIn("pub fn as_str", source)
        self.assertNotIn("pub fn expose", source)
        self.assertNotIn("pub fn value", source)
        self.assertIn("secret_handle_used: bool", source)

    def test_w02_07_does_not_execute_models_or_tools(self) -> None:
        source = (ROOT / "kernel/crates/clever-kernel/src/inference_policy.rs").read_text(encoding="utf-8")
        for forbidden in ("reqwest", "hyper::", "Command::new", "std::process", "tool_call", "execute_tool"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
