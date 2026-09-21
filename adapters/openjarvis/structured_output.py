from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any, Iterable, Mapping


MAX_TOOL_CALLS = 64
MAX_TOOL_NAME_BYTES = 512
MAX_TOOL_ARGUMENT_BYTES = 65_536
MAX_STRUCTURED_OUTPUT_BYTES = 1_048_576


class StructuredOutputRejected(ValueError):
    """Fail-closed rejection for malformed structured/model-emitted data."""


@dataclass(frozen=True, slots=True)
class ToolCallData:
    """A fully assembled model-emitted tool call.

    This is data only. The adapter intentionally exposes no execution primitive,
    registry lookup, shell/browser/MCP bridge, or authorization bypass here.
    """

    index: int
    call_id: str
    name: str
    arguments_json: str
    arguments: Mapping[str, Any]
    fragments: tuple[Mapping[str, Any], ...]


@dataclass(slots=True)
class _MutableToolCall:
    index: int
    call_id: str = ""
    name: str = ""
    arguments_json: str = ""
    fragments: list[Mapping[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.fragments is None:
            self.fragments = []


class ToolCallAssembler:
    """Assemble OpenJarvis ``StreamChunk.tool_calls`` fragments without executing them.

    The pinned OpenJarvis stream contract uses OpenAI-style fragments shaped as
    ``{"index", "id", "function": {"name", "arguments"}}``. IDs and names may
    arrive only on the first fragment while JSON arguments arrive incrementally.
    Conflicting identity, malformed JSON, gaps, and resource-budget violations are
    rejected rather than repaired or guessed.
    """

    def __init__(self) -> None:
        self._calls: dict[int, _MutableToolCall] = {}
        self._closed = False

    def feed(self, fragments: object) -> None:
        if self._closed:
            raise StructuredOutputRejected("tool-call assembler is already finalized")
        if not isinstance(fragments, list) or not fragments:
            raise StructuredOutputRejected("tool_calls must be a non-empty list")

        for raw in fragments:
            if not isinstance(raw, dict):
                raise StructuredOutputRejected("each tool-call fragment must be an object")
            index = raw.get("index")
            if type(index) is not int or index < 0 or index >= MAX_TOOL_CALLS:
                raise StructuredOutputRejected("tool-call index is invalid or exceeds budget")

            call = self._calls.setdefault(index, _MutableToolCall(index=index))
            if len(self._calls) > MAX_TOOL_CALLS:
                raise StructuredOutputRejected("tool-call count exceeds budget")

            call_id = raw.get("id", "")
            if call_id is None:
                call_id = ""
            if not isinstance(call_id, str):
                raise StructuredOutputRejected("tool-call id fragment must be text")
            if call_id:
                if call.call_id and call.call_id != call_id:
                    raise StructuredOutputRejected("conflicting tool-call ids for one index")
                call.call_id = call_id

            function = raw.get("function", {})
            if function is None:
                function = {}
            if not isinstance(function, dict):
                raise StructuredOutputRejected("tool-call function fragment must be an object")

            name_delta = function.get("name", "")
            arguments_delta = function.get("arguments", "")
            if name_delta is None:
                name_delta = ""
            if arguments_delta is None:
                arguments_delta = ""
            if not isinstance(name_delta, str) or not isinstance(arguments_delta, str):
                raise StructuredOutputRejected("tool-call name/arguments fragments must be text")

            next_name = call.name + name_delta
            next_arguments = call.arguments_json + arguments_delta
            if len(next_name.encode("utf-8")) > MAX_TOOL_NAME_BYTES:
                raise StructuredOutputRejected("tool-call name exceeds byte budget")
            if len(next_arguments.encode("utf-8")) > MAX_TOOL_ARGUMENT_BYTES:
                raise StructuredOutputRejected("tool-call arguments exceed byte budget")

            call.name = next_name
            call.arguments_json = next_arguments
            assert call.fragments is not None
            call.fragments.append(deepcopy(raw))

    def finalize(self) -> tuple[ToolCallData, ...]:
        if self._closed:
            raise StructuredOutputRejected("tool-call assembler is already finalized")
        self._closed = True
        if not self._calls:
            return ()

        indexes = sorted(self._calls)
        if indexes != list(range(len(indexes))):
            raise StructuredOutputRejected("tool-call indexes must be contiguous from zero")

        result: list[ToolCallData] = []
        for index in indexes:
            call = self._calls[index]
            if not call.call_id:
                raise StructuredOutputRejected("tool-call id is missing; refusing to fabricate one")
            if not call.name:
                raise StructuredOutputRejected("tool-call name is missing; refusing to fabricate one")
            try:
                parsed = json.loads(call.arguments_json)
            except (json.JSONDecodeError, TypeError) as exc:
                raise StructuredOutputRejected(
                    f"tool-call arguments are not valid JSON for index {index}"
                ) from exc
            if not isinstance(parsed, dict):
                raise StructuredOutputRejected("tool-call arguments must decode to a JSON object")
            result.append(
                ToolCallData(
                    index=index,
                    call_id=call.call_id,
                    name=call.name,
                    arguments_json=call.arguments_json,
                    arguments=parsed,
                    fragments=tuple(call.fragments or ()),
                )
            )
        return tuple(result)


def validate_structured_json(text: str, schema: Mapping[str, Any]) -> Any:
    """Parse one JSON value and validate it against caller-supplied Draft 2020-12 schema.

    The function never repairs model output and never trusts a schema emitted by the
    model itself. Missing validator support is an explicit failure, not a bypass.
    """

    if not isinstance(text, str):
        raise StructuredOutputRejected("structured output must be text")
    if len(text.encode("utf-8")) > MAX_STRUCTURED_OUTPUT_BYTES:
        raise StructuredOutputRejected("structured output exceeds byte budget")
    if not isinstance(schema, Mapping):
        raise StructuredOutputRejected("structured output schema must be an object")

    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StructuredOutputRejected("structured output is not valid JSON") from exc

    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError as exc:  # pragma: no cover - exercised in packaging/preflight lanes
        raise StructuredOutputRejected("jsonschema validator dependency is unavailable") from exc

    try:
        Draft202012Validator.check_schema(dict(schema))
        validator = Draft202012Validator(dict(schema))
    except SchemaError as exc:
        raise StructuredOutputRejected("caller-supplied JSON schema is invalid") from exc

    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        path = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise StructuredOutputRejected(f"structured output violates schema at {path}: {error.message}")
    return value


class StructuredStreamAssembler:
    """Collect text and tool-call fragments, then produce validated inert data."""

    def __init__(self) -> None:
        self._text: list[str] = []
        self._tool_calls = ToolCallAssembler()
        self._saw_tool_fragments = False
        self._closed = False

    def feed_text(self, delta: str) -> None:
        if self._closed:
            raise StructuredOutputRejected("structured stream assembler is already finalized")
        if not isinstance(delta, str):
            raise StructuredOutputRejected("text delta must be text")
        self._text.append(delta)
        if len("".join(self._text).encode("utf-8")) > MAX_STRUCTURED_OUTPUT_BYTES:
            raise StructuredOutputRejected("structured stream text exceeds byte budget")

    def feed_tool_calls(self, fragments: object) -> None:
        if self._closed:
            raise StructuredOutputRejected("structured stream assembler is already finalized")
        self._tool_calls.feed(fragments)
        self._saw_tool_fragments = True

    def finalize(
        self,
        *,
        response_schema: Mapping[str, Any] | None = None,
    ) -> tuple[Any | None, tuple[ToolCallData, ...]]:
        if self._closed:
            raise StructuredOutputRejected("structured stream assembler is already finalized")
        self._closed = True
        text = "".join(self._text)
        structured_value: Any | None = None
        if response_schema is not None:
            if not text:
                raise StructuredOutputRejected("structured output schema requested but no text was emitted")
            structured_value = validate_structured_json(text, response_schema)
        tool_calls = self._tool_calls.finalize() if self._saw_tool_fragments else ()
        return structured_value, tool_calls


__all__ = [
    "MAX_STRUCTURED_OUTPUT_BYTES",
    "MAX_TOOL_ARGUMENT_BYTES",
    "MAX_TOOL_CALLS",
    "MAX_TOOL_NAME_BYTES",
    "StructuredOutputRejected",
    "StructuredStreamAssembler",
    "ToolCallAssembler",
    "ToolCallData",
    "validate_structured_json",
]
