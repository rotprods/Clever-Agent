from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: str, old: str, new: str, label: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one source anchor, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_proto() -> None:
    path = "contracts/proto/clever/v1/inference.proto"
    replace_once(
        path,
        '''message InferenceConfig {\n  uint64 max_output_tokens = 1;\n  optional float temperature = 2;\n  optional float top_p = 3;\n  repeated string stop_sequences = 4;\n  bool stream = 5;\n}\n''',
        '''message InferenceToolDefinition {\n  string name = 1;\n  string arguments_schema_json = 2;\n}\n\nmessage InferenceToolCallFragment {\n  uint64 index = 1;\n  string call_id = 2;\n  string name = 3;\n  string arguments_json_delta = 4;\n}\n\nmessage InferenceConfig {\n  uint64 max_output_tokens = 1;\n  optional float temperature = 2;\n  optional float top_p = 3;\n  repeated string stop_sequences = 4;\n  bool stream = 5;\n  string structured_output_schema_json = 6;\n  repeated InferenceToolDefinition tools = 7;\n}\n''',
        "inference config typed declarations",
    )
    replace_once(
        path,
        '''message InferenceChunk {\n  ContractVersion contract_version = 1;\n  string request_id = 2;\n  string attempt_id = 3;\n  uint64 sequence = 4;\n  string text_delta = 5;\n}\n''',
        '''message InferenceChunk {\n  ContractVersion contract_version = 1;\n  string request_id = 2;\n  string attempt_id = 3;\n  uint64 sequence = 4;\n  string text_delta = 5;\n  string structured_json_delta = 6;\n  repeated InferenceToolCallFragment tool_call_fragments = 7;\n}\n''',
        "inference chunk typed payloads",
    )


def patch_json_schema() -> None:
    path = ROOT / "contracts/jsonschema/inference.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    props = schema["properties"]["config"]["properties"]
    props.setdefault("structuredOutputSchemaJson", {"type": "string", "minLength": 1})
    props.setdefault(
        "tools",
        {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "argumentsSchemaJson"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "argumentsSchemaJson": {"type": "string", "minLength": 2},
                },
            },
        },
    )
    path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def patch_structured_core() -> None:
    replace_once(
        "adapters/openjarvis/structured_inference.py",
        '''def _validate_schema(value: Any, schema: Mapping[str, Any]) -> None:\n''',
        '''def parse_schema_json(payload: str, *, label: str = "JSON schema") -> Mapping[str, Any]:\n    if not isinstance(payload, str) or not payload.strip():\n        raise StructuredInferenceError(f"{label} must be non-empty JSON text")\n    value = _strict_json_loads(payload)\n    if not isinstance(value, dict):\n        raise StructuredInferenceError(f"{label} must decode to an object")\n    try:\n        Draft202012Validator.check_schema(value)\n    except SchemaError as exc:\n        raise StructuredInferenceError(f"invalid {label}: {exc.message}") from exc\n    return value\n\n\ndef _validate_schema(value: Any, schema: Mapping[str, Any]) -> None:\n''',
        "public strict schema parser",
    )


