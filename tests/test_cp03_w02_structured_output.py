from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GENERATED_SDK = ROOT / "contracts" / "sdk" / "python" / "gen"
if str(GENERATED_SDK) not in sys.path:
    sys.path.insert(0, str(GENERATED_SDK))

from clever.v1 import common_pb2, identity_pb2, inference_pb2

from adapters.openjarvis.structured_output import (
    StructuredOutputError,
    ToolCallFragmentAssembler,
    validate_structured_json,
)
from adapters.openjarvis.streaming_inference import _finish_reason, execute_stream
from adapters.openjarvis.unary_inference import (
    PINNED_ENGINE_ID,
    PINNED_MODEL_ID,
    UnaryInferenceRejected,
)


def valid_stream_request() -> inference_pb2.InferenceRequest:
    request = inference_pb2.InferenceRequest(
        contract_version=common_pb2.ContractVersion(major=1, minor=2),
        request_id="req-w02-13-preflight",
        attempt_id="attempt-w02-13-preflight",
        principal=identity_pb2.PrincipalRef(user_id="user-local"),
        session_id="session-local",
        engine_id=PINNED_ENGINE_ID,
        model_id=PINNED_MODEL_ID,
        inputs=[
            inference_pb2.InferenceInput(
                role=inference_pb2.INFERENCE_ROLE_USER,
                content="Return structured data without executing any tool.",
            )
        ],
        config=inference_pb2.InferenceConfig(
            max_output_tokens=32,
            temperature=0.0,
            stream=True,
        ),
        idempotency_key="idem-w02-13-preflight",
    )
    deadline_ns = time.time_ns() + 60_000_000_000
    request.deadline_at.seconds = deadline_ns // 1_000_000_000
    request.deadline_at.nanos = deadline_ns % 1_000_000_000
    return request


class FakeMessage:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


class FakeRole:
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FakeEngine:
    def __init__(self, chunks) -> None:
        self.chunks = list(chunks)
        self.closed = False

    async def stream_full(self, _messages, **_kwargs):
        for chunk in self.chunks:
            yield chunk

    def close(self) -> None:
        self.closed = True


def native_chunk(*, content=None, tool_calls=None, finish_reason=None):
    return SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
        content_blocks=None,
        tool_results=None,
        finish_reason=finish_reason,
        usage=None,
    )


class ToolCallFragmentTests(unittest.TestCase):
    def test_fragmented_arguments_and_names_are_reassembled_as_data_only(self) -> None:
        assembler = ToolCallFragmentAssembler()
        fragments = [
            {
                "index": 0,
                "id": "call_",
                "type": "function",
                "function": {
                    "name": "danger",
                    "arguments": '{"command":"rm -',
                },
            },
            {
                "index": 0,
                "id": "001",
                "function": {
                    "name": "ous_name",
                    "arguments": 'rf /"}',
                },
            },
        ]
        with patch.object(subprocess, "run") as run_mock, patch.object(subprocess, "Popen") as popen_mock:
            assembler.ingest([fragments[0]])
            assembler.ingest([fragments[1]])
            records = assembler.finalize()
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.index, 0)
        self.assertEqual(record.call_id, "call_001")
        self.assertEqual(record.call_type, "function")
        self.assertEqual(record.name, "dangerous_name")
        self.assertEqual(record.arguments_json, '{"command":"rm -rf /"}')
        self.assertEqual(record.arguments, {"command": "rm -rf /"})
        self.assertEqual(len(record.fragments), 2)
        run_mock.assert_not_called()
        popen_mock.assert_not_called()

    def test_invalid_fragment_arguments_fail_closed_without_correction(self) -> None:
        assembler = ToolCallFragmentAssembler()
        assembler.ingest(
            [
                {
                    "index": 0,
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "lookup", "arguments": '{"x":'},
                }
            ]
        )
        with self.assertRaises(StructuredOutputError) as caught:
            assembler.finalize()
        self.assertIn("invalid JSON", str(caught.exception))

    def test_non_contiguous_indices_fail_closed(self) -> None:
        assembler = ToolCallFragmentAssembler()
        assembler.ingest(
            [
                {
                    "index": 1,
                    "id": "call_1",
                    "function": {"name": "lookup", "arguments": "{}"},
                }
            ]
        )
        with self.assertRaises(StructuredOutputError):
            assembler.finalize()

    def test_fragment_shape_is_strict_but_provider_metadata_is_retained(self) -> None:
        assembler = ToolCallFragmentAssembler()
        fragment = {
            "index": 0,
            "id": "google_stream_0",
            "type": "function",
            "function": {"name": "lookup", "arguments": "{}"},
            "thought_signature": b"opaque-provider-signature",
        }
        assembler.ingest([fragment])
        record = assembler.finalize()[0]
        self.assertEqual(record.fragments[0]["thought_signature"], b"opaque-provider-signature")
        with self.assertRaises(StructuredOutputError):
            assembler.ingest([{"index": True, "function": {"name": "x", "arguments": "{}"}}])


