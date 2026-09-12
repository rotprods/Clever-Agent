from __future__ import annotations

from io import BytesIO
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from adapters.openjarvis import sidecar


class OpenJarvisSidecarTests(unittest.TestCase):
    def test_initial_hello_is_unsolicited(self) -> None:
        hello = sidecar.hello_frame()
        self.assertTrue(hello.frame_id)
        self.assertEqual(hello.correlation_id, "")

    def test_protocol_responses_correlate_to_each_request(self) -> None:
        request_bodies = (
            ("registry_snapshot_request", sidecar.adapter_pb2.RegistrySnapshotRequest()),
            ("health_request", sidecar.adapter_pb2.AdapterHealthRequest()),
            ("cancel", sidecar.adapter_pb2.AdapterCancel(target_request_id="absent")),
            ("busy", sidecar.adapter_pb2.AdapterBusy()),
            ("shutdown", sidecar.adapter_pb2.AdapterShutdown(reason="test")),
        )
        requests = [sidecar._frame(f"request-{index}", body, message)
                    for index, (body, message) in enumerate(request_bodies)]
        incoming = BytesIO()
        sidecar.write_frame(incoming, sidecar._frame(
            "ack", "hello_ack", sidecar.adapter_pb2.AdapterHelloAck(accepted=True)))
        for request in requests:
            sidecar.write_frame(incoming, request)
        incoming.seek(0)
        outgoing = BytesIO()
        snapshot = sidecar.adapter_pb2.RegistrySnapshot(runtime_id=sidecar.RUNTIME_ID)
        with patch.object(sidecar, "discover_registry_snapshot", return_value=(snapshot, {"unsupported_registries": []})):
            self.assertEqual(sidecar.run_protocol(incoming, outgoing), 0)
        outgoing.seek(0)
        self.assertEqual(sidecar.read_frame(outgoing).WhichOneof("body"), "hello")
        expected_bodies = ("registry_snapshot", "health", "health", "error", "health")
        for request, expected_body in zip(requests, expected_bodies):
            response = sidecar.read_frame(outgoing)
            with self.subTest(request=request.WhichOneof("body")):
                self.assertTrue(response.frame_id)
                self.assertEqual(response.correlation_id, request.frame_id)
                self.assertEqual(response.WhichOneof("body"), expected_body)
        self.assertEqual(response.health.status, sidecar.runtime_pb2.RUNTIME_HEALTH_STATUS_STOPPING)
        self.assertIsNone(sidecar.read_frame(outgoing))

    def test_reserved_metadata_is_removed(self) -> None:
        cleaned = sidecar.sanitize_metadata(
            {
                "entry_module": "example.module",
                "policy_override": "allow",
                "risk_class": "R0",
                "authorization_scope": "*",
            }
        )
        self.assertEqual(cleaned, {"entry_module": "example.module"})

    def test_registry_map_covers_the_pinned_registry_framework(self) -> None:
        expected = {
            "ModelRegistry", "EngineRegistry", "MemoryRegistry", "FactStoreRegistry",
            "AgentRegistry", "ToolRegistry", "RouterPolicyRegistry", "BenchmarkRegistry",
            "ChannelRegistry", "LearningRegistry", "SkillRegistry", "SpeechRegistry",
            "CompressionRegistry", "TTSRegistry", "ConnectorRegistry", "MinerRegistry",
        }
        self.assertEqual(set(sidecar._REGISTRY_PRIMITIVES), expected)
        self.assertTrue(all(value != 0 for value in sidecar._REGISTRY_PRIMITIVES.values()))

    def test_registration_hints_follow_pinned_source_layout(self) -> None:
        self.assertEqual(
            sidecar._REGISTRATION_IMPORT_HINTS["CompressionRegistry"],
            ("openjarvis.sessions.compression",),
        )
        self.assertIn(
            "openjarvis.learning.routing.heuristic_policy",
            sidecar._REGISTRATION_IMPORT_HINTS["RouterPolicyRegistry"],
        )
        self.assertIn(
            "openjarvis.learning.routing.learned_router",
            sidecar._REGISTRATION_IMPORT_HINTS["RouterPolicyRegistry"],
        )
        self.assertEqual(
            sidecar._REGISTRATION_IMPORT_HINTS["TTSRegistry"],
            ("openjarvis.tools.text_to_speech",),
        )
        self.assertEqual(
            sidecar._REGISTRATION_IMPORT_HINTS["LearningRegistry"],
            ("openjarvis.learning.intelligence",),
        )

    def test_frame_reader_fails_closed_on_oversized_frame(self) -> None:
        stream = BytesIO(struct.pack(">I", sidecar.MAX_FRAME_BYTES + 1))
        with self.assertRaises(ValueError):
            sidecar.read_frame(stream)

    def test_frame_reader_fails_closed_on_partial_frame(self) -> None:
        stream = BytesIO(struct.pack(">I", 8) + b"abc")
        with self.assertRaises(EOFError):
            sidecar.read_frame(stream)

    def test_sidecar_does_not_embed_provider_allowlist(self) -> None:
        source = Path(sidecar.__file__).read_text(encoding="utf-8")
        for provider_key in ("ollama", "vllm", "simple", "calculator", "web_search"):
            self.assertNotIn(f'"{provider_key}"', source)
            self.assertNotIn(f"'{provider_key}'", source)

    def test_sidecar_image_pins_contract_runtime_dependency(self) -> None:
        dockerfile = (Path(__file__).resolve().parents[1] / "scripts/cp03/Dockerfile.openjarvis-sidecar").read_text(encoding="utf-8")
        self.assertIn("protobuf==7.36.0", dockerfile)
        self.assertIn("uv pip install --python /src/.venv/bin/python", dockerfile)
        self.assertNotIn("python -m pip", dockerfile)
        self.assertNotIn("apt-get", dockerfile)


if __name__ == "__main__":
    unittest.main()
