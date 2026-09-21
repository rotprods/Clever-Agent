from __future__ import annotations

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

from clever.v1 import common_pb2, identity_pb2, inference_pb2

from adapters.openjarvis.streaming_inference import (
    execute_stream,
    validate_stream_request,
)
from adapters.openjarvis.unary_inference import (
    PINNED_ENGINE_ID,
    PINNED_MODEL_ID,
    UnaryInferenceRejected,
)


def valid_stream_request() -> inference_pb2.InferenceRequest:
    request = inference_pb2.InferenceRequest(
        contract_version=common_pb2.ContractVersion(major=1, minor=2),
        request_id="req-w02-11",
        attempt_id="attempt-1",
        principal=identity_pb2.PrincipalRef(user_id="user-local"),
        session_id="session-local",
        engine_id=PINNED_ENGINE_ID,
        model_id=PINNED_MODEL_ID,
        inputs=[
            inference_pb2.InferenceInput(
                role=inference_pb2.INFERENCE_ROLE_USER,
                content="Stream a short UTF-8 response.",
            )
        ],
        config=inference_pb2.InferenceConfig(
            max_output_tokens=16,
            temperature=0.0,
            stream=True,
        ),
        idempotency_key="idem-w02-11",
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
        self.kwargs = None

    async def stream_full(self, _messages, **kwargs):
        self.kwargs = kwargs
        for chunk in self.chunks:
            yield chunk

    def close(self) -> None:
        self.closed = True


class StreamingInferenceTests(unittest.TestCase):
    def execute(self, chunks):
        request = valid_stream_request()
        engine = FakeEngine(chunks)
        emitted_chunks = []
        terminals = []

        def factory(_host: str):
            return engine, FakeMessage, FakeRole

        with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):
            execute_stream(
                request,
                emit_chunk=emitted_chunks.append,
                emit_terminal=terminals.append,
                engine_factory=factory,
                artifact_path=Path("/ignored/Qwen_Qwen3-0.6B-Q4_K_M.gguf"),
                host="http://127.0.0.1:8080",
            )
        return request, engine, emitted_chunks, terminals

    def test_native_stream_full_emits_ordered_utf8_chunks_and_one_terminal(self) -> None:
        request, engine, chunks, terminals = self.execute(
            [
                SimpleNamespace(
                    content="hé",
                    tool_calls=None,
                    content_blocks=None,
                    tool_results=None,
                    finish_reason=None,
                    usage=None,
                ),
                SimpleNamespace(
                    content="llo",
                    tool_calls=None,
                    content_blocks=None,
                    tool_results=None,
                    finish_reason=None,
                    usage=None,
                ),
                SimpleNamespace(
                    content=None,
                    tool_calls=None,
                    content_blocks=None,
                    tool_results=None,
                    finish_reason="stop",
                    usage={
                        "prompt_tokens": 7,
                        "completion_tokens": 2,
                        "total_tokens": 9,
                    },
                ),
            ]
        )
        self.assertEqual([chunk.sequence for chunk in chunks], [1, 2])
        self.assertEqual("".join(chunk.text_delta for chunk in chunks), "héllo")
        self.assertEqual(len(terminals), 1)
        terminal = terminals[0]
        self.assertEqual(terminal.request_id, request.request_id)
        self.assertEqual(terminal.attempt_id, request.attempt_id)
        self.assertEqual(terminal.final_sequence, 2)
        self.assertEqual(terminal.finish_reason, inference_pb2.INFERENCE_FINISH_REASON_STOP)
        self.assertEqual(
            terminal.usage.measurement,
            inference_pb2.INFERENCE_USAGE_MEASUREMENT_EXACT,
        )
        self.assertEqual(terminal.usage.total_tokens, 9)
        self.assertEqual(engine.kwargs["chat_template_kwargs"], {"enable_thinking": False})
        self.assertTrue(engine.closed)

    def test_missing_native_usage_is_explicit_unknown_not_fabricated(self) -> None:
        _, _, chunks, terminals = self.execute(
            [
                SimpleNamespace(
                    content="ok",
                    tool_calls=None,
                    content_blocks=None,
                    tool_results=None,
                    finish_reason=None,
                    usage=None,
                )
            ]
        )
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(terminals), 1)
        self.assertEqual(
            terminals[0].usage.measurement,
            inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN,
        )
        self.assertEqual(
            terminals[0].finish_reason,
            inference_pb2.INFERENCE_FINISH_REASON_UNSPECIFIED,
        )
        self.assertFalse(terminals[0].usage.HasField("input_tokens"))
        self.assertFalse(terminals[0].usage.HasField("output_tokens"))
        self.assertFalse(terminals[0].usage.HasField("total_tokens"))

    def test_empty_eof_never_emits_terminal_or_false_success(self) -> None:
        request = valid_stream_request()
        engine = FakeEngine([])
        emitted_chunks = []
        terminals = []

        def factory(_host: str):
            return engine, FakeMessage, FakeRole

        with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):
            with self.assertRaises(UnaryInferenceRejected) as caught:
                execute_stream(
                    request,
                    emit_chunk=emitted_chunks.append,
                    emit_terminal=terminals.append,
                    engine_factory=factory,
                    artifact_path=Path("/ignored/Qwen_Qwen3-0.6B-Q4_K_M.gguf"),
                    host="http://127.0.0.1:8080",
                )
        self.assertEqual(caught.exception.code, inference_pb2.INFERENCE_ERROR_CODE_INTERNAL)
        self.assertEqual(emitted_chunks, [])
        self.assertEqual(terminals, [])
        self.assertTrue(engine.closed)

    def test_tool_fragments_fail_closed_until_w02_13(self) -> None:
        request = valid_stream_request()
        engine = FakeEngine(
            [
                SimpleNamespace(
                    content=None,
                    tool_calls=[{"id": "not-executed"}],
                    content_blocks=None,
                    tool_results=None,
                    finish_reason=None,
                    usage=None,
                )
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
        self.assertIn("W02-13", str(caught.exception))
        self.assertEqual(chunks, [])
        self.assertEqual(terminals, [])

    def test_stream_false_rejected_before_engine(self) -> None:
        request = valid_stream_request()
        request.config.stream = False
        with self.assertRaises(UnaryInferenceRejected):
            validate_stream_request(request)


if __name__ == "__main__":
    unittest.main()
