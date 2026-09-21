from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from clever.v1 import inference_pb2

from adapters.openjarvis.structured_output import (
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
    """Bridge native ``stream_full`` while preserving cancellation and typed data truth.

    REQUESTED, ACK and terminal cessation are distinct. A CANCELLED terminal is
    emitted only after the cancellation signal is observed locally and the
    transport ACK is confirmed. Model-emitted tool calls are inert data: this
    function can assemble them into an explicit sink but has no execution path.
    Structured output is accepted only with a caller-supplied schema and sink.
    """
    validate_stream_request(request)
    if response_schema is not None and emit_structured_output is None:
        raise _reject("response_schema requires an explicit structured-output sink")
    if response_schema is None and emit_structured_output is not None:
        raise _reject("structured-output sink requires a caller-supplied response_schema")

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
        typed_assembler = (
            StructuredStreamAssembler()
            if emit_tool_call is not None or response_schema is not None
            else None
        )

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
                    if emit_tool_call is None or typed_assembler is None:
                        raise UnaryInferenceRejected(
                            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                            "W02-13 requires an explicit inert tool-call sink; model-emitted tools are never executed here",
                            retryable=False,
                        )
                    typed_assembler.feed_tool_calls(tool_calls)
                if content is not None:
                    if not isinstance(content, str):
                        raise UnaryInferenceRejected(
                            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                            "native streaming content must be text",
                            retryable=False,
                        )
                    if content:
                        if response_schema is not None:
                            assert typed_assembler is not None
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

            assembled_calls: tuple[ToolCallData, ...] = ()
            if typed_assembler is not None:
                structured_value, assembled_calls = typed_assembler.finalize(
                    response_schema=response_schema
                )
                if finish_reason == inference_pb2.INFERENCE_FINISH_REASON_TOOL_CALL and not assembled_calls:
                    raise StructuredOutputRejected(
                        "tool-call finish_reason was emitted without any assembled tool call"
                    )
                if emit_tool_call is not None:
                    for call in assembled_calls:
                        emit_tool_call(call)
                if response_schema is not None:
                    assert emit_structured_output is not None
                    emit_structured_output(structured_value)

            if sequence == 0 and not assembled_calls:
                raise UnaryInferenceRejected(
                    inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                    "native stream ended without content chunks or typed tool-call data",
                    retryable=False,
                )
            emit_terminal(
                inference_pb2.InferenceTerminal(
                    contract_version=contract_version(),
                    request_id=request.request_id,
                    attempt_id=request.attempt_id,
                    final_sequence=sequence,
                    finish_reason=finish_reason,
                    usage=usage,
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
