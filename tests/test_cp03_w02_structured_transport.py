from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from adapters.openjarvis.structured_output import ToolCallData
from adapters.openjarvis.unary_inference import UnaryInferenceRejected
from clever.v1 import adapter_pb2, common_pb2, inference_pb2


ROOT = Path(__file__).resolve().parents[1]


class StructuredTransportContractTests(unittest.TestCase):
    def _request(self, *, response_schema_json: str = "") -> inference_pb2.InferenceRequest:
        request = inference_pb2.InferenceRequest(
            contract_version=common_pb2.ContractVersion(major=1, minor=2),
            request_id="req-structured-transport",
            attempt_id="att-structured-transport",
            session_id="session-structured-transport",
            engine_id="llamacpp",
            model_id="qwen3:0.6b",
            idempotency_key="idem-structured-transport",
        )
        if response_schema_json:
            request.response_schema_json = response_schema_json
        return request

    def _request_frame(self, *, response_schema_json: str = "") -> adapter_pb2.AdapterFrame:
        return adapter_pb2.AdapterFrame(
            contract_version=common_pb2.ContractVersion(major=1, minor=1),
            frame_id="frame-structured-transport",
            inference_request=self._request(response_schema_json=response_schema_json),
        )

    def test_proto_has_explicit_typed_transport_without_metadata_encoding(self) -> None:
        inference = (ROOT / "contracts/proto/clever/v1/inference.proto").read_text()
        adapter = (ROOT / "contracts/proto/clever/v1/adapter.proto").read_text()
        self.assertRegex(inference, r"optional\s+string\s+response_schema_json\s*=\s*12;")
        self.assertRegex(inference, r"\bmessage\s+InferenceToolCall\b")
        self.assertRegex(inference, r"\bmessage\s+InferenceStructuredOutput\b")
        self.assertRegex(adapter, r"\binference_tool_call\s*=\s*25;")
        self.assertRegex(adapter, r"\binference_structured_output\s*=\s*26;")
        self.assertIsNone(re.search(r"(?mi)^\s*(?:optional\s+)?(?:string|bytes|map<[^>]+>)\s+\w*metadata\w*\s*=", inference))

    def test_generated_bindings_expose_typed_transport_messages(self) -> None:
        self.assertTrue(hasattr(inference_pb2.InferenceRequest(), "response_schema_json"))
        self.assertTrue(hasattr(inference_pb2, "InferenceToolCall"))
        self.assertTrue(hasattr(inference_pb2, "InferenceStructuredOutput"))
        frame = adapter_pb2.AdapterFrame()
        self.assertTrue(hasattr(frame, "inference_tool_call"))
        self.assertTrue(hasattr(frame, "inference_structured_output"))

    def test_sidecar_parses_only_caller_supplied_object_schema(self) -> None:
        from adapters.openjarvis.sidecar import _response_schema

        schema = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}
        request = self._request(response_schema_json=json.dumps(schema))
        self.assertEqual(schema, _response_schema(request))
        self.assertIsNone(_response_schema(self._request()))

        with self.assertRaises(UnaryInferenceRejected):
            _response_schema(self._request(response_schema_json="not-json"))
        with self.assertRaises(UnaryInferenceRejected):
            _response_schema(self._request(response_schema_json='["not", "an", "object"]'))

    def test_sidecar_emits_tool_call_as_correlated_inert_adapter_frame(self) -> None:
        from adapters.openjarvis.sidecar import _tool_call_frame

        request = self._request_frame()
        call = ToolCallData(
            index=0,
            call_id="call-1",
            name="definitely_not_a_real_executable_tool",
            arguments_json='{"path":"/tmp/never-executed"}',
            arguments={"path": "/tmp/never-executed"},
            fragments=(),
        )
        frame = _tool_call_frame(request, call)
        self.assertEqual("inference_tool_call", frame.WhichOneof("body"))
        self.assertEqual(request.frame_id, frame.correlation_id)
        body = frame.inference_tool_call
        self.assertEqual(request.inference_request.request_id, body.request_id)
        self.assertEqual(request.inference_request.attempt_id, body.attempt_id)
        self.assertEqual(0, body.index)
        self.assertEqual("call-1", body.call_id)
        self.assertEqual("definitely_not_a_real_executable_tool", body.name)
        self.assertEqual(call.arguments_json, body.arguments_json)

    def test_sidecar_emits_validated_structured_value_as_typed_json_data(self) -> None:
        from adapters.openjarvis.sidecar import _structured_output_frame

        request = self._request_frame(response_schema_json='{"type":"object"}')
        frame = _structured_output_frame(request, {"answer": "ok", "count": 2})
        self.assertEqual("inference_structured_output", frame.WhichOneof("body"))
        self.assertEqual(request.frame_id, frame.correlation_id)
        body = frame.inference_structured_output
        self.assertEqual(request.inference_request.request_id, body.request_id)
        self.assertEqual(request.inference_request.attempt_id, body.attempt_id)
        self.assertEqual({"answer": "ok", "count": 2}, json.loads(body.json_value))


if __name__ == "__main__":
    unittest.main()
