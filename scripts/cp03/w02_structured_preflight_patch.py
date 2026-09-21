from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "adapters/openjarvis/structured_output.py"
STREAMING_PATH = ROOT / "adapters/openjarvis/streaming_inference.py"

MODULE = '''from __future__ import annotations

import copy
from dataclasses import dataclass, field
import json
from typing import Any


MAX_TOOL_CALLS = 64
MAX_FRAGMENTS = 256
MAX_FRAGMENT_BYTES = 64 * 1024
MAX_TOTAL_FRAGMENT_BYTES = 256 * 1024
MAX_NESTING_DEPTH = 8


class StructuredOutputError(ValueError):
    """Fail-closed normalization error for model-produced structured data."""


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    index: int
    call_id: str
    call_type: str
    name: str
    arguments_json: str
    arguments: dict[str, Any]
    fragments: tuple[dict[str, Any], ...]


@dataclass(slots=True)
class _ToolCallParts:
    call_id_parts: list[str] = field(default_factory=list)
    name_parts: list[str] = field(default_factory=list)
    arguments_parts: list[str] = field(default_factory=list)
    call_type: str = ""
    fragments: list[dict[str, Any]] = field(default_factory=list)


def _bounded_size(value: object, *, depth: int = 0) -> int:
    if depth > MAX_NESTING_DEPTH:
        raise StructuredOutputError("tool-call fragment nesting exceeds bounded depth")
    if value is None or isinstance(value, (bool, int, float)):
        return 8
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, (list, tuple)):
        return sum(_bounded_size(item, depth=depth + 1) for item in value)
    if isinstance(value, dict):
        total = 0
        for key, item in value.items():
            if not isinstance(key, str):
                raise StructuredOutputError("tool-call fragment keys must be strings")
            total += len(key.encode("utf-8"))
            total += _bounded_size(item, depth=depth + 1)
        return total
    raise StructuredOutputError(
        f"unsupported tool-call metadata type: {type(value).__name__}"
    )


def _string_field(mapping: dict[str, Any], field_name: str) -> str:
    value = mapping.get(field_name, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise StructuredOutputError(f"tool-call {field_name} fragment must be text")
    return value


class ToolCallFragmentAssembler:
    """Assemble pinned OpenJarvis ``StreamChunk.tool_calls`` without executing them.

    The pinned OpenAI-compatible and Anthropic paths emit OpenAI-shaped fragments
    keyed by ``index``. Google emits a complete call in the same shape. Provider
    metadata is retained verbatim inside ``fragments`` for later canonical wire
    projection; this layer grants no action authority.
    """

    def __init__(self) -> None:
        self._calls: dict[int, _ToolCallParts] = {}
        self._fragment_count = 0
        self._fragment_bytes = 0

    def ingest(self, fragments: object) -> None:
        if not isinstance(fragments, list):
            raise StructuredOutputError("native tool_calls must be a list")
        for fragment in fragments:
            if not isinstance(fragment, dict):
                raise StructuredOutputError("native tool-call fragment must be an object")
            index = fragment.get("index")
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                raise StructuredOutputError("tool-call index must be a non-negative integer")
            if index >= MAX_TOOL_CALLS:
                raise StructuredOutputError("tool-call index exceeds bounded call count")
            fragment_bytes = _bounded_size(fragment)
            if fragment_bytes > MAX_FRAGMENT_BYTES:
                raise StructuredOutputError("tool-call fragment exceeds byte budget")
            if self._fragment_count + 1 > MAX_FRAGMENTS:
                raise StructuredOutputError("tool-call fragment count exceeds budget")
            if self._fragment_bytes + fragment_bytes > MAX_TOTAL_FRAGMENT_BYTES:
                raise StructuredOutputError("tool-call fragments exceed aggregate byte budget")

            function = fragment.get("function")
            if not isinstance(function, dict):
                raise StructuredOutputError("tool-call fragment requires a function object")
            call_id = _string_field(fragment, "id")
            call_type = _string_field(fragment, "type")
            name = _string_field(function, "name")
            arguments = _string_field(function, "arguments")

            parts = self._calls.setdefault(index, _ToolCallParts())
            if call_type:
                if parts.call_type and parts.call_type != call_type:
                    raise StructuredOutputError("conflicting tool-call type fragments")
                parts.call_type = call_type
            if call_id:
                parts.call_id_parts.append(call_id)
            if name:
                parts.name_parts.append(name)
            if arguments:
                parts.arguments_parts.append(arguments)
            parts.fragments.append(copy.deepcopy(fragment))
            self._fragment_count += 1
            self._fragment_bytes += fragment_bytes

    def finalize(self) -> tuple[ToolCallRecord, ...]:
        if not self._calls:
            return ()
        indices = sorted(self._calls)
        if indices != list(range(len(indices))):
            raise StructuredOutputError("tool-call indices must be contiguous from zero")
        records: list[ToolCallRecord] = []
        for index in indices:
            parts = self._calls[index]
            call_id = "".join(parts.call_id_parts)
            name = "".join(parts.name_parts)
            arguments_json = "".join(parts.arguments_parts)
            if not call_id:
                raise StructuredOutputError(f"tool-call {index} is missing id")
            if not name:
                raise StructuredOutputError(f"tool-call {index} is missing function name")
            if not arguments_json:
                raise StructuredOutputError(f"tool-call {index} is missing arguments JSON")
            try:
                arguments = json.loads(arguments_json)
            except json.JSONDecodeError as exc:
                raise StructuredOutputError(
                    f"tool-call {index} arguments contain invalid JSON"
                ) from exc
            if not isinstance(arguments, dict):
                raise StructuredOutputError(
                    f"tool-call {index} arguments JSON must decode to an object"
                )
            records.append(
                ToolCallRecord(
                    index=index,
                    call_id=call_id,
                    call_type=parts.call_type or "function",
                    name=name,
                    arguments_json=arguments_json,
                    arguments=arguments,
                    fragments=tuple(copy.deepcopy(parts.fragments)),
                )
            )
        return tuple(records)


def validate_structured_json(text: object, schema: object | None) -> object:
    """Parse model JSON and optionally validate Draft 2020-12 without correction."""
    if not isinstance(text, str):
        raise StructuredOutputError("structured output must be text")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StructuredOutputError("structured output contains invalid JSON") from exc
    if schema is None:
        return value
    if not isinstance(schema, dict):
        raise StructuredOutputError("structured output schema must be an object")
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError as exc:
        raise StructuredOutputError(
            "jsonschema runtime dependency is unavailable; refusing unvalidated output"
        ) from exc
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise StructuredOutputError("structured output schema is invalid") from exc
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        first = errors[0]
        path = "$" + "".join(f"[{part!r}]" for part in first.absolute_path)
        raise StructuredOutputError(
            f"structured output schema validation failed at {path}"
        )
    return value
'''

