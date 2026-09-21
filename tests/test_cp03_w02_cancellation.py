from __future__ import annotations

from pathlib import Path
import sys
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GENERATED_SDK = ROOT / "contracts" / "sdk" / "python" / "gen"
if str(GENERATED_SDK) not in sys.path:
    sys.path.insert(0, str(GENERATED_SDK))

from clever.v1 import common_pb2, identity_pb2, inference_pb2

from adapters.openjarvis.sidecar import _InferenceCoordinator
from adapters.openjarvis.streaming_inference import execute_stream
from adapters.openjarvis.unary_inference import PINNED_ENGINE_ID, PINNED_MODEL_ID, UnaryInferenceRejected


def valid_stream_request() -> inference_pb2.InferenceRequest:
    request = inference_pb2.InferenceRequest(
        contract_version=common_pb2.ContractVersion(major=1, minor=2),
        request_id="req-w02-12",
        attempt_id="attempt-w02-12",
        principal=identity_pb2.PrincipalRef(user_id="user-local"),
        session_id="session-local",
        engine_id=PINNED_ENGINE_ID,
        model_id=PINNED_MODEL_ID,
        inputs=[
            inference_pb2.InferenceInput(
                role=inference_pb2.INFERENCE_ROLE_USER,
                content="Cancel this local stream safely.",
            )
        ],
        config=inference_pb2.InferenceConfig(
            max_output_tokens=16,
            temperature=0.0,
            stream=True,
        ),
        idempotency_key="idem-w02-12",
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


def native_chunk(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=text,
        tool_calls=None,
        content_blocks=None,
        tool_results=None,
        finish_reason=None,
        usage=None,
    )


class CancellationExecutionTests(unittest.TestCase):
    def execute(self, cancel_event: threading.Event, *, acknowledge: bool, cancel_after_first: bool):
        request = valid_stream_request()
        engine = FakeEngine([native_chunk("one"), native_chunk("two")])
        chunks = []
        terminals = []
        ack_waits = []

        def factory(_host: str):
            return engine, FakeMessage, FakeRole

        def emit_chunk(chunk) -> None:
            chunks.append(chunk)
            if cancel_after_first and len(chunks) == 1:
                cancel_event.set()

        def wait_for_ack(timeout: float) -> bool:
            ack_waits.append(timeout)
            return acknowledge

        with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):
            execute_stream(
                request,
                emit_chunk=emit_chunk,
                emit_terminal=terminals.append,
                engine_factory=factory,
                artifact_path=Path("/ignored/Qwen_Qwen3-0.6B-Q4_K_M.gguf"),
                host="http://127.0.0.1:8080",
                cancel_requested=cancel_event.is_set,
                wait_for_cancel_ack=wait_for_ack,
            )
        return engine, chunks, terminals, ack_waits

    def test_cancel_before_first_chunk_has_ack_then_cancelled_terminal(self) -> None:
        event = threading.Event()
        event.set()
        engine, chunks, terminals, waits = self.execute(event, acknowledge=True, cancel_after_first=False)
        self.assertEqual(chunks, [])
        self.assertEqual(len(terminals), 1)
        self.assertEqual(terminals[0].finish_reason, inference_pb2.INFERENCE_FINISH_REASON_CANCELLED)
        self.assertEqual(terminals[0].final_sequence, 0)
        self.assertEqual(terminals[0].usage.measurement, inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN)
        self.assertTrue(waits)
        self.assertTrue(engine.closed)

    def test_cancel_during_stream_stops_locally_after_observed_chunk(self) -> None:
        event = threading.Event()
        engine, chunks, terminals, waits = self.execute(event, acknowledge=True, cancel_after_first=True)
        self.assertEqual([chunk.sequence for chunk in chunks], [1])
        self.assertEqual(len(terminals), 1)
        self.assertEqual(terminals[0].finish_reason, inference_pb2.INFERENCE_FINISH_REASON_CANCELLED)
        self.assertEqual(terminals[0].final_sequence, 1)
        self.assertTrue(waits)
        self.assertTrue(engine.closed)

    def test_cancel_without_ack_never_fabricates_cancelled_terminal(self) -> None:
        event = threading.Event()
        event.set()
        request = valid_stream_request()
        engine = FakeEngine([native_chunk("never")])
        terminals = []

        def factory(_host: str):
            return engine, FakeMessage, FakeRole

        with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):
            with self.assertRaises(UnaryInferenceRejected) as caught:
                execute_stream(
                    request,
                    emit_chunk=lambda _chunk: None,
                    emit_terminal=terminals.append,
                    engine_factory=factory,
                    artifact_path=Path("/ignored/Qwen_Qwen3-0.6B-Q4_K_M.gguf"),
                    host="http://127.0.0.1:8080",
                    cancel_requested=event.is_set,
                    wait_for_cancel_ack=lambda _timeout: False,
                )
        self.assertIn("ack", str(caught.exception).lower())
        self.assertEqual(terminals, [])
        self.assertTrue(engine.closed)


class SingleFlightCoordinatorTests(unittest.TestCase):
    def test_single_flight_and_terminal_history_are_explicit(self) -> None:
        coordinator = _InferenceCoordinator()
        first = coordinator.begin("req-1", "attempt-1", "frame-1")
        self.assertIsNotNone(first)
        self.assertIsNone(coordinator.begin("req-2", "attempt-2", "frame-2"))
        status, target = coordinator.request_cancel("req-1", "attempt-1")
        self.assertEqual(status, "REQUESTED")
        self.assertIs(target, first)
        self.assertTrue(first.cancel_requested.is_set())
        first.cancel_acknowledged.set()
        coordinator.complete_cancelled(first)
        status, target = coordinator.request_cancel("req-1", "attempt-1")
        self.assertEqual(status, "ALREADY_TERMINAL")
        self.assertIsNone(target)
        second = coordinator.begin("req-2", "attempt-2", "frame-2")
        self.assertIsNotNone(second)


if __name__ == "__main__":
    unittest.main()