def patch_streaming() -> None:
    path = "adapters/openjarvis/streaming_inference.py"
    replace_once(path, "from typing import Any, Callable\n", "from typing import Any, Callable, Mapping\n", "typing Mapping")
    replace_once(
        path,
        "from clever.v1 import inference_pb2\n\n",
        '''from clever.v1 import inference_pb2\n\nfrom adapters.openjarvis.structured_inference import (\n    StructuredInferenceError,\n    assemble_structured_json,\n    assemble_tool_call_fragments,\n    parse_schema_json,\n)\n\n''',
        "structured imports",
    )
    replace_once(
        path,
        '''    mapping = {\n        "stop": inference_pb2.INFERENCE_FINISH_REASON_STOP,\n        "length": inference_pb2.INFERENCE_FINISH_REASON_LENGTH,\n        "content_filter": inference_pb2.INFERENCE_FINISH_REASON_CONTENT_FILTER,\n    }\n''',
        '''    mapping = {\n        "stop": inference_pb2.INFERENCE_FINISH_REASON_STOP,\n        "length": inference_pb2.INFERENCE_FINISH_REASON_LENGTH,\n        "content_filter": inference_pb2.INFERENCE_FINISH_REASON_CONTENT_FILTER,\n        "tool_call": inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL,\n        "tool_calls": inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL,\n    }\n''',
        "tool finish reason",
    )
    anchor = '''def execute_stream(\n'''
    helper = '''def _structured_contract(\n    request: inference_pb2.InferenceRequest,\n) -> tuple[Mapping[str, Any] | None, dict[str, Mapping[str, Any]]]:\n    config = request.config\n    structured_text = config.structured_output_schema_json.strip()\n    if structured_text and config.tools:\n        raise _reject("structured_output_schema_json and tools are mutually exclusive")\n    structured_schema = (\n        parse_schema_json(structured_text, label="structured output schema")\n        if structured_text\n        else None\n    )\n    tool_schemas: dict[str, Mapping[str, Any]] = {}\n    for index, tool in enumerate(config.tools):\n        name = tool.name.strip()\n        if not name:\n            raise _reject(f"tools[{index}].name must be non-empty")\n        if name in tool_schemas:\n            raise _reject(f"duplicate tool definition: {name}")\n        tool_schemas[name] = parse_schema_json(\n            tool.arguments_schema_json, label=f"tool {name} arguments schema"\n        )\n    return structured_schema, tool_schemas\n\n\n'''
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if helper not in text:
        if text.count(anchor) != 1:
            raise RuntimeError("stream helper anchor mismatch")
        text = text.replace(anchor, helper + anchor, 1)
        target.write_text(text, encoding="utf-8")
    replace_once(
        path,
        '''    validate_stream_request(request)\n    attest_pinned_artifact(artifact_path or _artifact_path())\n''',
        '''    validate_stream_request(request)\n    try:\n        structured_schema, tool_schemas = _structured_contract(request)\n    except StructuredInferenceError as exc:\n        raise _reject(str(exc)) from exc\n    attest_pinned_artifact(artifact_path or _artifact_path())\n''',
        "structured contract validation",
    )
    replace_once(
        path,
        '''            saw_finish = False\n            if cancellation_is_requested():\n''',
        '''            saw_finish = False\n            structured_fragments: list[str] = []\n            tool_fragment_groups: list[list[Mapping[str, Any]]] = []\n            if cancellation_is_requested():\n''',
        "structured accumulators",
    )
    replace_once(
        path,
        '''                if tool_calls or content_blocks or tool_results:\n                    raise UnaryInferenceRejected(\n                        inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,\n                        "typed/tool streaming fragments are deferred to W02-13",\n                        retryable=False,\n                    )\n                if content is not None:\n                    if not isinstance(content, str):\n                        raise UnaryInferenceRejected(\n                            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,\n                            "native streaming content must be text",\n                            retryable=False,\n                        )\n                    if content:\n                        sequence += 1\n                        emit_chunk(\n                            inference_pb2.InferenceChunk(\n                                contract_version=contract_version(),\n                                request_id=request.request_id,\n                                attempt_id=request.attempt_id,\n                                sequence=sequence,\n                                text_delta=content,\n                            )\n                        )\n''',
        '''                if content_blocks or tool_results:\n                    raise UnaryInferenceRejected(\n                        inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,\n                        "content_blocks/tool_results are not an inert W02-13 transport surface",\n                        retryable=False,\n                    )\n                if tool_calls:\n                    if not tool_schemas:\n                        raise UnaryInferenceRejected(\n                            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,\n                            "W02-13 tool fragments require declared tools",\n                            retryable=False,\n                        )\n                    if structured_schema is not None:\n                        raise _reject("native tool calls cannot appear in structured-output mode")\n                    if not isinstance(tool_calls, (list, tuple)) or not all(\n                        isinstance(item, Mapping) for item in tool_calls\n                    ):\n                        raise UnaryInferenceRejected(\n                            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,\n                            "native tool_calls must be a list of mappings",\n                            retryable=False,\n                        )\n                    tool_fragment_groups.append([dict(item) for item in tool_calls])\n                if content is not None:\n                    if not isinstance(content, str):\n                        raise UnaryInferenceRejected(\n                            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,\n                            "native streaming content must be text",\n                            retryable=False,\n                        )\n                    if content:\n                        if tool_schemas:\n                            raise UnaryInferenceRejected(\n                                inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,\n                                "text content cannot be mixed with tool-call mode",\n                                retryable=False,\n                            )\n                        if structured_schema is not None:\n                            structured_fragments.append(content)\n                        else:\n                            sequence += 1\n                            emit_chunk(\n                                inference_pb2.InferenceChunk(\n                                    contract_version=contract_version(),\n                                    request_id=request.request_id,\n                                    attempt_id=request.attempt_id,\n                                    sequence=sequence,\n                                    text_delta=content,\n                                )\n                            )\n''',
        "typed native fragment handling",
    )
    replace_once(
        path,
        '''            if cancellation_is_requested():\n                emit_cancelled(sequence, usage)\n                return\n            if sequence == 0:\n                raise UnaryInferenceRejected(\n                    inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,\n                    "native stream ended without content chunks",\n                    retryable=False,\n                )\n            emit_terminal(\n''',
        '''            if cancellation_is_requested():\n                emit_cancelled(sequence, usage)\n                return\n            try:\n                if structured_schema is not None:\n                    assemble_structured_json(structured_fragments, schema=structured_schema)\n                    for fragment in structured_fragments:\n                        sequence += 1\n                        emit_chunk(\n                            inference_pb2.InferenceChunk(\n                                contract_version=contract_version(),\n                                request_id=request.request_id,\n                                attempt_id=request.attempt_id,\n                                sequence=sequence,\n                                structured_json_delta=fragment,\n                            )\n                        )\n                elif tool_schemas:\n                    flattened = [item for group in tool_fragment_groups for item in group]\n                    assemble_tool_call_fragments(flattened, schemas_by_name=tool_schemas)\n                    for group in tool_fragment_groups:\n                        typed = []\n                        for fragment in group:\n                            function = fragment.get("function") or {}\n                            typed.append(\n                                inference_pb2.InferenceToolCallFragment(\n                                    index=int(fragment.get("index", 0)),\n                                    call_id=str(fragment.get("id") or ""),\n                                    name=str(function.get("name") or ""),\n                                    arguments_json_delta=str(function.get("arguments") or ""),\n                                )\n                            )\n                        sequence += 1\n                        emit_chunk(\n                            inference_pb2.InferenceChunk(\n                                contract_version=contract_version(),\n                                request_id=request.request_id,\n                                attempt_id=request.attempt_id,\n                                sequence=sequence,\n                                tool_call_fragments=typed,\n                            )\n                        )\n            except StructuredInferenceError as exc:\n                raise UnaryInferenceRejected(\n                    inference_pb2.INFERENCE_ERROR_CODE_INVALID_REQUEST,\n                    f"structured/tool output validation failed: {exc}",\n                    retryable=False,\n                ) from exc\n            if sequence == 0:\n                raise UnaryInferenceRejected(\n                    inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,\n                    "native stream ended without canonical chunks",\n                    retryable=False,\n                )\n            if tool_schemas and finish_reason != inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL:\n                raise UnaryInferenceRejected(\n                    inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,\n                    "tool-call stream must terminate with TOOL_CALL finish_reason",\n                    retryable=False,\n                )\n            emit_terminal(\n''',
        "validated canonical typed emission",
    )


