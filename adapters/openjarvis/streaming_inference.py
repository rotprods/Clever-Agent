from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from clever.v1 import inference_pb2

from adapters.openjarvis.structured_output import (
    MAX_STRUCTURED_OUTPUT_BYTES,
    StructuredOutputRejected,
    StructuredStreamAssembler,
    ToolCallData,
)
from adapters.openjarvis.unary_inference import (
    PINNED_ENGINE_ID,
    PINNED_MODEL_ID,
    UnaryInferenceRejected,
    _artifact_path,
    _loopback_host,
    _messages,
    _native_engine_factory,
    attest_pinned_artifact,
    contract_version,
)


def _reject(message: str) -> UnaryInferenceRejected:
    return UnaryInferenceRejected(
        inference_pb2.INFERENCE_ERROR_CODE_INVALID_REQUEST,
        message,
        retryable=False,
    )


def _request_response_schema(request: inference_pb2.InferenceRequest) -> Mapping[str, Any] | None:
    if not request.HasField("config") or not request.config.HasField("response_schema_json"):
        return None
    raw = request.config.response_schema_json
    if not raw.strip():
        raise _reject("response_schema_json must be non-empty when present")
    if len(raw.encode("utf-8")) > MAX_STRUCTURED_OUTPUT_BYTES:
        raise _reject("response_schema_json exceeds byte budget")
    try:
        schema = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _reject("response_schema_json is not valid JSON") from exc
    if not isinstance(schema, dict):
        raise _reject("response_schema_json must decode to a JSON object")
    return schema


def validate_stream_request(request: inference_pb2.InferenceRequest) -> None:
    if not request.HasField("contract_version") or request.contract_version.major != 1:
        raise _reject("unsupported or missing inference contract version")
    if request.contract_version.minor > 2:
        raise _reject("inference contract minor is newer than supported")
    for field, value in (
        ("request_id", request.request_id),
        ("attempt_id", request.attempt_id),
        ("session_id", request.session_id),
        ("engine_id", request.engine_id),
        ("model_id", request.model_id),
        ("idempotency_key", request.idempotency_key),
    ):
        if not value.strip():
            raise _reject(f"{field} must be non-empty")
    if not request.HasField("principal") or not request.principal.user_id.strip():
        raise _reject("principal.user_id must be non-empty")
    if request.engine_id != PINNED_ENGINE_ID or request.model_id != PINNED_MODEL_ID:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_MODEL_UNAVAILABLE,
            "W02-11 accepts only the exact W02-09 pinned engine/model lane",
            retryable=False,
        )
    if not request.HasField("config"):
        raise _reject("config is required")
    if not request.config.stream:
        raise _reject("stream=false belongs to the unary W02-10 lane")
    if request.config.max_output_tokens <= 0 or request.config.max_output_tokens > 256:
        raise _reject("W02-11 max_output_tokens must be in 1..=256")
    _request_response_schema(request)
    if not request.inputs:
        raise _reject("at least one inference input is required")
    valid_roles = {
        inference_pb2.INFERENCE_ROLE_SYSTEM,
        inference_pb2.INFERENCE_ROLE_USER,
        inference_pb2.INFERENCE_ROLE_ASSISTANT,
        inference_pb2.INFERENCE_ROLE_TOOL,
    }
    for index, item in enumerate(request.inputs):
        if item.role not in valid_roles:
            raise _reject(f"inputs[{index}].role is invalid")
        if not item.content.strip():
            raise _reject(f"inputs[{index}].content must be non-empty")
    if not request.HasField("deadline_at"):
        raise _reject("deadline_at is required")
    deadline_ns = request.deadline_at.seconds * 1_000_000_000 + request.deadline_at.nanos
    if deadline_ns <= time.time_ns():
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_DEADLINE_EXCEEDED,
            "inference deadline already elapsed",
            retryable=False,
        )


def _finish_reason(value: object) -> int:
    if value is None:
        return inference_pb2.INFERENCE_FINISH_REASON_UNSPECIFIED
    mapping = {
        "stop": inference_pb2.INFERENCE_FINISH_REASON_STOP,
        "length": inference_pb2.INFERENCE_FINISH_REASON_LENGTH,
        "content_filter": inference_pb2.INFERENCE_FINISH_REASON_CONTENT_FILTER,
        "tool_calls": inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL,
    }
    reason = mapping.get(str(value))
    if reason is None:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
            f"unsupported native streaming finish_reason {value!r}",
            retryable=False,
        )
    return reason


