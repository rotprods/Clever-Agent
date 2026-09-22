from __future__ import annotations

from pathlib import Path
import os
import re
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

from adapters.openjarvis.streaming_inference import execute_stream
from adapters.openjarvis.structured_output import (
    StructuredOutputRejected,
    StructuredStreamAssembler,
    ToolCallAssembler,
    validate_structured_json,
)
from adapters.openjarvis.unary_inference import PINNED_ENGINE_ID, PINNED_MODEL_ID, UnaryInferenceRejected


def valid_stream_request() -> inference_pb2.InferenceRequest:
    request = inference_pb2.InferenceRequest(
        contract_version=common_pb2.ContractVersion(major=1, minor=2),
        request_id="req-w02-13",
        attempt_id="attempt-structured-1",
        principal=identity_pb2.PrincipalRef(user_id="user-local"),
        session_id="session-local",
        engine_id=PINNED_ENGINE_ID,
        model_id=PINNED_MODEL_ID,
        inputs=[
            inference_pb2.InferenceInput(
                role=inference_pb2.INFERENCE_ROLE_USER,
                content="Return structured data only.",
            )
        ],
        config=inference_pb2.InferenceConfig(
            max_output_tokens=64,
            temperature=0.0,
            stream=True,
        ),
        idempotency_key="idem-w02-13",
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


class StructuredOutputUnitTests(unittest.TestCase):
    def test_fragmented_tool_call_is_assembled_without_execution(self) -> None:
        assembler = ToolCallAssembler()
        assembler.feed(
            [
                {
                    "index": 0,
                    "id": "call-1",
                    "function": {"name": "browser.open; rm -rf /", "arguments": '{"url":'},
                }
            ]
        )
        assembler.feed(
            [
                {
                    "index": 0,
                    "function": {"arguments": '"https://example.test"}'},
                }
            ]
        )
        with patch.object(subprocess, "run") as run, patch.object(os, "system") as system:
            calls = assembler.finalize()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].call_id, "call-1")
        self.assertEqual(calls[0].name, "browser.open; rm -rf /")
        self.assertEqual(calls[0].arguments, {"url": "https://example.test"})
        self.assertEqual(len(calls[0].fragments), 2)
        run.assert_not_called()
        system.assert_not_called()

    def test_invalid_fragmented_arguments_fail_closed(self) -> None:
        assembler = ToolCallAssembler()
        assembler.feed(
            [
                {
                    "index": 0,
                    "id": "call-bad",
                    "function": {"name": "calc", "arguments": '{"x":'},
                }
            ]
        )
        assembler.feed([{"index": 0, "function": {"arguments": "nope}"}}])
        with self.assertRaises(StructuredOutputRejected):
            assembler.finalize()

    def test_conflicting_tool_identity_is_rejected(self) -> None:
        assembler = ToolCallAssembler()
        assembler.feed([{"index": 0, "id": "call-a", "function": {"name": "calc", "arguments": "{"}}])
        with self.assertRaises(StructuredOutputRejected):
            assembler.feed([{"index": 0, "id": "call-b", "function": {"arguments": "}"}}])

    def test_structured_json_validates_draft_2020_12_schema(self) -> None:
        schema = {
            "type": "object",
            "required": ["answer"],
            "additionalProperties": False,
            "properties": {"answer": {"type": "integer", "minimum": 0}},
        }
        self.assertEqual(validate_structured_json('{"answer":42}', schema), {"answer": 42})
        with self.assertRaises(StructuredOutputRejected):
            validate_structured_json('{"answer":"42"}', schema)
        with self.assertRaises(StructuredOutputRejected):
            validate_structured_json('{"answer":', schema)

    def test_stream_assembler_combines_text_and_inert_tool_data(self) -> None:
        assembler = StructuredStreamAssembler()
        assembler.feed_text('{"answer":')
        assembler.feed_text("42}")
        assembler.feed_tool_calls(
            [
                {
                    "index": 0,
                    "id": "call-1",
                    "function": {"name": "lookup", "arguments": '{"q":"x"}'},
                }
            ]
        )
        value, calls = assembler.finalize(
            response_schema={
                "type": "object",
                "required": ["answer"],
                "properties": {"answer": {"type": "integer"}},
            }
        )
        self.assertEqual(value, {"answer": 42})
        self.assertEqual(calls[0].name, "lookup")

    def test_canonical_transport_contract_is_explicit_not_metadata(self) -> None:
        inference = (ROOT / "contracts/proto/clever/v1/inference.proto").read_text()
        adapter = (ROOT / "contracts/proto/clever/v1/adapter.proto").read_text()
        self.assertRegex(inference, r"optional\s+string\s+response_schema_json\s*=\s*12;")
        self.assertRegex(inference, r"\bmessage\s+InferenceToolCall\b")
        self.assertRegex(inference, r"\bmessage\s+InferenceStructuredOutput\b")
        self.assertRegex(adapter, r"\binference_tool_call\s*=\s*25;")
        self.assertRegex(adapter, r"\binference_structured_output\s*=\s*26;")
        self.assertIsNone(re.search(r"metadata.*(tool|structured)|(?:tool|structured).*metadata", inference, re.I | re.S))