IMPORT = "from adapters.openjarvis.structured_output import StructuredOutputError, ToolCallFragmentAssembler\n"
IMPORT_ANCHOR = "from adapters.openjarvis.unary_inference import (\n"
FINISH_OLD = '''    mapping = {
        "stop": inference_pb2.INFERENCE_FINISH_REASON_STOP,
        "length": inference_pb2.INFERENCE_FINISH_REASON_LENGTH,
        "content_filter": inference_pb2.INFERENCE_FINISH_REASON_CONTENT_FILTER,
    }
'''
FINISH_NEW = '''    mapping = {
        "stop": inference_pb2.INFERENCE_FINISH_REASON_STOP,
        "length": inference_pb2.INFERENCE_FINISH_REASON_LENGTH,
        "content_filter": inference_pb2.INFERENCE_FINISH_REASON_CONTENT_FILTER,
        "tool_calls": inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL,
    }
'''
STATE_OLD = '''            saw_finish = False
            if cancellation_is_requested():
'''
STATE_NEW = '''            saw_finish = False
            tool_call_assembler = ToolCallFragmentAssembler()
            saw_tool_calls = False
            if cancellation_is_requested():
'''
DEFER_OLD = '''                if tool_calls or content_blocks or tool_results:
                    raise UnaryInferenceRejected(
                        inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                        "typed/tool streaming fragments are deferred to W02-13",
                        retryable=False,
                    )
'''
DEFER_NEW = '''                if tool_calls:
                    try:
                        tool_call_assembler.ingest(tool_calls)
                    except StructuredOutputError as exc:
                        raise UnaryInferenceRejected(
                            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                            f"invalid native tool-call fragment: {exc}",
                            retryable=False,
                        ) from exc
                    saw_tool_calls = True
                if content_blocks or tool_results:
                    raise UnaryInferenceRejected(
                        inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                        "aggregate native tool data is not representable on the current canonical inference wire",
                        retryable=False,
                    )
'''
END_OLD = '''            if sequence == 0:
                raise UnaryInferenceRejected(
                    inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                    "native stream ended without content chunks",
                    retryable=False,
                )
'''
END_NEW = '''            if saw_tool_calls:
                try:
                    tool_call_assembler.finalize()
                except StructuredOutputError as exc:
                    raise UnaryInferenceRejected(
                        inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                        f"invalid assembled native tool call: {exc}",
                        retryable=False,
                    ) from exc
                raise UnaryInferenceRejected(
                    inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                    "validated native tool-call data cannot yet be represented on the canonical inference wire; W02-13 wire projection remains required",
                    retryable=False,
                )
            if sequence == 0:
                raise UnaryInferenceRejected(
                    inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                    "native stream ended without content chunks",
                    retryable=False,
                )
'''


def patch_streaming(text: str) -> str:
    if IMPORT not in text:
        if IMPORT_ANCHOR not in text:
            raise RuntimeError("streaming inference import anchor missing")
        text = text.replace(IMPORT_ANCHOR, IMPORT + "\n" + IMPORT_ANCHOR, 1)
    replacements = (
        (FINISH_OLD, FINISH_NEW, "finish reason"),
        (STATE_OLD, STATE_NEW, "assembler state"),
        (DEFER_OLD, DEFER_NEW, "tool deferral"),
        (END_OLD, END_NEW, "tool finalization"),
    )
    for old, new, label in replacements:
        if new in text:
            continue
        if old not in text:
            raise RuntimeError(f"streaming inference {label} anchor missing")
        text = text.replace(old, new, 1)
    return text


def check() -> None:
    if not MODULE_PATH.exists() or MODULE_PATH.read_text(encoding="utf-8") != MODULE:
        raise SystemExit("structured output module is not materialized")
    text = STREAMING_PATH.read_text(encoding="utf-8")
    if patch_streaming(text) != text:
        raise SystemExit("streaming inference W02-13 preflight patch is not materialized")


def apply() -> None:
    MODULE_PATH.write_text(MODULE, encoding="utf-8")
    original = STREAMING_PATH.read_text(encoding="utf-8")
    patched = patch_streaming(original)
    STREAMING_PATH.write_text(patched, encoding="utf-8")
    check()


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.apply:
        apply()
    else:
        check()


if __name__ == "__main__":
    main()
