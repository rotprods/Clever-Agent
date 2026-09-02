from __future__ import annotations

from io import BytesIO
from pathlib import Path
import struct
import unittest

from adapters.openjarvis import sidecar


class OpenJarvisSidecarTests(unittest.TestCase):
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
