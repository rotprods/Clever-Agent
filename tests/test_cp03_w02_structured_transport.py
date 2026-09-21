from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GENERATED_SDK = ROOT / "contracts" / "sdk" / "python" / "gen"
if str(GENERATED_SDK) not in sys.path:
    sys.path.insert(0, str(GENERATED_SDK))

from clever.v1 import adapter_pb2, common_pb2, identity_pb2, inference_pb2

from adapters.openjarvis.sidecar import read_frame, write_frame
from adapters.openjarvis.streaming_inference import execute_stream
from adapters.openjarvis.unary_inference import PINNED_ENGINE_ID, PINNED_MODEL_ID, UnaryInferenceRejected


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


def request(*, response_schema: dict | None = None) -> inference_pb2.InferenceRequest:
    config_kwargs = {
        "max_output_tokens": 64,
        "temperature": 0.0,
        "stream": True,
    }
    if response_schema is not None:
        config_kwargs["response_schema_json"] = json.dumps(
            response_schema,
            sort_keys=True,
            separators=(",", ":"),
        )
    value = inference_pb2.InferenceRequest(
        contract_version=common_pb2.ContractVersion(major=1, minor=2),
        request_id="req-w02-13-transport",
        attempt_id="attempt-w02-13-transport",
        principal=identity_pb2.PrincipalRef(user_id="user-local"),
        session_id="session-local",
        engine_id=PINNED_ENGINE_ID,
        model_id=PINNED_MODEL_ID,
        inputs=[
            inference_pb2.InferenceInput(
                role=inference_pb2.INFERENCE_ROLE_USER,
                content="Return the requested typed data.",
            )
        ],
        config=inference_pb2.InferenceConfig(**config_kwargs),
        idempotency_key="idem-w02-13-transport",
    )
    deadline_ns = time.time_ns() + 60_000_000_000
    value.deadline_at.seconds = deadline_ns // 1_000_000_000
    value.deadline_at.nanos = deadline_ns % 1_000_000_000
    return value


def execute(value: inference_pb2.InferenceRequest, chunks):
    engine = FakeEngine(chunks)
    text_chunks = []
    terminals = []

    def factory(_host: str):
        return engine, FakeMessage, FakeRole

    with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):
        execute_stream(
            value,
            emit_chunk=text_chunks.append,
            emit_terminal=terminals.append,
            engine_factory=factory,
            artifact_path=Path("/ignored/Qwen_Qwen3-0.6B-Q4_K_M.gguf"),
            host="http://127.0.0.1:8080",
        )
    return engine, text_chunks, terminals


class StructuredTransportTests(unittest.TestCase):
    def test_fragmented_tool_call_crosses_adapter_frame_as_inert_typed_data(self) -> None:
        engine, text, terminals = execute(
            request(),
            [
                SimpleNamespace(
                    content=None,
                    tool_calls=[{
                        "index": 0,
                        "id": "call-transport-1",
                        "function": {"name": "shell.exec", "arguments": '{"cmd":'},
                    }],
                    content_blocks=None,
                    tool_results=None,
                    finish_reason=None,
                    usage=None,
                ),
                SimpleNamespace(
                    content=None,
                    tool_calls=[{
                        "index": 0,
                        "function": {"arguments": '"echo never-execute"}'},
                    }],
                    content_blocks=None,
                    tool_results=None,
                    finish_reason="tool_calls",
                    usage=None,
                ),
            ],
        )
        self.assertTrue(engine.closed)
        self.assertEqual(text, [])
        self.assertEqual(len(terminals), 1)
        terminal = terminals[0]
        self.assertEqual(terminal.final_sequence, 0)
        self.assertEqual(terminal.finish_reason, inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL)
        self.assertEqual(len(terminal.tool_calls), 1)
        self.assertEqual(terminal.tool_calls[0].index, 0)
        self.assertEqual(terminal.tool_calls[0].call_id, "call-transport-1")
        self.assertEqual(terminal.tool_calls[0].name, "shell.exec")
        self.assertEqual(terminal.tool_calls[0].arguments_json, '{"cmd":"echo never-execute"}')

        frame = adapter_pb2.AdapterFrame(
            contract_version=common_pb2.ContractVersion(major=1, minor=2),
            frame_id="typed-terminal-frame",
            correlation_id="request-frame",
            inference_terminal=terminal,
        )
        wire = BytesIO()
        write_frame(wire, frame)
        wire.seek(0)
        decoded = read_frame(wire)
        assert decoded is not None
        self.assertEqual(decoded.WhichOneof("body"), "inference_terminal")
        self.assertEqual(decoded.inference_terminal.tool_calls[0].name, "shell.exec")
        self.assertEqual(decoded.inference_terminal.tool_calls[0].arguments_json, '{"cmd":"echo never-execute"}')

    def test_validated_structured_output_crosses_terminal_as_canonical_json(self) -> None:
        schema = {
            "type": "object",
            "required": ["answer"],
            "additionalProperties": False,
            "properties": {"answer": {"type": "integer"}},
        }
        engine, text, terminals = execute(
            request(response_schema=schema),
            [
                SimpleNamespace(
                    content='{\"answer\":',
                    tool_calls=None,
                    content_blocks=None,
                    tool_results=None,
                    finish_reason=None,
                    usage=None,
                ),
                SimpleNamespace(
                    content="42}",
                    tool_calls=None,
                    content_blocks=None,
                    tool_results=None,
                    finish_reason="stop",
                    usage=None,
                ),
            ],
        )
        self.assertTrue(engine.closed)
        self.assertEqual("".join(chunk.text_delta for chunk in text), '{"answer":42}')
        self.assertEqual(len(terminals), 1)
        terminal = terminals[0]
        self.assertTrue(terminal.HasField("structured_output"))
        self.assertEqual(terminal.structured_output.json_value, '{"answer":42}')
        self.assertEqual(list(terminal.tool_calls), [])

    def test_invalid_caller_schema_fails_before_engine_execution(self) -> None:
        value = request()
        value.config.response_schema_json = "[not-an-object]"
        called = False

        def factory(_host: str):
            nonlocal called
            called = True
            return FakeEngine([]), FakeMessage, FakeRole

        with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):
            with self.assertRaises(UnaryInferenceRejected):
                execute_stream(
                    value,
                    emit_chunk=lambda _chunk: None,
                    emit_terminal=lambda _terminal: None,
                    engine_factory=factory,
                    artifact_path=Path("/ignored/Qwen_Qwen3-0.6B-Q4_K_M.gguf"),
                    host="http://127.0.0.1:8080",
                )
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
