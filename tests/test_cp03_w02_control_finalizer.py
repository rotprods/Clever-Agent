from __future__ import annotations

import unittest
from scripts.cp03 import finalize_w02_control as finalizer


class W02ControlFinalizerTests(unittest.TestCase):
    def test_canonical_identity_is_frozen(self) -> None:
        self.assertEqual(finalizer.TASK, "W02-05")
        self.assertEqual(finalizer.NEXT, "W02-04")
        self.assertEqual(finalizer.EVIDENCE_ID, "EVID-W02-CONTROL-ATOMIC-20260909")
        self.assertEqual(finalizer.CLAIM_ID, "CLAIM-CP03-W02-CONTROL-002")

    def test_rejects_noncanonical_artifact_digest_before_mutation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "artifact digest"):
            finalizer.finalize(
                run_id=1,
                validated_head="a" * 40,
                artifact_id=1,
                artifact_digest="a" * 64,
            )

    def test_rejects_non_sha_head_before_mutation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "validated_head"):
            finalizer.finalize(
                run_id=1,
                validated_head="main",
                artifact_id=1,
                artifact_digest="sha256:" + "a" * 64,
            )

    def test_rejects_nonpositive_run_or_artifact_before_mutation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "run/artifact"):
            finalizer.finalize(
                run_id=0,
                validated_head="a" * 40,
                artifact_id=1,
                artifact_digest="sha256:" + "a" * 64,
            )


if __name__ == "__main__":
    unittest.main()