def patch_sidecars() -> None:
    for path in (
        "adapters/openjarvis/sidecar.py",
        "kernel/crates/clever-kernel/tests/fixtures/fake_adapter_sidecar.py",
    ):
        replace_once(
            path,
            '''            "streaming-cancellation",\n''',
            '''            "streaming-cancellation",\n            "structured-inference",\n''',
            f"{path} structured feature",
        )

    path = "kernel/crates/clever-kernel/tests/fixtures/fake_adapter_sidecar.py"
    helper_anchor = '''def stream_terminal(request, final_sequence: int) -> adapter_pb2.AdapterFrame:\n'''
    helper = '''def structured_chunk(request, sequence: int, delta: str) -> adapter_pb2.AdapterFrame:\n    body = inference_pb2.InferenceChunk(\n        contract_version=inference_version(),\n        request_id=request.request_id,\n        attempt_id=request.attempt_id,\n        sequence=sequence,\n        structured_json_delta=delta,\n    )\n    return frame(f"structured-chunk-{sequence}", "inference_chunk", body, correlation_id="__REQUEST_FRAME__")\n\n\ndef tool_chunk(request, sequence: int, *, call_id: str = "", name: str = "", arguments: str = "") -> adapter_pb2.AdapterFrame:\n    body = inference_pb2.InferenceChunk(\n        contract_version=inference_version(),\n        request_id=request.request_id,\n        attempt_id=request.attempt_id,\n        sequence=sequence,\n        tool_call_fragments=[\n            inference_pb2.InferenceToolCallFragment(\n                index=0, call_id=call_id, name=name, arguments_json_delta=arguments\n            )\n        ],\n    )\n    return frame(f"tool-chunk-{sequence}", "inference_chunk", body, correlation_id="__REQUEST_FRAME__")\n\n\n'''
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if helper not in text:
        if text.count(helper_anchor) != 1:
            raise RuntimeError("fake sidecar helper anchor mismatch")
        target.write_text(text.replace(helper_anchor, helper + helper_anchor, 1), encoding="utf-8")
    replace_once(
        path,
        '''        first = stream_chunk(request, 1, "hé")\n        second = stream_chunk(request, 2, "llo")\n        terminal = stream_terminal(request, 2)\n''',
        '''        if mode == "stream-structured-valid":\n            first = structured_chunk(request, 1, '{"answer":"hel')\n            second = structured_chunk(request, 2, 'lo"}')\n            terminal = stream_terminal(request, 2)\n            for value in (first, second, terminal):\n                value.correlation_id = envelope.frame_id\n            write_coalesced(first, second, terminal)\n            return 0\n        if mode == "stream-tool-valid":\n            first = tool_chunk(request, 1, call_id="call-weather", name="weather", arguments='{"city":"Ma')\n            second = tool_chunk(request, 2, arguments='drid"}')\n            terminal = stream_terminal(request, 2)\n            terminal.inference_terminal.finish_reason = inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL\n            for value in (first, second, terminal):\n                value.correlation_id = envelope.frame_id\n            write_coalesced(first, second, terminal)\n            return 0\n        if mode == "stream-structured-mixed":\n            mixed = structured_chunk(request, 1, '{"answer":"bad"}')\n            mixed.inference_chunk.text_delta = "also-text"\n            terminal = stream_terminal(request, 1)\n            for value in (mixed, terminal):\n                value.correlation_id = envelope.frame_id\n            write_coalesced(mixed, terminal)\n            return 0\n        first = stream_chunk(request, 1, "hé")\n        second = stream_chunk(request, 2, "llo")\n        terminal = stream_terminal(request, 2)\n''',
        "fake structured modes",
    )


