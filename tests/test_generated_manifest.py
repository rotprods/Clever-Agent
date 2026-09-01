from __future__ import annotations

from pathlib import Path
import unittest

from scripts.contracts.generated_manifest import is_canonical_generated_file


class GeneratedManifestTests(unittest.TestCase):
    def test_transient_runtime_artifacts_are_excluded(self) -> None:
        rejected = (
            "contracts/sdk/python/gen/clever/v1/__pycache__/events_pb2.cpython-312.pyc",
            "contracts/sdk/python/gen/clever/v1/events_pb2.pyc",
            "contracts/sdk/python/gen/clever/v1/events_pb2.pyo",
            "contracts/sdk/typescript/src/gen/.cache/index.ts",
            "contracts/sdk/swift/Sources/CleverContracts/Gen/.DS_Store",
        )
        for raw in rejected:
            with self.subTest(path=raw):
                self.assertFalse(is_canonical_generated_file(Path(raw)))

    def test_generated_source_and_wire_outputs_are_canonical(self) -> None:
        accepted = (
            "contracts/sdk/python/gen/clever/v1/events_pb2.py",
            "contracts/sdk/typescript/src/gen/clever/v1/events_pb.ts",
            "contracts/sdk/swift/Sources/CleverContracts/Gen/clever/v1/events.pb.swift",
            "contracts/sdk/rust/src/gen/clever.v1.rs",
            "contracts/fixtures/wire/event.bin",
            "contracts/fixtures/wire/event.protobuf.json",
        )
        for raw in accepted:
            with self.subTest(path=raw):
                self.assertTrue(is_canonical_generated_file(Path(raw)))


if __name__ == "__main__":
    unittest.main()