class StreamingStructuredIntegrationTests(unittest.TestCase):
    def execute(self, chunks, **kwargs):
        request = valid_stream_request()
        engine = FakeEngine(chunks)
        text_chunks = []
        terminals = []
        tool_calls = []
        structured = []

        def factory(_host: str):
            return engine, FakeMessage, FakeRole

        with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):
            execute_stream(
                request,
                emit_chunk=text_chunks.append,
                emit_terminal=terminals.append,
                emit_tool_call=tool_calls.append,
                emit_structured_output=structured.append if kwargs.get("response_schema") else None,
                response_schema=kwargs.get("response_schema"),
                engine_factory=factory,
                artifact_path=Path("/ignored/Qwen_Qwen3-0.6B-Q4_K_M.gguf"),
                host="http://127.0.0.1:8080",
            )
        return engine, text_chunks, terminals, tool_calls, structured

    def test_fragmented_tool_call_reaches_typed_data_sink_and_never_executes(self) -> None:
        chunks = [
            SimpleNamespace(
                content=None,
                tool_calls=[
                    {
                        "index": 0,
                        "id": "call-1",
                        "function": {"name": "shell.exec", "arguments": '{"cmd":'},
                    }
                ],
                content_blocks=None,
                tool_results=None,
                finish_reason=None,
                usage=None,
            ),
            SimpleNamespace(
                content=None,
                tool_calls=[{"index": 0, "function": {"arguments": '"echo owned"}'}}],
                content_blocks=None,
                tool_results=None,
                finish_reason="tool_calls",
                usage=None,
            ),
        ]
        with patch.object(subprocess, "run") as run, patch.object(os, "system") as system:
            engine, text, terminals, calls, structured = self.execute(chunks)
        self.assertTrue(engine.closed)
        self.assertEqual(text, [])
        self.assertEqual(structured, [])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "shell.exec")
        self.assertEqual(calls[0].arguments, {"cmd": "echo owned"})
        self.assertEqual(len(terminals), 1)
        self.assertEqual(terminals[0].final_sequence, 0)
        self.assertEqual(terminals[0].finish_reason, inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL)
        run.assert_not_called()
        system.assert_not_called()

    def test_structured_json_is_validated_before_typed_sink(self) -> None:
        schema = {
            "type": "object",
            "required": ["answer"],
            "additionalProperties": False,
            "properties": {"answer": {"type": "integer"}},
        }
        engine, text, terminals, calls, structured = self.execute(
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
            response_schema=schema,
        )
        self.assertTrue(engine.closed)
        self.assertEqual("".join(chunk.text_delta for chunk in text), '{"answer":42}')
        self.assertEqual(calls, [])
        self.assertEqual(structured, [{"answer": 42}])
        self.assertEqual(len(terminals), 1)

    def test_invalid_structured_json_never_emits_structured_or_terminal_success(self) -> None:
        request = valid_stream_request()
        engine = FakeEngine(
            [
                SimpleNamespace(
                    content='{\"answer\":\"wrong\"}',
                    tool_calls=None,
                    content_blocks=None,
                    tool_results=None,
                    finish_reason="stop",
                    usage=None,
                )
            ]
        )
        text_chunks = []
        terminals = []
        structured = []

        def factory(_host: str):
            return engine, FakeMessage, FakeRole

        with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):
            with self.assertRaises(UnaryInferenceRejected):
                execute_stream(
                    request,
                    emit_chunk=text_chunks.append,
                    emit_terminal=terminals.append,
                    emit_tool_call=lambda _call: self.fail("unexpected tool call"),
                    emit_structured_output=structured.append,
                    response_schema={
                        "type": "object",
                        "required": ["answer"],
                        "properties": {"answer": {"type": "integer"}},
                    },
                    engine_factory=factory,
                    artifact_path=Path("/ignored/Qwen_Qwen3-0.6B-Q4_K_M.gguf"),
                    host="http://127.0.0.1:8080",
                )
        self.assertEqual(structured, [])
        self.assertEqual(terminals, [])
        self.assertTrue(engine.closed)

    def test_tool_fragments_without_typed_sink_still_fail_closed(self) -> None:
        request = valid_stream_request()
        engine = FakeEngine(
            [
                SimpleNamespace(
                    content=None,
                    tool_calls=[{"index": 0, "id": "call-1", "function": {"name": "x", "arguments": "{}"}}],
                    content_blocks=None,
                    tool_results=None,
                    finish_reason="tool_calls",
                    usage=None,
                )
            ]
        )

        def factory(_host: str):
            return engine, FakeMessage, FakeRole

        with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):
            with self.assertRaises(UnaryInferenceRejected) as caught:
                execute_stream(
                    request,
                    emit_chunk=lambda _chunk: None,
                    emit_terminal=lambda _terminal: None,
                    engine_factory=factory,
                    artifact_path=Path("/ignored/Qwen_Qwen3-0.6B-Q4_K_M.gguf"),
                    host="http://127.0.0.1:8080",
                )
        self.assertIn("W02-13", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