def patch_kernel() -> None:
    path = "kernel/crates/clever-kernel/src/adapter.rs"
    replace_once(
        path,
        '''        if !self.negotiated_features.contains("streaming-inference") {\n            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(\n                "peer did not negotiate streaming-inference".to_owned(),\n            ));\n        }\n''',
        '''        if !self.negotiated_features.contains("streaming-inference") {\n            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(\n                "peer did not negotiate streaming-inference".to_owned(),\n            ));\n        }\n''',
        "stream feature anchor",
    )
    replace_once(
        path,
        '''        let config = request.config.as_ref().ok_or_else(|| {\n            AdapterSupervisorError::InvalidInferenceRequest("config is required".to_owned())\n        })?;\n        if request.engine_id != W02_UNARY_ENGINE_ID\n            || request.model_id != W02_UNARY_MODEL_ID\n            || request.idempotency_key.trim().is_empty()\n            || request.inputs.is_empty()\n            || request.deadline_at.is_none()\n            || !config.stream\n            || config.max_output_tokens == 0\n            || config.max_output_tokens > 256\n            || request\n                .inputs\n                .iter()\n                .any(|input| input.role == 0 || input.content.trim().is_empty())\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(\n                "request is outside the bounded W02-11 streaming lane".to_owned(),\n            ));\n        }\n''',
        '''        let config = request.config.as_ref().ok_or_else(|| {\n            AdapterSupervisorError::InvalidInferenceRequest("config is required".to_owned())\n        })?;\n        let structured_mode = !config.structured_output_schema_json.trim().is_empty();\n        let tool_mode = !config.tools.is_empty();\n        let mut tool_names = BTreeSet::new();\n        let invalid_tools = config.tools.iter().any(|tool| {\n            tool.name.trim().is_empty()\n                || tool.arguments_schema_json.trim().is_empty()\n                || !tool_names.insert(tool.name.clone())\n        });\n        if (structured_mode || tool_mode)\n            && !self.negotiated_features.contains("structured-inference")\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(\n                "peer did not negotiate structured-inference".to_owned(),\n            ));\n        }\n        if request.engine_id != W02_UNARY_ENGINE_ID\n            || request.model_id != W02_UNARY_MODEL_ID\n            || request.idempotency_key.trim().is_empty()\n            || request.inputs.is_empty()\n            || request.deadline_at.is_none()\n            || !config.stream\n            || config.max_output_tokens == 0\n            || config.max_output_tokens > 256\n            || (structured_mode && tool_mode)\n            || invalid_tools\n            || request\n                .inputs\n                .iter()\n                .any(|input| input.role == 0 || input.content.trim().is_empty())\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidInferenceRequest(\n                "request is outside the bounded W02-13 streaming lane".to_owned(),\n            ));\n        }\n''',
        "bounded W02-13 request validation",
    )
    replace_once(
        path,
        '''        if chunk.request_id != request.request_id\n            || chunk.attempt_id != request.attempt_id\n            || chunk.sequence != expected_sequence\n            || chunk.text_delta.is_empty()\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(format!(\n                "invalid streaming chunk identity/sequence/content: expected sequence {expected_sequence}"\n            )));\n        }\n        Ok(())\n''',
        '''        let config = request.config.as_ref().ok_or_else(|| {\n            AdapterSupervisorError::InvalidInferenceRequest("config is required".to_owned())\n        })?;\n        let structured_mode = !config.structured_output_schema_json.trim().is_empty();\n        let tool_mode = !config.tools.is_empty();\n        let has_text = !chunk.text_delta.is_empty();\n        let has_structured = !chunk.structured_json_delta.is_empty();\n        let has_tools = !chunk.tool_call_fragments.is_empty();\n        let payload_count = usize::from(has_text) + usize::from(has_structured) + usize::from(has_tools);\n        let declared_tools: BTreeSet<&str> = config.tools.iter().map(|tool| tool.name.as_str()).collect();\n        let tool_fragments_valid = chunk.tool_call_fragments.iter().all(|fragment| {\n            (!fragment.call_id.is_empty() || !fragment.name.is_empty() || !fragment.arguments_json_delta.is_empty())\n                && (fragment.name.is_empty() || declared_tools.contains(fragment.name.as_str()))\n        });\n        let payload_valid = payload_count == 1\n            && if structured_mode { has_structured } else if tool_mode { has_tools } else { has_text };\n        if chunk.request_id != request.request_id\n            || chunk.attempt_id != request.attempt_id\n            || chunk.sequence != expected_sequence\n            || !payload_valid\n            || !tool_fragments_valid\n        {\n            return self.fail_protocol(AdapterSupervisorError::InvalidRuntimeResponse(format!(\n                "invalid streaming chunk identity/sequence/typed payload: expected sequence {expected_sequence}"\n            )));\n        }\n        Ok(())\n''',
        "typed stream chunk validation",
    )
    replace_once(
        path,
        '''        if terminal.request_id != request.request_id\n            || terminal.attempt_id != request.attempt_id\n            || terminal.final_sequence != expected_final_sequence\n            || !matches!(\n                finish,\n                Some(InferenceFinishReason::Unspecified)\n                    | Some(InferenceFinishReason::Stop)\n                    | Some(InferenceFinishReason::Length)\n                    | Some(InferenceFinishReason::ContentFilter)\n            )\n            || !usage_valid\n''',
        '''        let tool_mode = request.config.as_ref().is_some_and(|config| !config.tools.is_empty());\n        let finish_valid = if tool_mode {\n            finish == Some(InferenceFinishReason::ToolCall)\n        } else {\n            matches!(\n                finish,\n                Some(InferenceFinishReason::Unspecified)\n                    | Some(InferenceFinishReason::Stop)\n                    | Some(InferenceFinishReason::Length)\n                    | Some(InferenceFinishReason::ContentFilter)\n            )\n        };\n        if terminal.request_id != request.request_id\n            || terminal.attempt_id != request.attempt_id\n            || terminal.final_sequence != expected_final_sequence\n            || !finish_valid\n            || !usage_valid\n''',
        "typed stream terminal validation",
    )


