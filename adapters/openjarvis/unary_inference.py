from __future__ import annotations

from dataclasses import dataclass
import contextlib
import hashlib
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable
from urllib.parse import urlparse

from clever.v1 import common_pb2, inference_pb2

WIRE_MAJOR = 1
WIRE_MINOR = 2
PINNED_ENGINE_ID = "llamacpp"
PINNED_MODEL_ID = "qwen3:0.6b"
PINNED_ARTIFACT_FILENAME = "Qwen_Qwen3-0.6B-Q4_K_M.gguf"
PINNED_ARTIFACT_SIZE = 484_220_320
PINNED_ARTIFACT_SHA256 = "9acfc1e001311f34b4252001b626f2e466d592a42065f66571bff3790d4e1b14"
PINNED_ARTIFACT_MAGIC = b"GGUF"


class UnaryInferenceRejected(RuntimeError):
    def __init__(self, code: int, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class UnaryInferenceOutcome:
    chunk: inference_pb2.InferenceChunk
    terminal: inference_pb2.InferenceTerminal


def contract_version() -> common_pb2.ContractVersion:
    return common_pb2.ContractVersion(major=WIRE_MAJOR, minor=WIRE_MINOR)


def _reject(message: str) -> UnaryInferenceRejected:
    return UnaryInferenceRejected(
        inference_pb2.INFERENCE_ERROR_CODE_INVALID_REQUEST,
        message,
        retryable=False,
    )


def validate_unary_request(request: inference_pb2.InferenceRequest) -> None:
    if not request.HasField("contract_version") or request.contract_version.major != WIRE_MAJOR:
        raise _reject("unsupported or missing inference contract version")
    if request.contract_version.minor > WIRE_MINOR:
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
            "W02-10 accepts only the exact W02-09 pinned engine/model lane",
            retryable=False,
        )
    if not request.HasField("config"):
        raise _reject("config is required")
    if request.config.stream:
        raise _reject("stream=true belongs to W02-11 and is unavailable in W02-10")
    if request.config.max_output_tokens <= 0:
        raise _reject("max_output_tokens must be positive")
    if request.config.max_output_tokens > 256:
        raise _reject("W02-10 unary max_output_tokens exceeds the bounded lane limit")
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


def _artifact_path() -> Path:
    raw = os.environ.get("CLEVER_W02_MODEL_PATH", "").strip()
    if not raw:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_MODEL_UNAVAILABLE,
            "CLEVER_W02_MODEL_PATH is required",
            retryable=False,
        )
    return Path(raw)


def attest_pinned_artifact(path: Path) -> None:
    if path.name != PINNED_ARTIFACT_FILENAME or not path.is_file():
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_MODEL_UNAVAILABLE,
            "pinned W02-09 GGUF artifact is missing",
            retryable=False,
        )
    if path.stat().st_size != PINNED_ARTIFACT_SIZE:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_MODEL_UNAVAILABLE,
            "pinned W02-09 GGUF size mismatch",
            retryable=False,
        )
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        magic = handle.read(4)
        if magic != PINNED_ARTIFACT_MAGIC:
            raise UnaryInferenceRejected(
                inference_pb2.INFERENCE_ERROR_CODE_MODEL_UNAVAILABLE,
                "pinned W02-09 GGUF magic mismatch",
                retryable=False,
            )
        digest.update(magic)
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != PINNED_ARTIFACT_SHA256:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_MODEL_UNAVAILABLE,
            "pinned W02-09 GGUF SHA-256 mismatch",
            retryable=False,
        )


def _loopback_host() -> str:
    host = os.environ.get("LLAMACPP_HOST", "").strip()
    parsed = urlparse(host)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_ENGINE_UNAVAILABLE,
            "W02-10 llamacpp endpoint must be an explicit local loopback HTTP endpoint",
            retryable=False,
        )
    return host.rstrip("/")


def _native_engine_factory(host: str) -> tuple[Any, type, type]:
    with contextlib.redirect_stdout(sys.stderr):
        import openjarvis.engine  # noqa: F401
        import openjarvis.intelligence as intelligence
        from openjarvis.core.registry import EngineRegistry, ModelRegistry
        from openjarvis.core.types import Message, Role

        register_builtin = getattr(intelligence, "register_builtin_models", None)
        if callable(register_builtin):
            register_builtin()
        spec = ModelRegistry.get(PINNED_MODEL_ID)
        if PINNED_ENGINE_ID not in tuple(spec.supported_engines):
            raise RuntimeError("pinned model no longer advertises llamacpp support")
        engine = EngineRegistry.create(PINNED_ENGINE_ID, host=host, timeout=120.0)
    return engine, Message, Role


