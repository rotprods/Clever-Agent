from __future__ import annotations

import unittest
from scripts.cp03 import finalize_w02_teardown as finalizer


class W02TeardownFinalizerTests(unittest.TestCase):
    def test_canonical_transition_is_frozen(self) -> None:
        self.assertEqual(finalizer.TASK, "W02-04")
        self.assertEqual(finalizer.NEXT, "W02-06")
        self.assertEqual(finalizer.EVIDENCE_ID, "EVID-W02-TEARDOWN-20260909")
        self.assertEqual(finalizer.CLAIM_ID, "CLAIM-CP03-W02-TEARDOWN-001")

    def test_bad_digest_fails_before_state_mutation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "artifact digest"):
            finalizer.finalize(run_id=1, validated_head="a"*40, artifact_id=1, artifact_digest="a"*64)

    def test_floating_head_fails_before_state_mutation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "validated_head"):
            finalizer.finalize(run_id=1, validated_head="main", artifact_id=1, artifact_digest="sha256:"+"a"*64)

    def test_nonpositive_run_or_artifact_fails(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "run/artifact"):
            finalizer.finalize(run_id=0, validated_head="a"*40, artifact_id=1, artifact_digest="sha256:"+"a"*64)


if __name__ == "__main__":
    unittest.main()