def patch_rust_fixtures() -> None:
    for path in (
        "kernel/crates/clever-kernel/tests/adapter_supervisor.rs",
        "kernel/crates/clever-kernel/tests/inference_security.rs",
    ):
        target = ROOT / path
        text = target.read_text(encoding="utf-8")
        old = '''            stop_sequences: Vec::new(),\n            stream: true,\n'''
        new = '''            stop_sequences: Vec::new(),\n            stream: true,\n            structured_output_schema_json: String::new(),\n            tools: Vec::new(),\n'''
        if old in text and new not in text:
            text = text.replace(old, new)
        old_false = '''            stop_sequences: Vec::new(),\n            stream: false,\n'''
        new_false = '''            stop_sequences: Vec::new(),\n            stream: false,\n            structured_output_schema_json: String::new(),\n            tools: Vec::new(),\n'''
        if old_false in text and new_false not in text:
            text = text.replace(old_false, new_false)
        target.write_text(text, encoding="utf-8")

    path = "kernel/crates/clever-kernel/tests/adapter_supervisor.rs"
    replace_once(
        path,
        '''    CapabilityAvailability, ContractVersion, InferenceConfig, InferenceFinishReason,\n    InferenceInput, InferenceRequest, InferenceRole, InferenceUsageMeasurement, PrincipalRef,\n''',
        '''    CapabilityAvailability, ContractVersion, InferenceConfig, InferenceFinishReason,\n    InferenceInput, InferenceRequest, InferenceRole, InferenceToolDefinition,\n    InferenceUsageMeasurement, PrincipalRef,\n''',
        "Rust typed test import",
    )
    anchor = '''#[test]\nfn rejects_relative_adapter_programs_before_spawn() {\n'''
    helpers = '''fn fake_structured_request() -> InferenceRequest {\n    let mut request = fake_stream_request();\n    request.request_id = "w02-13-structured-request".to_owned();\n    request.attempt_id = "w02-13-structured-attempt".to_owned();\n    request.config.as_mut().expect("config").structured_output_schema_json =\n        r#"{"type":"object","additionalProperties":false,"required":["answer"],"properties":{"answer":{"type":"string"}}}"#.to_owned();\n    request\n}\n\nfn fake_tool_request() -> InferenceRequest {\n    let mut request = fake_stream_request();\n    request.request_id = "w02-13-tool-request".to_owned();\n    request.attempt_id = "w02-13-tool-attempt".to_owned();\n    request.config.as_mut().expect("config").tools = vec![InferenceToolDefinition {\n        name: "weather".to_owned(),\n        arguments_schema_json: r#"{"type":"object","additionalProperties":false,"required":["city"],"properties":{"city":{"type":"string"}}}"#.to_owned(),\n    }];\n    request\n}\n\n'''
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if helpers not in text:
        if text.count(anchor) != 1:
            raise RuntimeError("Rust helper insertion anchor mismatch")
        target.write_text(text.replace(anchor, helpers + anchor, 1), encoding="utf-8")
    tests_anchor = '''#[test]\nfn rejects_relative_adapter_programs_before_spawn() {\n'''
    tests = '''#[test]\nfn canonical_structured_fragments_cross_typed_transport_without_text_execution() {\n    let command = fake_command("stream-structured-valid");\n    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())\n        .expect("connect structured fake sidecar");\n    let result = supervisor.infer_stream(fake_structured_request()).expect("typed structured stream");\n    assert_eq!(result.chunks.len(), 2);\n    assert!(result.text.is_empty());\n    let assembled: String = result.chunks.iter().map(|chunk| chunk.structured_json_delta.as_str()).collect();\n    assert_eq!(assembled, r#"{"answer":"hello"}"#);\n    assert!(result.chunks.iter().all(|chunk| chunk.text_delta.is_empty() && chunk.tool_call_fragments.is_empty()));\n}\n\n#[test]\nfn canonical_tool_fragments_remain_inert_typed_data_and_finish_tool_call() {\n    let command = fake_command("stream-tool-valid");\n    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())\n        .expect("connect tool fake sidecar");\n    let result = supervisor.infer_stream(fake_tool_request()).expect("typed tool stream");\n    assert_eq!(result.chunks.len(), 2);\n    assert!(result.text.is_empty());\n    assert_eq!(InferenceFinishReason::try_from(result.terminal.finish_reason), Ok(InferenceFinishReason::ToolCall));\n    assert_eq!(result.chunks[0].tool_call_fragments[0].name, "weather");\n    let arguments: String = result.chunks.iter().map(|chunk| chunk.tool_call_fragments[0].arguments_json_delta.as_str()).collect();\n    assert_eq!(arguments, r#"{"city":"Madrid"}"#);\n}\n\n#[test]\nfn mixed_text_and_structured_payload_fails_closed() {\n    let command = fake_command("stream-structured-mixed");\n    let mut supervisor = AdapterSupervisor::start(command, fake_identity(), fast_policy())\n        .expect("connect invalid structured fake sidecar");\n    let error = supervisor.infer_stream(fake_structured_request()).expect_err("mixed payload must fail");\n    assert!(matches!(error, AdapterSupervisorError::InvalidRuntimeResponse(_)));\n    assert!(supervisor.is_poisoned());\n}\n\n'''
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if tests not in text:
        if text.count(tests_anchor) != 1:
            raise RuntimeError("Rust typed test anchor mismatch")
        target.write_text(text.replace(tests_anchor, tests + tests_anchor, 1), encoding="utf-8")


