from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from scripts.contracts.versioning import UnsupportedContractVersion, require_supported_mapping


ROOT = Path(__file__).resolve().parents[1]


class InferenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads((ROOT / "contracts/jsonschema/inference.schema.json").read_text())
        cls.fixture = json.loads((ROOT / "contracts/fixtures/inference.json").read_text())
        common = json.loads((ROOT / "contracts/jsonschema/common.schema.json").read_text())
        registry = Registry().with_resources(
            [(common["$id"], Resource.from_contents(common)), (cls.schema["$id"], Resource.from_contents(cls.schema))]
        )
        cls.validator = Draft202012Validator(cls.schema, registry=registry, format_checker=FormatChecker())

    def assert_invalid(self, mutate) -> None:
        value = copy.deepcopy(self.fixture)
        mutate(value)
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_canonical_request_fixture_is_valid_v1_2(self) -> None:
        self.assertEqual([], list(self.validator.iter_errors(self.fixture)))
        self.assertEqual({"major": 1, "minor": 2}, self.fixture["contractVersion"])
        require_supported_mapping(self.fixture)

    def test_identity_attempt_deadline_and_idempotency_are_required(self) -> None:
        for field in ("requestId", "attemptId", "principal", "sessionId", "engineId", "modelId", "deadlineAt", "idempotencyKey"):
            with self.subTest(field=field):
                self.assert_invalid(lambda value, field=field: value.pop(field))

    def test_empty_inputs_and_zero_output_budget_are_rejected(self) -> None:
        self.assert_invalid(lambda value: value.__setitem__("inputs", []))
        self.assert_invalid(lambda value: value["config"].__setitem__("maxOutputTokens", "0"))

    def test_unknown_role_and_arbitrary_authority_fields_are_rejected(self) -> None:
        self.assert_invalid(lambda value: value["inputs"][0].__setitem__("role", "ROOT"))
        self.assert_invalid(lambda value: value.__setitem__("policyGrant", "self-approved"))

    def test_unknown_major_still_fails_closed(self) -> None:
        value = copy.deepcopy(self.fixture)
        value["contractVersion"]["major"] = 2
        with self.assertRaises(UnsupportedContractVersion):
            require_supported_mapping(value)
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_proto_defines_minimal_messages_without_authority_fields(self) -> None:
        inference = (ROOT / "contracts/proto/clever/v1/inference.proto").read_text()
        for name in ("InferenceRequest", "InferenceChunk", "InferenceTerminal", "InferenceError", "InferenceCancel", "InferenceUsage"):
            self.assertRegex(inference, rf"\bmessage\s+{name}\b")
        for field in ("request_id", "attempt_id", "principal", "session_id", "engine_id", "model_id", "deadline_at", "idempotency_key", "sequence", "finish_reason"):
            self.assertRegex(inference, rf"\b{field}\b")
        self.assertIsNone(re.search(r"\b(policy_grant|verified_parity|egress_grant|budget_grant)\b", inference.lower()))

    def test_adapter_extension_is_additive_and_uses_new_field_numbers(self) -> None:
        adapter = (ROOT / "contracts/proto/clever/v1/adapter.proto").read_text()
        expected = {
            "inference_request": 20,
            "inference_chunk": 21,
            "inference_terminal": 22,
            "inference_error": 23,
            "inference_cancel": 24,
        }
        for field, number in expected.items():
            self.assertRegex(adapter, rf"\b{field}\s*=\s*{number};")


if __name__ == "__main__":
    unittest.main()
