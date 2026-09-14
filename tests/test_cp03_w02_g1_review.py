from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
FINDINGS = json.loads((ROOT / "reports/reviews/CP03_W02_G1_FINDINGS.json").read_text())


class G1IndependentReviewTests(unittest.TestCase):
    def task_graph(self):
        return json.loads((ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json").read_text())

    def finding(self, finding_id: str):
        for row in FINDINGS["findings"]:
            if row["id"] == finding_id:
                return row
        self.fail(f"missing finding {finding_id}")

    def test_frozen_denominators_and_parity(self):
        graph = self.task_graph()
        self.assertEqual(graph["global_denominator"], 7565)
        self.assertEqual(graph["openjarvis_obligations"], 646)
        scope = json.loads((ROOT / "inventory/cp03/W02_SCOPE_LOCK.json").read_text())
        self.assertEqual(scope["w02_proof_units"], 47)
        goal = json.loads((ROOT / "GOAL_STATE.json").read_text())
        self.assertEqual(goal["parity"]["total"], 7565)
        self.assertEqual(goal["parity"]["verified"], 0)

    def test_g1_tasks_are_complete_and_inference_is_next(self):
        graph = self.task_graph()
        tasks = {row["id"]: row for row in graph["tasks"]}
        for task_id in ("W02-03", "W02-04", "W02-05"):
            self.assertEqual(tasks[task_id]["status"], "COMPLETE")
            self.assertTrue(tasks[task_id]["proof"])
            self.assertTrue(all(p.get("result") == "PASS" for p in tasks[task_id]["proof"]))
        self.assertEqual(tasks["W02-06"]["status"], "READY")
        self.assertEqual(set(tasks["W02-06"]["depends_on"]), {"W02-01", "W02-04", "W02-05"})
        self.assertEqual(graph["first_executable_task"], "W02-06")

    def test_sidecar_hello_is_unsolicited_and_responses_correlate(self):
        text = (ROOT / "adapters/openjarvis/sidecar.py").read_text()
        self.assertRegex(text, r'def _frame\([^)]*correlation_id: str = ""')
        self.assertIn('return _frame("openjarvis-hello", "hello", hello)', text)
        for needle in (
            "correlation_id=request.frame_id",
            "health_frame(reasons=diagnostics",
            "health_frame(correlation_id=request.frame_id)",
            '"error", error, correlation_id=request.frame_id',
        ):
            self.assertIn(needle, text)

    def test_adapter_keeps_bounded_io_and_atomic_registry(self):
        text = (ROOT / "kernel/crates/clever-kernel/src/adapter.rs").read_text()
        for needle in (
            "mpsc::sync_channel(max_inbound_frames)",
            "max_inbound_bytes",
            "pending_bytes",
            "write_timeout",
            "recv_timeout(self.policy.write_timeout)",
            "process.process_group(0)",
            "wait_child_bounded",
            "join_handle_bounded",
            "registry.register_batch(descriptors)",
        ):
            self.assertIn(needle, text)
        self.assertNotIn("self.child\n            .wait()", text)

    def test_known_stderr_risk_is_never_silently_lost(self):
        text = (ROOT / "kernel/crates/clever-kernel/src/adapter.rs").read_text()
        finding = self.finding("SEC-P2-STDERR")
        if "stderr(Stdio::inherit())" in text:
            self.assertEqual(finding["status"], "OPEN")
            self.assertIn("W02-07", finding["blocking_scope"])
        else:
            self.assertNotEqual(finding["status"], "OPEN")

    def test_cleanup_observability_risk_is_tracked_until_results_are_surfaced(self):
        text = (ROOT / "kernel/crates/clever-kernel/src/adapter.rs").read_text()
        finding = self.finding("REL-P1-CLEANUP-OBSERVABILITY")
        collapse_markers = (
            "let _ = self.child.kill();",
            "self.run_cleanup_bounded();",
            "let _ = self.join_threads_bounded();",
            "self.termination_complete = true;",
        )
        if all(marker in text for marker in collapse_markers):
            self.assertEqual(finding["status"], "OPEN")
        else:
            self.assertNotEqual(finding["status"], "OPEN")

    def test_unpinned_actions_are_exactly_accounted_for(self):
        offenders = []
        use_re = re.compile(r"^\s*-\s*uses:\s*([^\s#]+)", re.MULTILINE)
        for workflow in sorted((ROOT / ".github/workflows").glob("*.yml")):
            for use in use_re.findall(workflow.read_text()):
                if use.startswith("./"):
                    continue
                if "@" not in use or not re.fullmatch(r"[0-9a-f]{40}", use.rsplit("@", 1)[1]):
                    offenders.append(f"{workflow.name}:{use}")
        finding = self.finding("SUPPLY-P1-UNPINNED-ACTIONS")
        self.assertEqual(finding["status"], "OPEN")
        self.assertEqual(len(offenders), finding["observed_count"])
        self.assertGreater(len(offenders), 0)

    def test_upstream_pin_is_exact(self):
        ledger = (ROOT / "UPSTREAM_LEDGER.yaml").read_text()
        self.assertIn("72033b8ec288aa067ce4530ff9d96bf231e9c4e5", ledger)
        self.assertNotRegex(ledger, r"\bref:\s*(main|master|latest)\b")

    def test_review_finding_ids_are_unique_and_have_actions(self):
        ids = [row["id"] for row in FINDINGS["findings"]]
        self.assertEqual(len(ids), len(set(ids)))
        for row in FINDINGS["findings"]:
            self.assertIn(row["severity"], {"P0", "P1", "P2", "P3"})
            self.assertTrue(row["recommended_action"])
            self.assertTrue(row["evidence"])

    def test_external_branch_protection_blocker_is_explicit(self):
        row = self.finding("SEC-P1-BRANCH-PROTECTION")
        self.assertEqual(row["status"], "OPEN_EXTERNAL")
        self.assertIn("production_release", row["blocking_scope"])


if __name__ == "__main__":
    unittest.main()
