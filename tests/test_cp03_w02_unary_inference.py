from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from clever.v1 import common_pb2, identity_pb2, inference_pb2

from adapters.openjarvis.unary_inference import (
    PINNED_ENGINE_ID,
    PINNED_MODEL_ID,
    UnaryInferenceRejected,
    execute_unary,
    validate_unary_request,
)


def valid_request() -> inference_pb2.InferenceRequest:
    request = inference_pb2.InferenceRequest(
        contract_version=common_pb2.ContractVersion(major=1, minor=2),
        request_id="req-w02-10",
        attempt_id="attempt-1",
        principal=identity_pb2.PrincipalRef(user_id="user-local"),
        session_id="session-local",
        engine_id=PINNED_ENGINE_ID,
        model_id=PINNED_MODEL_ID,
        inputs=[
            inference_pb2.InferenceInput(
                role=inference_pb2.INFERENCE_ROLE_USER,
                content="Reply with the single word READY.",
            )
        ],
        config=inference_pb2.InferenceConfig(max_output_tokens=16, temperature=0.0, stream=False),
        idempotency_key="idem-w02-10",
    )
    deadline_ns = time.time_ns() + 60_000_000_000
    request.deadline_at.seconds = deadline_ns // 1_000_000_000
    request.deadline_at.nanos = deadline_ns % 1_000_000_000
    return request


class UnaryInferenceValidationTests(unittest.TestCase):
    def test_valid_contract_shape_is_accepted_before_runtime_attestation(self) -> None:
        validate_unary_request(valid_request())

    def test_missing_inputs_rejected_before_engine_creation(self) -> None:
        request = valid_request()
        request.ClearField("inputs")
        calls = 0

        def factory(_host: str):
            nonlocal calls
            calls += 1
            raise AssertionError("engine factory must not be reached")

        with self.assertRaises(UnaryInferenceRejected) as caught:
            execute_unary(
                request,
                engine_factory=factory,
                artifact_path=Path("/definitely/missing.gguf"),
                host="http://127.0.0.1:8080",
            )
        self.assertEqual(caught.exception.code, inference_pb2.INFERENCE_ERROR_CODE_INVALID_REQUEST)
        self.assertEqual(calls, 0)

    def test_unapproved_model_rejected_before_engine_creation(self) -> None:
        request = valid_request()
        request.model_id = "floating:model"
        calls = 0

        def factory(_host: str):
            nonlocal calls
            calls += 1
            raise AssertionError("engine factory must not be reached")

        with self.assertRaises(UnaryInferenceRejected) as caught:
            execute_unary(
                request,
                engine_factory=factory,
                artifact_path=Path("/definitely/missing.gguf"),
                host="http://127.0.0.1:8080",
            )
        self.assertEqual(caught.exception.code, inference_pb2.INFERENCE_ERROR_CODE_MODEL_UNAVAILABLE)
        self.assertEqual(calls, 0)

    def test_streaming_is_explicitly_deferred_to_w02_11(self) -> None:
        request = valid_request()
        request.config.stream = True
        with self.assertRaises(UnaryInferenceRejected) as caught:
            validate_unary_request(request)
        self.assertEqual(caught.exception.code, inference_pb2.INFERENCE_ERROR_CODE_INVALID_REQUEST)
        self.assertIn("W02-11", str(caught.exception))

    def test_expired_deadline_rejected(self) -> None:
        request = valid_request()
        request.deadline_at.seconds = 1
        request.deadline_at.nanos = 0
        with self.assertRaises(UnaryInferenceRejected) as caught:
            validate_unary_request(request)
        self.assertEqual(caught.exception.code, inference_pb2.INFERENCE_ERROR_CODE_DEADLINE_EXCEEDED)

    def test_missing_real_weights_is_blocked_before_engine_creation(self) -> None:
        request = valid_request()
        calls = 0

        def factory(_host: str):
            nonlocal calls
            calls += 1
            raise AssertionError("engine factory must not be reached")

        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "Qwen_Qwen3-0.6B-Q4_K_M.gguf"
            with self.assertRaises(UnaryInferenceRejected) as caught:
                execute_unary(
                    request,
                    engine_factory=factory,
                    artifact_path=missing,
                    host="http://127.0.0.1:8080",
                )
        self.assertEqual(caught.exception.code, inference_pb2.INFERENCE_ERROR_CODE_MODEL_UNAVAILABLE)
        self.assertEqual(calls, 0)


if __name__ == "__main__":
    unittest.main()
