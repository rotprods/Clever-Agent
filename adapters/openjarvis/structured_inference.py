from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


DEFAULT_MAX_JSON_BYTES = 1 * 1024 * 1024


class StructuredInferenceError(ValueError):
    """Fail-closed structured inference decode/validation error."""


@dataclass(frozen=True, slots=True)
class ToolCallData:
    """Validated tool-call data.

    This type is deliberately inert: it carries no executable/callable field and
    performs no shell, MCP, browser, network or tool dispatch.
    """

    index: int
    call_id: str
    name: str
    arguments: Mapping[str, Any]


def _reject_constant(value: str) -> None:
    raise StructuredInferenceError(f"non-finite JSON constant is forbidden: {value}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StructuredInferenceError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _strict_json_loads(payload: str) -> Any:
    try:
        return json.loads(
            payload,
            parse_constant=_reject_constant,
            object_pairs_hook=_strict_object,
        )
    except StructuredInferenceError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise StructuredInferenceError(f"invalid JSON: {exc.msg if hasattr(exc, 'msg') else exc}") from exc


def _validate_schema(value: Any, schema: Mapping[str, Any]) -> None:
    if not isinstance(schema, Mapping):
        raise StructuredInferenceError("JSON schema must be a mapping")
    try:
        Draft202012Validator.check_schema(dict(schema))
        Draft202012Validator(dict(schema)).validate(value)
    except SchemaError as exc:
        raise StructuredInferenceError(f"invalid JSON schema: {exc.message}") from exc
    except ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path) or "$"
        raise StructuredInferenceError(f"schema validation failed at {path}: {exc.message}") from exc


def assemble_structured_json(
    fragments: Iterable[str],
    *,
    schema: Mapping[str, Any],
    max_bytes: int = DEFAULT_MAX_JSON_BYTES,
) -> Any:
    """Assemble fragmented structured output and validate it fail-closed."""
    if max_bytes <= 0:
        raise StructuredInferenceError("max_bytes must be positive")
    parts: list[str] = []
    size = 0
    for index, fragment in enumerate(fragments):
        if not isinstance(fragment, str):
            raise StructuredInferenceError(f"structured fragment {index} must be text")
        encoded = fragment.encode("utf-8")
        size += len(encoded)
        if size > max_bytes:
            raise StructuredInferenceError(f"structured JSON exceeds byte budget: {size} > {max_bytes}")
        parts.append(fragment)
    if not parts:
        raise StructuredInferenceError("structured output contained no fragments")
    value = _strict_json_loads("".join(parts))
    _validate_schema(value, schema)
    return value


@dataclass(slots=True)
class _ToolAccumulator:
    call_id: str | None = None
    name: str | None = None
    arguments: list[str] | None = None
    argument_bytes: int = 0

    def __post_init__(self) -> None:
        if self.arguments is None:
            self.arguments = []


def assemble_tool_call_fragments(
    fragments: Iterable[Mapping[str, Any]],
    *,
    schemas_by_name: Mapping[str, Mapping[str, Any]],
    max_argument_bytes: int = DEFAULT_MAX_JSON_BYTES,
) -> tuple[ToolCallData, ...]:
    """Assemble OpenAI-style fragmented native tool calls into inert typed data.

    Expected fragment shape is ``{index,id?,function:{name?,arguments?}}``. Tool
    identity may repeat but may never change. Arguments are concatenated in
    arrival order, parsed with strict JSON, required to be an object, and then
    validated against the declared schema for that exact tool name.
    """
    if max_argument_bytes <= 0:
        raise StructuredInferenceError("max_argument_bytes must be positive")
    if not isinstance(schemas_by_name, Mapping):
        raise StructuredInferenceError("schemas_by_name must be a mapping")

    accumulators: dict[int, _ToolAccumulator] = {}
    seen_any = False
    for position, fragment in enumerate(fragments):
        seen_any = True
        if not isinstance(fragment, Mapping):
            raise StructuredInferenceError(f"tool fragment {position} must be a mapping")
        index = fragment.get("index")
        if type(index) is not int or index < 0:
            raise StructuredInferenceError(f"tool fragment {position} has invalid index")
        unexpected = set(fragment) - {"index", "id", "function"}
        if unexpected:
            raise StructuredInferenceError(
                f"tool fragment {position} contains unsupported keys: {sorted(unexpected)}"
            )
        state = accumulators.setdefault(index, _ToolAccumulator())

        call_id = fragment.get("id")
        if call_id is not None:
            if not isinstance(call_id, str) or not call_id.strip():
                raise StructuredInferenceError(f"tool fragment {position} has invalid id")
            if state.call_id is not None and state.call_id != call_id:
                raise StructuredInferenceError(f"tool call {index} changed id mid-stream")
            state.call_id = call_id

        function = fragment.get("function")
        if function is not None:
            if not isinstance(function, Mapping):
                raise StructuredInferenceError(f"tool fragment {position}.function must be a mapping")
            function_unexpected = set(function) - {"name", "arguments"}
            if function_unexpected:
                raise StructuredInferenceError(
                    f"tool fragment {position}.function contains unsupported keys: {sorted(function_unexpected)}"
                )
            name = function.get("name")
            if name is not None:
                if not isinstance(name, str) or not name.strip():
                    raise StructuredInferenceError(f"tool fragment {position} has invalid function.name")
                if state.name is not None and state.name != name:
                    raise StructuredInferenceError(f"tool call {index} changed name mid-stream")
                state.name = name
            arguments = function.get("arguments")
            if arguments is not None:
                if not isinstance(arguments, str):
                    raise StructuredInferenceError(
                        f"tool fragment {position}.function.arguments must be text"
                    )
                state.argument_bytes += len(arguments.encode("utf-8"))
                if state.argument_bytes > max_argument_bytes:
                    raise StructuredInferenceError(
                        f"tool call {index} arguments exceed byte budget: "
                        f"{state.argument_bytes} > {max_argument_bytes}"
                    )
                assert state.arguments is not None
                state.arguments.append(arguments)

    if not seen_any:
        raise StructuredInferenceError("tool-call stream contained no fragments")

    result: list[ToolCallData] = []
    for index in sorted(accumulators):
        state = accumulators[index]
        if state.call_id is None:
            raise StructuredInferenceError(f"tool call {index} missing id")
        if state.name is None:
            raise StructuredInferenceError(f"tool call {index} missing function.name")
        if state.name not in schemas_by_name:
            raise StructuredInferenceError(f"tool call {index} references undeclared tool: {state.name}")
        assert state.arguments is not None
        if not state.arguments:
            raise StructuredInferenceError(f"tool call {index} missing function.arguments")
        arguments = _strict_json_loads("".join(state.arguments))
        if not isinstance(arguments, dict):
            raise StructuredInferenceError(f"tool call {index} arguments must decode to an object")
        _validate_schema(arguments, schemas_by_name[state.name])
        result.append(
            ToolCallData(
                index=index,
                call_id=state.call_id,
                name=state.name,
                arguments=arguments,
            )
        )
    return tuple(result)