class StructuredJsonTests(unittest.TestCase):
    def test_invalid_json_is_explicit_failure(self) -> None:
        with self.assertRaises(StructuredOutputError) as caught:
            validate_structured_json('{"answer":', None)
        self.assertIn("invalid JSON", str(caught.exception))

    def test_schema_mismatch_is_explicit_failure(self) -> None:
        schema = {
            "type": "object",
            "required": ["answer"],
            "additionalProperties": False,
            "properties": {"answer": {"type": "integer"}},
        }
        with self.assertRaises(StructuredOutputError) as caught:
            validate_structured_json('{"answer":"not-an-int"}', schema)
        self.assertIn("schema validation failed", str(caught.exception))

    def test_valid_json_schema_returns_original_value(self) -> None:
        schema = {
            "type": "object",
            "required": ["answer"],
            "additionalProperties": False,
            "properties": {"answer": {"type": "integer"}},
        }
        self.assertEqual(validate_structured_json('{"answer":42}', schema), {"answer": 42})


class StreamingPreflightTests(unittest.TestCase):
    def test_native_tool_finish_reason_maps_to_representational_enum(self) -> None:
        self.assertEqual(
            _finish_reason("tool_calls"),
            inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL,
        )

    def test_native_tool_fragments_are_validated_then_fail_closed_until_wire_projection_exists(self) -> None:
        request = valid_stream_request()
        engine = FakeEngine(
            [
                native_chunk(
                    tool_calls=[
                        {
                            "index": 0,
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "lookup", "arguments": '{"q":'},
                        }
                    ]
                ),
                native_chunk(
                    tool_calls=[
                        {
                            "index": 0,
                            "function": {"arguments": '"value"}'},
                        }
                    ]
                ),
                native_chunk(finish_reason="tool_calls"),
            ]
        )
        chunks = []
        terminals = []

        def factory(_host: str):
            return engine, FakeMessage, FakeRole

        with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):
            with self.assertRaises(UnaryInferenceRejected) as caught:
                execute_stream(
                    request,
                    emit_chunk=chunks.append,
                    emit_terminal=terminals.append,
                    engine_factory=factory,
                    artifact_path=Path("/ignored/Qwen_Qwen3-0.6B-Q4_K_M.gguf"),
                    host="http://127.0.0.1:8080",
                )
        self.assertIn("canonical inference wire", str(caught.exception))
        self.assertEqual(chunks, [])
        self.assertEqual(terminals, [])
        self.assertTrue(engine.closed)

    def test_structured_helper_has_no_execution_primitives(self) -> None:
        path = ROOT / "adapters" / "openjarvis" / "structured_output.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden_import_roots = {"subprocess", "os", "socket", "shlex"}
        forbidden_calls = {"exec", "eval", "system", "Popen"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name.split(".")[0] not in forbidden_import_roots for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn((node.module or "").split(".")[0], forbidden_import_roots)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_calls)
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls)


if __name__ == "__main__":
    unittest.main()