def write_python_transport_tests() -> None:
    path = ROOT / "tests/test_cp03_w02_structured_transport.py"
    path.write_text('''from __future__ import annotations\n\nfrom pathlib import Path\nimport time\nimport unittest\nfrom types import SimpleNamespace\nfrom unittest.mock import patch\n\nfrom clever.v1 import common_pb2, identity_pb2, inference_pb2\n\nfrom adapters.openjarvis.streaming_inference import execute_stream\nfrom adapters.openjarvis.unary_inference import PINNED_ENGINE_ID, PINNED_MODEL_ID, UnaryInferenceRejected\n\n\nclass FakeMessage:\n    def __init__(self, **kwargs):\n        self.__dict__.update(kwargs)\n\n\nclass FakeRole:\n    SYSTEM = "system"\n    USER = "user"\n    ASSISTANT = "assistant"\n    TOOL = "tool"\n\n\nclass FakeEngine:\n    def __init__(self, chunks):\n        self.chunks = chunks\n    async def stream_full(self, _messages, **_kwargs):\n        for chunk in self.chunks:\n            yield chunk\n    def close(self):\n        pass\n\n\ndef request(*, structured=False, tool=False):\n    config = inference_pb2.InferenceConfig(max_output_tokens=16, temperature=0.0, stream=True)\n    if structured:\n        config.structured_output_schema_json = '{"type":"object","additionalProperties":false,"required":["answer"],"properties":{"answer":{"type":"string"}}}'\n    if tool:\n        config.tools.add(name="weather", arguments_schema_json='{"type":"object","additionalProperties":false,"required":["city"],"properties":{"city":{"type":"string"}}}')\n    value = inference_pb2.InferenceRequest(\n        contract_version=common_pb2.ContractVersion(major=1, minor=2),\n        request_id="req-w02-13", attempt_id="attempt-w02-13",\n        principal=identity_pb2.PrincipalRef(user_id="local-user"), session_id="session",\n        engine_id=PINNED_ENGINE_ID, model_id=PINNED_MODEL_ID,\n        inputs=[inference_pb2.InferenceInput(role=inference_pb2.INFERENCE_ROLE_USER, content="typed")],\n        config=config, idempotency_key="idem-w02-13",\n    )\n    deadline = time.time_ns() + 60_000_000_000\n    value.deadline_at.seconds = deadline // 1_000_000_000\n    value.deadline_at.nanos = deadline % 1_000_000_000\n    return value\n\n\ndef run(req, native):\n    chunks=[]; terminals=[]\n    engine=FakeEngine(native)\n    with patch("adapters.openjarvis.streaming_inference.attest_pinned_artifact"):\n        execute_stream(req, emit_chunk=chunks.append, emit_terminal=terminals.append,\n            engine_factory=lambda _host: (engine, FakeMessage, FakeRole),\n            artifact_path=Path("/ignored/model.gguf"), host="http://127.0.0.1:8080")\n    return chunks, terminals\n\n\nclass StructuredTransportTests(unittest.TestCase):\n    def test_fragmented_structured_json_is_validated_before_typed_emission(self):\n        chunks, terminals = run(request(structured=True), [\n            SimpleNamespace(content='{"answer":"hel', tool_calls=None, content_blocks=None, tool_results=None, finish_reason=None, usage=None),\n            SimpleNamespace(content='lo"}', tool_calls=None, content_blocks=None, tool_results=None, finish_reason="stop", usage=None),\n        ])\n        self.assertEqual([c.structured_json_delta for c in chunks], ['{"answer":"hel', 'lo"}'])\n        self.assertTrue(all(not c.text_delta and not c.tool_call_fragments for c in chunks))\n        self.assertEqual(len(terminals), 1)\n\n    def test_fragmented_tool_arguments_cross_transport_as_inert_data(self):\n        chunks, terminals = run(request(tool=True), [\n            SimpleNamespace(content=None, tool_calls=[{"index":0,"id":"call-weather","function":{"name":"weather","arguments":'{"city":"Ma'}}], content_blocks=None, tool_results=None, finish_reason=None, usage=None),\n            SimpleNamespace(content=None, tool_calls=[{"index":0,"function":{"arguments":'drid"}'}}], content_blocks=None, tool_results=None, finish_reason="tool_calls", usage=None),\n        ])\n        self.assertEqual(len(chunks), 2)\n        self.assertEqual(chunks[0].tool_call_fragments[0].name, "weather")\n        self.assertEqual("".join(c.tool_call_fragments[0].arguments_json_delta for c in chunks), '{"city":"Madrid"}')\n        self.assertEqual(terminals[0].finish_reason, inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL)\n\n    def test_invalid_structured_json_and_undeclared_tool_never_emit_success(self):\n        with self.assertRaises(UnaryInferenceRejected):\n            run(request(structured=True), [SimpleNamespace(content='{"answer":7}', tool_calls=None, content_blocks=None, tool_results=None, finish_reason="stop", usage=None)])\n        with self.assertRaises(UnaryInferenceRejected):\n            run(request(), [SimpleNamespace(content=None, tool_calls=[{"index":0,"id":"x","function":{"name":"shell","arguments":"{}"}}], content_blocks=None, tool_results=None, finish_reason="tool_calls", usage=None)])\n\n    def test_structured_and_tools_are_mutually_exclusive(self):\n        req = request(structured=True)\n        req.config.tools.add(name="weather", arguments_schema_json="{}")\n        with self.assertRaises(UnaryInferenceRejected):\n            run(req, [])\n\n\nif __name__ == "__main__":\n    unittest.main()\n''', encoding="utf-8")


def main() -> int:
    patch_proto()
    patch_json_schema()
    patch_structured_core()
    patch_streaming()
    patch_sidecars()
    patch_kernel()
    patch_rust_fixtures()
    write_python_transport_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