def _usage(raw: object) -> inference_pb2.InferenceUsage:
    if not isinstance(raw, dict):
        return inference_pb2.InferenceUsage(
            measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN
        )
    values: dict[str, int] = {}
    for native, canonical in (
        ("prompt_tokens", "input_tokens"),
        ("completion_tokens", "output_tokens"),
        ("total_tokens", "total_tokens"),
    ):
        value = raw.get(native)
        if type(value) is not int or value < 0:
            return inference_pb2.InferenceUsage(
                measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN
            )
        values[canonical] = value
    return inference_pb2.InferenceUsage(
        measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_EXACT,
        **values,
    )


def _typed_terminal(
    *,
    request: inference_pb2.InferenceRequest,
    sequence: int,
    finish_reason: int,
    usage: inference_pb2.InferenceUsage,
    calls: tuple[ToolCallData, ...],
    structured_value: Any | None,
) -> inference_pb2.InferenceTerminal:
    terminal = inference_pb2.InferenceTerminal(
        contract_version=contract_version(),
        request_id=request.request_id,
        attempt_id=request.attempt_id,
        final_sequence=sequence,
        finish_reason=finish_reason,
        usage=usage,
        tool_calls=[
            inference_pb2.InferenceToolCall(
                index=call.index,
                call_id=call.call_id,
                name=call.name,
                arguments_json=call.arguments_json,
            )
            for call in calls
        ],
    )
    if structured_value is not None:
        terminal.structured_output.json_value = json.dumps(
            structured_value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return terminal


def execute_stream(
    request: inference_pb2.InferenceRequest,
    *,
    emit_chunk: Callable[[inference_pb2.InferenceChunk], None],
    emit_terminal: Callable[[inference_pb2.InferenceTerminal], None],
    emit_tool_call: Callable[[ToolCallData], None] | None = None,
    response_schema: Mapping[str, Any] | None = None,
    emit_structured_output: Callable[[Any], None] | None = None,
    engine_factory: Callable[[str], tuple[Any, type, type]] = _native_engine_factory,
    artifact_path: Path | None = None,
    host: str | None = None,
    cancel_requested: Callable[[], bool] | None = None,
    wait_for_cancel_ack: Callable[[float], bool] | None = None,
    cancel_ack_timeout: float = 1.0,
) -> None:
    """Bridge native ``stream_full`` with typed, inert structured data.

    REQUESTED, ACK and terminal cessation are distinct. A CANCELLED terminal is
    emitted only after the cancellation signal is observed locally and the
    transport ACK is confirmed. Model-emitted tool calls are assembled into
    explicit protobuf fields and are never executed here. Structured output is
    accepted only against a caller-authored schema and is transported as
    deterministic canonical JSON on the terminal frame.
    """
    validate_stream_request(request)
    request_schema = _request_response_schema(request)
    if response_schema is not None and request_schema is not None and dict(response_schema) != request_schema:
        raise _reject("explicit response schema conflicts with request response_schema_json")
    effective_schema = response_schema if response_schema is not None else request_schema
    if effective_schema is not None and emit_structured_output is None:
        # The protobuf terminal is always an explicit structured-output sink. The
        # callback is optional and exists only for direct bridge consumers/tests.
        pass
    if effective_schema is None and emit_structured_output is not None:
        raise _reject("structured-output sink requires a caller-supplied response schema")

    attest_pinned_artifact(artifact_path or _artifact_path())
    resolved_host = host or _loopback_host()
    parsed = urlparse(resolved_host)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_ENGINE_UNAVAILABLE,
            "non-loopback native endpoint rejected",
            retryable=False,
        )

    def cancellation_is_requested() -> bool:
        return bool(cancel_requested is not None and cancel_requested())

    def emit_cancelled(sequence: int, usage: inference_pb2.InferenceUsage) -> None:
        if wait_for_cancel_ack is None or not wait_for_cancel_ack(cancel_ack_timeout):
            raise UnaryInferenceRejected(
                inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                "local cancellation observed but transport ACK was not confirmed",
                retryable=False,
            )
        emit_terminal(
            inference_pb2.InferenceTerminal(
                contract_version=contract_version(),
                request_id=request.request_id,
                attempt_id=request.attempt_id,
                final_sequence=sequence,
                finish_reason=inference_pb2.INFERENCE_FINISH_REASON_CANCELLED,
                usage=usage,
            )
        )

    engine = None
    try:
        engine, message_type, role_type = engine_factory(resolved_host)
        messages = _messages(request, message_type, role_type)
        temperature = request.config.temperature if request.config.HasField("temperature") else 0.0
        typed_assembler = StructuredStreamAssembler()

        async def consume() -> None:
            sequence = 0
            finish_reason = inference_pb2.INFERENCE_FINISH_REASON_UNSPECIFIED
            usage = inference_pb2.InferenceUsage(
                measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN
            )
            saw_finish = False
            if cancellation_is_requested():
                emit_cancelled(sequence, usage)
                return
            async for native in engine.stream_full(
                messages,
                model=PINNED_MODEL_ID,
                temperature=float(temperature),
                max_tokens=int(request.config.max_output_tokens),
                chat_template_kwargs={"enable_thinking": False},
            ):
                if cancellation_is_requested():
                    emit_cancelled(sequence, usage)
                    return

                content = getattr(native, "content", None)
                tool_calls = getattr(native, "tool_calls", None)
                content_blocks = getattr(native, "content_blocks", None)
                tool_results = getattr(native, "tool_results", None)
                native_finish = getattr(native, "finish_reason", None)
                native_usage = getattr(native, "usage", None)

                if saw_finish and any(
                    value not in (None, [], {}, "")
                    for value in (content, tool_calls, content_blocks, tool_results, native_finish, native_usage)
                ):
                    raise UnaryInferenceRejected(
                        inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                        "native stream emitted data after finish_reason",
                        retryable=False,
                    )
                if content_blocks or tool_results:
                    raise UnaryInferenceRejected(
                        inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                        "content_blocks/tool_results are not yet mapped into the canonical W02-13 transport",
                        retryable=False,
                    )
                if tool_calls:
                    typed_assembler.feed_tool_calls(tool_calls)
                if content is not None:
                    if not isinstance(content, str):
                        raise UnaryInferenceRejected(
                            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                            "native streaming content must be text",
                            retryable=False,
                        )
                    if content:
                        if effective_schema is not None:
                            typed_assembler.feed_text(content)
                        sequence += 1
                        emit_chunk(
                            inference_pb2.InferenceChunk(
                                contract_version=contract_version(),
                                request_id=request.request_id,
                                attempt_id=request.attempt_id,
                                sequence=sequence,
                                text_delta=content,
                            )
                        )
                if native_usage is not None:
                    usage = _usage(native_usage)
                if native_finish is not None:
                    if saw_finish:
                        raise UnaryInferenceRejected(
                            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                            "native stream emitted duplicate finish_reason",
                            retryable=False,
                        )
                    finish_reason = _finish_reason(native_finish)
                    saw_finish = True
                if cancellation_is_requested():
                    emit_cancelled(sequence, usage)
                    return

            if cancellation_is_requested():
                emit_cancelled(sequence, usage)
                return

            structured_value, assembled_calls = typed_assembler.finalize(
                response_schema=effective_schema
            )
            if finish_reason == inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL and not assembled_calls:
                raise StructuredOutputRejected(
                    "tool-call finish_reason was emitted without any assembled tool call"
                )
            if assembled_calls and finish_reason != inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL:
                raise StructuredOutputRejected(
                    "assembled tool-call data requires tool_calls finish_reason"
                )
            if emit_tool_call is not None:
                for call in assembled_calls:
                    emit_tool_call(call)
            if effective_schema is not None and emit_structured_output is not None:
                emit_structured_output(structured_value)

            if sequence == 0 and not assembled_calls:
                raise UnaryInferenceRejected(
                    inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                    "native stream ended without content chunks or typed tool-call data",
                    retryable=False,
                )
            emit_terminal(
                _typed_terminal(
                    request=request,
                    sequence=sequence,
                    finish_reason=finish_reason,
                    usage=usage,
                    calls=assembled_calls,
                    structured_value=structured_value,
                )
            )

        asyncio.run(consume())
    except StructuredOutputRejected as exc:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
            f"structured model output rejected: {exc}",
            retryable=False,
        ) from exc
    except UnaryInferenceRejected:
        raise
    except Exception as exc:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_ENGINE_UNAVAILABLE,
            f"native OpenJarvis streaming execution failed: {type(exc).__name__}: {exc}",
            retryable=False,
        ) from exc
    finally:
        if engine is not None:
            close = getattr(engine, "close", None)
            if callable(close):
                with contextlib.suppress(Exception):
                    close()
