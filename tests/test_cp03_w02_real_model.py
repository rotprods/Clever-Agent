from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.cp03.w02_real_model import (
    DEFAULT_MANIFEST,
    LaneError,
    acquire_artifact,
    validate_manifest,
    verify_artifact,
)


class W02RealModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))

    def test_canonical_manifest_is_immutable_real_lane(self) -> None:
        validate_manifest(self.manifest)
        artifact = self.manifest["artifact"]
        self.assertEqual(self.manifest["task"], "W02-09")
        self.assertEqual(self.manifest["model"]["catalog_model_id"], "qwen3:0.6b")
        self.assertEqual(self.manifest["engine"]["openjarvis_key"], "llamacpp")
        self.assertEqual(artifact["kind"], "REAL_MODEL_WEIGHTS")
        self.assertEqual(artifact["size_bytes"], 484220320)
        self.assertEqual(
            artifact["sha256"],
            "9acfc1e001311f34b4252001b626f2e466d592a42065f66571bff3790d4e1b14",
        )
        self.assertIn(artifact["revision"], artifact["download_url"])
        for ref in (
            self.manifest["upstream"]["commit"],
            self.manifest["model"]["base_revision"],
            self.manifest["engine"]["runtime_commit"],
            artifact["revision"],
        ):
            self.assertEqual(len(ref), 40)
            self.assertNotIn(ref, {"main", "master", "latest"})
        self.assertFalse(self.manifest["engine"]["runtime_execution_in_w02_09"])
        self.assertEqual(self.manifest["counters"]["verified_capabilities"], 0)
        self.assertEqual(self.manifest["counters"]["parity_promotions"], 0)
        self.assertEqual(self.manifest["counters"]["model_executions"], 0)

    def test_mock_artifact_cannot_satisfy_manifest(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["artifact"]["kind"] = "MOCK_MODEL_WEIGHTS"
        with self.assertRaisesRegex(LaneError, "mock/synthetic"):
            validate_manifest(manifest)

    def test_floating_artifact_revision_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["artifact"]["revision"] = "main"
        with self.assertRaisesRegex(LaneError, "immutable"):
            validate_manifest(manifest)

    def test_missing_real_weights_are_blocked(self) -> None:
        with TemporaryDirectory() as directory:
            receipt = verify_artifact(Path(directory) / "missing.gguf", self.manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertEqual(receipt["reason"], "ARTIFACT_MISSING")
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

    def test_corrupt_weights_are_blocked(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.gguf"
            path.write_bytes(b"GGUFcorrupt")
            receipt = verify_artifact(path, self.manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertTrue(receipt["reason"].startswith("ARTIFACT_CORRUPT:"))
        self.assertIn("size:", receipt["reason"])
        self.assertIn("sha256", receipt["reason"])

    def test_verifier_accepts_only_matching_size_hash_and_magic(self) -> None:
        payload = b"GGUF" + b"real-test-bytes"
        manifest = copy.deepcopy(self.manifest)
        manifest["artifact"]["size_bytes"] = len(payload)
        manifest["artifact"]["sha256"] = hashlib.sha256(payload).hexdigest()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.gguf"
            path.write_bytes(payload)
            receipt = verify_artifact(path, manifest)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["observed_magic_hex"], "47475546")
        self.assertEqual(receipt["model_executions"], 0)

    def test_acquisition_without_explicit_network_grant_is_blocked(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            receipt = acquire_artifact(Path(directory) / "model.gguf", self.manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertEqual(receipt["reason"], "ACQUISITION_GRANT_MISSING")

    def test_wrong_magic_is_blocked_even_if_hash_and_size_match(self) -> None:
        payload = b"NOPE" + b"payload"
        manifest = copy.deepcopy(self.manifest)
        manifest["artifact"]["size_bytes"] = len(payload)
        manifest["artifact"]["sha256"] = hashlib.sha256(payload).hexdigest()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.gguf"
            path.write_bytes(payload)
            receipt = verify_artifact(path, manifest)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn("magic:", receipt["reason"])


if __name__ == "__main__":
    unittest.main()
