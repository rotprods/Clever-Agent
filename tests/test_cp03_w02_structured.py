from __future__ import annotations

import inspect
import unittest

from adapters.openjarvis.structured_inference import (
    StructuredInferenceError,
    ToolCallData,
    assemble_structured_json,
    assemble_tool_call_fragments,
)


WEATHER_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["city", "unit"],
    "properties": {
        "city": {"type": "string", "minLength": 1},
        "unit": {"enum": ["c", "f"]},
    },
}


class StructuredOutputTests(unittest.TestCase):
    def test_fragmented_structured_json_is_assembled_and_schema_validated(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["answer", "confidence"],
            "properties": {
                "answer": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
        }
        value = assemble_structured_json(
            ['{"answer":"hel', 'lo","confidence":', '0.75}'], schema=schema
        )
        self.assertEqual(value, {"answer": "hello", "confidence": 0.75})

    def test_invalid_json_and_duplicate_keys_fail_closed(self) -> None:
        with self.assertRaisesRegex(StructuredInferenceError, "invalid JSON"):
            assemble_structured_json(['{"x":'], schema={"type": "object"})
        with self.assertRaisesRegex(StructuredInferenceError, "duplicate JSON object key"):
            assemble_structured_json(['{"x":1,"x":2}'], schema={"type": "object"})

    def test_non_finite_and_schema_violation_fail_closed(self) -> None:
        with self.assertRaisesRegex(StructuredInferenceError, "non-finite JSON constant"):
            assemble_structured_json(["NaN"], schema={})
        with self.assertRaisesRegex(StructuredInferenceError, "schema validation failed"):
            assemble_structured_json(
                ['{"answer":7}'],
                schema={
                    "type": "object",
                    "required": ["answer"],
                    "properties": {"answer": {"type": "string"}},
                },
            )

    def test_structured_byte_budget_is_enforced_before_decode(self) -> None:
        with self.assertRaisesRegex(StructuredInferenceError, "exceeds byte budget"):
            assemble_structured_json(['{"x":"12345"}'], schema={}, max_bytes=8)


class ToolFragmentTests(unittest.TestCase):
    def test_fragmented_arguments_are_assembled_as_inert_typed_data(self) -> None:
        fragments = [
            {"index": 0, "id": "call-weather", "function": {"name": "weather", "arguments": '{"city":"Ma'}},
            {"index": 0, "function": {"arguments": 'drid","unit":"'}},
            {"index": 0, "function": {"arguments": 'c"}'}},
        ]
        calls = assemble_tool_call_fragments(
            fragments, schemas_by_name={"weather": WEATHER_SCHEMA}
        )
        self.assertEqual(
            calls,
            (
                ToolCallData(
                    index=0,
                    call_id="call-weather",
                    name="weather",
                    arguments={"city": "Madrid", "unit": "c"},
                ),
            ),
        )

    def test_tool_identity_mutation_and_undeclared_tool_fail_closed(self) -> None:
        with self.assertRaisesRegex(StructuredInferenceError, "changed name mid-stream"):
            assemble_tool_call_fragments(
                [
                    {"index": 0, "id": "a", "function": {"name": "weather", "arguments": "{"}},
                    {"index": 0, "function": {"name": "shell", "arguments": "}"}},
                ],
                schemas_by_name={"weather": WEATHER_SCHEMA, "shell": {}},
            )
        with self.assertRaisesRegex(StructuredInferenceError, "undeclared tool"):
            assemble_tool_call_fragments(
                [
                    {
                        "index": 0,
                        "id": "a",
                        "function": {"name": "shell", "arguments": '{"cmd":"rm -rf /"}'},
                    }
                ],
                schemas_by_name={"weather": WEATHER_SCHEMA},
            )

    def test_invalid_fragmented_arguments_and_schema_violation_fail_closed(self) -> None:
        with self.assertRaisesRegex(StructuredInferenceError, "invalid JSON"):
            assemble_tool_call_fragments(
                [
                    {
                        "index": 0,
                        "id": "a",
                        "function": {"name": "weather", "arguments": '{"city":"Madrid"'},
                    }
                ],
                schemas_by_name={"weather": WEATHER_SCHEMA},
            )
        with self.assertRaisesRegex(StructuredInferenceError, "schema validation failed"):
            assemble_tool_call_fragments(
                [
                    {
                        "index": 0,
                        "id": "a",
                        "function": {"name": "weather", "arguments": '{"city":"Madrid","unit":"kelvin"}'},
                    }
                ],
                schemas_by_name={"weather": WEATHER_SCHEMA},
            )

    def test_argument_budget_is_enforced_and_no_execution_surface_exists(self) -> None:
        with self.assertRaisesRegex(StructuredInferenceError, "exceed byte budget"):
            assemble_tool_call_fragments(
                [
                    {
                        "index": 0,
                        "id": "a",
                        "function": {"name": "weather", "arguments": '{"city":"Madrid","unit":"c"}'},
                    }
                ],
                schemas_by_name={"weather": WEATHER_SCHEMA},
                max_argument_bytes=8,
            )

        source = inspect.getsource(__import__("adapters.openjarvis.structured_inference", fromlist=["*"]))
        forbidden = (
            "subprocess",
            "os.system",
            "socket.",
            "httpx",
            "requests.",
            "browser",
            "mcp",
            "exec(",
            "eval(",
        )
        for token in forbidden:
            self.assertNotIn(token, source.lower())

        malicious = assemble_tool_call_fragments(
            [
                {
                    "index": 0,
                    "id": "call-data-only",
                    "function": {
                        "name": "weather",
                        "arguments": '{"city":"$(touch /tmp/should-not-exist)","unit":"c"}',
                    },
                }
            ],
            schemas_by_name={"weather": WEATHER_SCHEMA},
        )
        self.assertEqual(malicious[0].arguments["city"], "$(touch /tmp/should-not-exist)")


if __name__ == "__main__":
    unittest.main()