def _messages(request: inference_pb2.InferenceRequest, message_type: type, role_type: type) -> list[Any]:
    role_map = {
        inference_pb2.INFERENCE_ROLE_SYSTEM: role_type.SYSTEM,
        inference_pb2.INFERENCE_ROLE_USER: role_type.USER,
        inference_pb2.INFERENCE_ROLE_ASSISTANT: role_type.ASSISTANT,
        inference_pb2.INFERENCE_ROLE_TOOL: role_type.TOOL,
    }
    return [
        message_type(
            role=role_map[item.role],
            content=item.content,
            name=item.name or None,
        )
        for item in request.inputs
    ]


def _finish_reason(value: object) -> int:
    mapping = {
        "stop": inference_pb2.INFERENCE_FINISH_REASON_STOP,
        "length": inference_pb2.INFERENCE_FINISH_REASON_LENGTH,
        "content_filter": inference_pb2.INFERENCE_FINISH_REASON_CONTENT_FILTER,
    }
    reason = mapping.get(str(value))
    if reason is None:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
            f"unsupported native unary finish_reason {value!r}",
            retryable=False,
        )
    return reason


def _usage(raw: object) -> inference_pb2.InferenceUsage:
    if not isinstance(raw, dict):
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
            "native unary result did not provide usage",
            retryable=False,
        )
    values = {}
    for native, canonical in (
        ("prompt_tokens", "input_tokens"),
        ("completion_tokens", "output_tokens"),
        ("total_tokens", "total_tokens"),
    ):
        value = raw.get(native)
        if type(value) is not int or value < 0:
            raise UnaryInferenceRejected(
                inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                f"native unary usage field {native} is invalid",
                retryable=False,
            )
        values[canonical] = value
    return inference_pb2.InferenceUsage(
        measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_EXACT,
        **values,
    )


def execute_unary(
    request: inference_pb2.InferenceRequest,
    *,
    engine_factory: Callable[[str], tuple[Any, type, type]] = _native_engine_factory,
    artifact_path: Path | None = None,
    host: str | None = None,
) -> UnaryInferenceOutcome:
    # Critical ordering: malformed/unapproved input is rejected before any native
    # engine object is created or contacted.
    validate_unary_request(request)
    attest_pinned_artifact(artifact_path or _artifact_path())
    resolved_host = host or _loopback_host()
    parsed = urlparse(resolved_host)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_ENGINE_UNAVAILABLE,
            "non-loopback native endpoint rejected",
            retryable=False,
        )

    engine = None
    try:
        engine, message_type, role_type = engine_factory(resolved_host)
        messages = _messages(request, message_type, role_type)
        temperature = request.config.temperature if request.config.HasField("temperature") else 0.0
        result = engine.generate(
            messages,
            model=PINNED_MODEL_ID,
            temperature=float(temperature),
            max_tokens=int(request.config.max_output_tokens),
            # The W02-10 canonical contract has no reasoning-content surface. The
            # pinned Qwen3 template otherwise defaults to thinking mode, which can
            # consume the entire bounded completion in reasoning_content and leave
            # OpenJarvis' canonical `content` empty. Disable template thinking for
            # this unary lane so terminal visible text is preserved end-to-end.
            chat_template_kwargs={"enable_thinking": False},
        )
        if not isinstance(result, dict):
            raise UnaryInferenceRejected(
                inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                "native unary result must be a mapping",
                retryable=False,
            )
        content = result.get("content")
        if not isinstance(content, str) or not content.strip():
            raise UnaryInferenceRejected(
                inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                "native unary result content is empty",
                retryable=False,
            )
        chunk = inference_pb2.InferenceChunk(
            contract_version=contract_version(),
            request_id=request.request_id,
            attempt_id=request.attempt_id,
            sequence=1,
            text_delta=content,
        )
        terminal = inference_pb2.InferenceTerminal(
            contract_version=contract_version(),
            request_id=request.request_id,
            attempt_id=request.attempt_id,
            final_sequence=1,
            finish_reason=_finish_reason(result.get("finish_reason")),
            usage=_usage(result.get("usage")),
        )
        return UnaryInferenceOutcome(chunk=chunk, terminal=terminal)
    except UnaryInferenceRejected:
        raise
    except Exception as exc:
        raise UnaryInferenceRejected(
            inference_pb2.INFERENCE_ERROR_CODE_ENGINE_UNAVAILABLE,
            f"native OpenJarvis unary execution failed: {type(exc).__name__}: {exc}",
            retryable=False,
        ) from exc
    finally:
        if engine is not None:
            close = getattr(engine, "close", None)
            if callable(close):
                with contextlib.suppress(Exception):
                    close()
