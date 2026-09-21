from __future__ import annotations

import argparse
import contextlib
import importlib
import inspect
import json
from pathlib import Path
import struct
import sys
import threading
import time
from typing import BinaryIO, Iterable

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "contracts/sdk/python/gen"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(GENERATED) not in sys.path:
    sys.path.insert(0, str(GENERATED))

from adapters.openjarvis import ADAPTER_ID, RUNTIME_ID, UPSTREAM_COMMIT, UPSTREAM_REPOSITORY
from adapters.openjarvis.streaming_inference import execute_stream
from adapters.openjarvis.unary_inference import UnaryInferenceRejected, execute_unary
from clever.v1 import adapter_pb2, common_pb2, inference_pb2, runtime_pb2

MAX_FRAME_BYTES = 4 * 1024 * 1024
WIRE_MAJOR = 1
WIRE_MINOR = 1
class _ActiveInference:
    def __init__(self, request_id: str, attempt_id: str, frame_id: str) -> None:
        self.request_id = request_id
        self.attempt_id = attempt_id
        self.frame_id = frame_id
        self.cancel_requested = threading.Event()
        self.cancel_acknowledged = threading.Event()


class _InferenceCoordinator:
    """Single-flight request/attempt ownership for the W02-12 streaming lane."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: _ActiveInference | None = None
        self._last_terminal: tuple[str, str] | None = None

    def begin(self, request_id: str, attempt_id: str, frame_id: str) -> _ActiveInference | None:
        with self._lock:
            if self._active is not None:
                return None
            state = _ActiveInference(request_id, attempt_id, frame_id)
            self._active = state
            return state

    def busy(self) -> bool:
        with self._lock:
            return self._active is not None

    def request_cancel(self, request_id: str, attempt_id: str) -> tuple[str, _ActiveInference | None]:
        with self._lock:
            if (
                self._active is not None
                and self._active.request_id == request_id
                and self._active.attempt_id == attempt_id
            ):
                self._active.cancel_requested.set()
                return "REQUESTED", self._active
            if self._last_terminal == (request_id, attempt_id):
                return "ALREADY_TERMINAL", None
            return "NOT_ACTIVE", None

    def complete_normal(self, state: _ActiveInference) -> bool:
        with self._lock:
            if self._active is not state or state.cancel_requested.is_set():
                return False
            self._active = None
            self._last_terminal = (state.request_id, state.attempt_id)
            return True

    def complete_cancelled(self, state: _ActiveInference) -> None:
        with self._lock:
            if self._active is state:
                self._active = None
            self._last_terminal = (state.request_id, state.attempt_id)

    def fail(self, state: _ActiveInference) -> None:
        with self._lock:
            if self._active is state:
                self._active = None


_RESERVED_METADATA_TOKENS = (
    "permission",
    "scope",
    "risk",
    "policy",
    "authorization",
    "authz",
)

# These are registry-domain import hints, never provider/implementation allowlists.
# The registry contents themselves remain authoritative and are enumerated at runtime.
_REGISTRATION_IMPORT_HINTS = {
    "AgentRegistry": ("openjarvis.agents",),
    "BenchmarkRegistry": ("openjarvis.bench",),
    "ChannelRegistry": ("openjarvis.channels",),
    "CompressionRegistry": ("openjarvis.sessions.compression",),
    "ConnectorRegistry": ("openjarvis.connectors",),
    "EngineRegistry": ("openjarvis.engine",),
    "FactStoreRegistry": ("openjarvis.memory",),
    "LearningRegistry": ("openjarvis.learning.intelligence",),
    "MemoryRegistry": ("openjarvis.memory", "openjarvis.tools.storage"),
    "MinerRegistry": ("openjarvis.mining",),
    "ModelRegistry": ("openjarvis.intelligence",),
    "RouterPolicyRegistry": (
        "openjarvis.learning.routing.heuristic_policy",
        "openjarvis.learning.routing.learned_router",
    ),
    "SkillRegistry": ("openjarvis.skills",),
    "SpeechRegistry": ("openjarvis.speech",),
    "TTSRegistry": ("openjarvis.tools.text_to_speech",),
    "ToolRegistry": ("openjarvis.tools",),
}

_REGISTRY_PRIMITIVES = {
    "ModelRegistry": adapter_pb2.REGISTRY_PRIMITIVE_MODEL,
    "EngineRegistry": adapter_pb2.REGISTRY_PRIMITIVE_ENGINE,
    "MemoryRegistry": adapter_pb2.REGISTRY_PRIMITIVE_MEMORY,
    "FactStoreRegistry": adapter_pb2.REGISTRY_PRIMITIVE_FACT_STORE,
    "AgentRegistry": adapter_pb2.REGISTRY_PRIMITIVE_AGENT,
    "ToolRegistry": adapter_pb2.REGISTRY_PRIMITIVE_TOOL,
    "RouterPolicyRegistry": adapter_pb2.REGISTRY_PRIMITIVE_ROUTER_POLICY,
    "BenchmarkRegistry": adapter_pb2.REGISTRY_PRIMITIVE_BENCHMARK,
    "ChannelRegistry": adapter_pb2.REGISTRY_PRIMITIVE_CHANNEL,
    "LearningRegistry": adapter_pb2.REGISTRY_PRIMITIVE_LEARNING,
    "SkillRegistry": adapter_pb2.REGISTRY_PRIMITIVE_SKILL,
    "SpeechRegistry": adapter_pb2.REGISTRY_PRIMITIVE_SPEECH,
    "CompressionRegistry": adapter_pb2.REGISTRY_PRIMITIVE_COMPRESSION,
    "TTSRegistry": adapter_pb2.REGISTRY_PRIMITIVE_TTS,
    "ConnectorRegistry": adapter_pb2.REGISTRY_PRIMITIVE_CONNECTOR,
    "MinerRegistry": adapter_pb2.REGISTRY_PRIMITIVE_MINER,
}


def contract_version() -> common_pb2.ContractVersion:
    return common_pb2.ContractVersion(major=WIRE_MAJOR, minor=WIRE_MINOR)


def is_reserved_metadata_key(key: str) -> bool:
    normalized = key.casefold()
    return any(token in normalized for token in _RESERVED_METADATA_TOKENS)


def sanitize_metadata(metadata: dict[str, str]) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in sorted(metadata.items())
        if not is_reserved_metadata_key(str(key))
    }


def _import_registry_domains(registry_names: Iterable[str]) -> list[str]:
    failures: list[str] = []
    seen: set[str] = set()
    for registry_name in sorted(registry_names):
        for module_name in _REGISTRATION_IMPORT_HINTS.get(registry_name, ()):  # domain hint only
            if module_name in seen:
                continue
            seen.add(module_name)
            try:
                # Third-party import-time chatter must never corrupt stdout framing.
                with contextlib.redirect_stdout(sys.stderr):
                    module = importlib.import_module(module_name)
                    if module_name == "openjarvis.intelligence":
                        register_builtin = getattr(module, "register_builtin_models", None)
                        if callable(register_builtin):
                            register_builtin()
            except Exception as exc:  # optional extras/platform bindings may fail at import
                failures.append(f"{module_name}:{type(exc).__name__}")
    return sorted(failures)


def _registry_classes() -> list[tuple[str, type]]:
    registry_module = importlib.import_module("openjarvis.core.registry")
    registry_base = getattr(registry_module, "RegistryBase")
    classes: list[tuple[str, type]] = []
    for name, candidate in vars(registry_module).items():
        if (
            name.endswith("Registry")
            and inspect.isclass(candidate)
            and candidate is not registry_base
            and issubclass(candidate, registry_base)
        ):
            classes.append((name, candidate))
    return sorted(classes, key=lambda item: item[0])


def _entry_identity(entry: object) -> tuple[str, str]:
    if inspect.isclass(entry) or inspect.isfunction(entry):
        module = getattr(entry, "__module__", type(entry).__module__)
        qualname = getattr(entry, "__qualname__", getattr(entry, "__name__", type(entry).__name__))
        return f"{module}.{qualname}", type(entry).__name__
    entry_type = type(entry)
    return f"{entry_type.__module__}.{entry_type.__qualname__}", entry_type.__name__


def discover_registry_snapshot() -> tuple[adapter_pb2.RegistrySnapshot, dict[str, object]]:
    classes = _registry_classes()
    registry_names = [name for name, _ in classes]
    import_failures = _import_registry_domains(registry_names)

    # Imports may have populated the same class objects; enumerate only after import.
    classes = _registry_classes()
    entries: list[adapter_pb2.NativeRegistryEntry] = []
    unsupported_registries: list[str] = []
    registry_counts: dict[str, int] = {}
    for registry_name, registry_cls in classes:
        primitive = _REGISTRY_PRIMITIVES.get(registry_name)
        if primitive is None:
            unsupported_registries.append(registry_name)
            continue
        native_items = sorted(registry_cls.items(), key=lambda item: str(item[0]))
        registry_counts[registry_name] = len(native_items)
        for key, entry in native_items:
            implementation, native_type = _entry_identity(entry)
            metadata = sanitize_metadata(
                {
                    "registry_class": registry_name,
                    "entry_module": getattr(entry, "__module__", type(entry).__module__),
                    "entry_qualname": getattr(
                        entry,
                        "__qualname__",
                        getattr(entry, "__name__", type(entry).__qualname__),
                    ),
                }
            )
            entries.append(
                adapter_pb2.NativeRegistryEntry(
                    primitive=primitive,
                    key=str(key),
                    implementation=implementation,
                    native_type=native_type,
                    metadata=metadata,
                )
            )

    entries.sort(key=lambda row: (row.primitive, row.key, row.implementation))
    snapshot = adapter_pb2.RegistrySnapshot(runtime_id=RUNTIME_ID, entries=entries)
    diagnostics: dict[str, object] = {
        "schema_version": 1,
        "source_repo": "openjarvis",
        "upstream_repository": UPSTREAM_REPOSITORY,
        "upstream_commit": UPSTREAM_COMMIT,
        "registry_class_count": len(classes),
        "registry_counts": dict(sorted(registry_counts.items())),
        "entry_count": len(entries),
        "import_failures": import_failures,
        "unsupported_registries": sorted(unsupported_registries),
        "entries": [
            {
                "primitive": adapter_pb2.RegistryPrimitive.Name(row.primitive),
                "key": row.key,
                "implementation": row.implementation,
                "native_type": row.native_type,
                "metadata": dict(sorted(row.metadata.items())),
            }
            for row in entries
        ],
    }
    return snapshot, diagnostics


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError(f"truncated adapter frame: expected {size} bytes")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(stream: BinaryIO, *, max_frame_bytes: int = MAX_FRAME_BYTES) -> adapter_pb2.AdapterFrame | None:
    prefix = stream.read(4)
    if prefix == b"":
        return None
    if len(prefix) != 4:
        raise EOFError("truncated adapter frame length prefix")
    (length,) = struct.unpack(">I", prefix)
    if length == 0 or length > max_frame_bytes:
        raise ValueError(f"adapter frame length {length} outside allowed range")
    payload = _read_exact(stream, length)
    frame = adapter_pb2.AdapterFrame()
    frame.ParseFromString(payload)
    if frame.contract_version.major != WIRE_MAJOR:
        raise ValueError(f"unsupported Clever adapter major {frame.contract_version.major}")
    return frame


def write_frame(stream: BinaryIO, frame: adapter_pb2.AdapterFrame, *, max_frame_bytes: int = MAX_FRAME_BYTES) -> None:
    payload = frame.SerializeToString(deterministic=True)
    if not payload or len(payload) > max_frame_bytes:
        raise ValueError(f"adapter frame length {len(payload)} outside allowed range")
    stream.write(struct.pack(">I", len(payload)))
    stream.write(payload)
    stream.flush()


def _now_timestamp() -> tuple[int, int]:
    now = time.time_ns()
    return divmod(now, 1_000_000_000)


def _stamp(message: object) -> None:
    seconds, nanos = _now_timestamp()
    target = getattr(message, "sent_at", None)
    if target is not None:
        target.seconds = seconds
        target.nanos = nanos


def _frame(frame_id: str, body_name: str, body: object, *, correlation_id: str = "") -> adapter_pb2.AdapterFrame:
    frame = adapter_pb2.AdapterFrame(
        contract_version=contract_version(),
        frame_id=frame_id,
        correlation_id=correlation_id,
    )
    _stamp(frame)
    getattr(frame, body_name).CopyFrom(body)
    return frame


def hello_frame() -> adapter_pb2.AdapterFrame:
    hello = adapter_pb2.AdapterHello(
        contract_version=contract_version(),
        adapter_id=ADAPTER_ID,
        runtime=runtime_pb2.RuntimeDescriptor(
            contract_version=contract_version(),
            runtime_id=RUNTIME_ID,
            runtime_kind="python-sidecar",
            implementation_version=UPSTREAM_COMMIT[:12],
            process_id=str(__import__("os").getpid()),
        ),
        upstream_repository=UPSTREAM_REPOSITORY,
        upstream_commit=UPSTREAM_COMMIT,
        max_frame_bytes=MAX_FRAME_BYTES,
        supported_features=[
            "be32-length-prefix",
            "registry-snapshot",
            "runtime-health",
            "cancel",
            "shutdown",
            "unary-inference",
            "streaming-inference",
            "streaming-cancellation",
        ],
    )
    return _frame("openjarvis-hello", "hello", hello)


def health_frame(*, degraded: bool = False, reasons: Iterable[str] = (), correlation_id: str = "") -> adapter_pb2.AdapterFrame:
    seconds, nanos = _now_timestamp()
    reason_list = sorted(set(str(reason) for reason in reasons if str(reason)))
    status = (
        runtime_pb2.RUNTIME_HEALTH_STATUS_DEGRADED
        if degraded or reason_list
        else runtime_pb2.RUNTIME_HEALTH_STATUS_READY
    )
    health = runtime_pb2.RuntimeHealth(
        contract_version=contract_version(),
        runtime_id=RUNTIME_ID,
        status=status,
        degradation_reasons=reason_list,
        dropped_event_count=0,
        failed_action_count=0,
    )
    health.observed_at.seconds = seconds
    health.observed_at.nanos = nanos
    return _frame("openjarvis-health", "health", health, correlation_id=correlation_id)


def run_protocol(stdin: BinaryIO, stdout: BinaryIO) -> int:
    snapshot, diagnostics = discover_registry_snapshot()
    write_frame(stdout, hello_frame())
    first = read_frame(stdin)
    if first is None or first.WhichOneof("body") != "hello_ack" or not first.hello_ack.accepted:
        return 64

    write_lock = threading.Lock()
    coordinator = _InferenceCoordinator()

    def send(frame: adapter_pb2.AdapterFrame) -> None:
        with write_lock:
            write_frame(stdout, frame)

    def adapter_error(request: adapter_pb2.AdapterFrame, code: str, message: str) -> None:
        send(
            _frame(
                f"adapter-error:{request.frame_id}",
                "error",
                adapter_pb2.AdapterError(code=code, message=message, retryable=False),
                correlation_id=request.frame_id,
            )
        )

    def inference_error(request: adapter_pb2.AdapterFrame, code: int, message: str) -> None:
        native = request.inference_request
        send(
            _frame(
                f"inference-error:{request.frame_id}",
                "inference_error",
                inference_pb2.InferenceError(
                    contract_version=common_pb2.ContractVersion(major=1, minor=2),
                    request_id=native.request_id,
                    attempt_id=native.attempt_id,
                    code=code,
                    message=message,
                    retryable=False,
                ),
                correlation_id=request.frame_id,
            )
        )

    def start_stream(request: adapter_pb2.AdapterFrame) -> bool:
        native_request = request.inference_request
        state = coordinator.begin(native_request.request_id, native_request.attempt_id, request.frame_id)
        if state is None:
            inference_error(
                request,
                inference_pb2.INFERENCE_ERROR_CODE_BUSY,
                "W02-12 sidecar is explicit single-flight; another inference is active",
            )
            return False

        def worker() -> None:
            def emit_chunk(chunk: inference_pb2.InferenceChunk) -> None:
                send(
                    _frame(
                        f"inference-chunk:{request.frame_id}:{chunk.sequence}",
                        "inference_chunk",
                        chunk,
                        correlation_id=request.frame_id,
                    )
                )

            def emit_terminal(terminal: inference_pb2.InferenceTerminal) -> None:
                if terminal.finish_reason == inference_pb2.INFERENCE_FINISH_REASON_CANCELLED:
                    if not state.cancel_acknowledged.wait(1.0):
                        raise UnaryInferenceRejected(
                            inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                            "cancelled terminal attempted before transport ACK",
                            retryable=False,
                        )
                    coordinator.complete_cancelled(state)
                    send(
                        _frame(
                            f"inference-terminal:{request.frame_id}",
                            "inference_terminal",
                            terminal,
                            correlation_id=request.frame_id,
                        )
                    )
                    return

                if coordinator.complete_normal(state):
                    send(
                        _frame(
                            f"inference-terminal:{request.frame_id}",
                            "inference_terminal",
                            terminal,
                            correlation_id=request.frame_id,
                        )
                    )
                    return

                if not state.cancel_requested.is_set() or not state.cancel_acknowledged.wait(1.0):
                    raise UnaryInferenceRejected(
                        inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
                        "stream terminal raced cancellation without an ACK",
                        retryable=False,
                    )
                cancelled = inference_pb2.InferenceTerminal(
                    contract_version=common_pb2.ContractVersion(major=1, minor=2),
                    request_id=native_request.request_id,
                    attempt_id=native_request.attempt_id,
                    final_sequence=terminal.final_sequence,
                    finish_reason=inference_pb2.INFERENCE_FINISH_REASON_CANCELLED,
                    usage=inference_pb2.InferenceUsage(
                        measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN
                    ),
                )
                coordinator.complete_cancelled(state)
                send(
                    _frame(
                        f"inference-terminal:{request.frame_id}",
                        "inference_terminal",
                        cancelled,
                        correlation_id=request.frame_id,
                    )
                )

            try:
                execute_stream(
                    native_request,
                    emit_chunk=emit_chunk,
                    emit_terminal=emit_terminal,
                    cancel_requested=state.cancel_requested.is_set,
                    wait_for_cancel_ack=state.cancel_acknowledged.wait,
                )
            except UnaryInferenceRejected as exc:
                send(
                    _frame(
                        f"inference-error:{request.frame_id}",
                        "inference_error",
                        inference_pb2.InferenceError(
                            contract_version=common_pb2.ContractVersion(major=1, minor=2),
                            request_id=native_request.request_id,
                            attempt_id=native_request.attempt_id,
                            code=exc.code,
                            message=str(exc),
                            retryable=exc.retryable,
                        ),
                        correlation_id=request.frame_id,
                    )
                )
            finally:
                coordinator.fail(state)

        threading.Thread(target=worker, name=f"openjarvis-stream-{native_request.attempt_id}", daemon=True).start()
        return True

    while True:
        request = read_frame(stdin)
        if request is None:
            return 0
        body = request.WhichOneof("body")
        if body == "registry_snapshot_request":
            response = _frame(
                f"registry:{request.frame_id}",
                "registry_snapshot",
                snapshot,
                correlation_id=request.frame_id,
            )
            send(response)
        elif body == "health_request":
            send(health_frame(reasons=diagnostics["unsupported_registries"], correlation_id=request.frame_id))
        elif body == "cancel":
            # Legacy adapter-control cancellation remains a no-op health acknowledgement.
            send(health_frame(correlation_id=request.frame_id))
        elif body == "inference_cancel":
            cancel = request.inference_cancel
            if (
                not cancel.HasField("contract_version")
                or cancel.contract_version.major != 1
                or cancel.contract_version.minor > 2
                or not cancel.target_request_id.strip()
                or not cancel.target_attempt_id.strip()
                or not cancel.reason.strip()
            ):
                adapter_error(request, "CANCEL_INVALID", "inference cancellation target/reason is invalid")
                continue
            status, state = coordinator.request_cancel(cancel.target_request_id, cancel.target_attempt_id)
            if status == "REQUESTED" and state is not None:
                send(
                    _frame(
                        f"inference-cancel-ack:{request.frame_id}",
                        "inference_cancel",
                        cancel,
                        correlation_id=request.frame_id,
                    )
                )
                state.cancel_acknowledged.set()
            elif status == "ALREADY_TERMINAL":
                adapter_error(
                    request,
                    "CANCEL_ALREADY_TERMINAL",
                    "target request/attempt already reached a terminal state",
                )
            else:
                adapter_error(
                    request,
                    "CANCEL_NOT_ACTIVE",
                    "target request/attempt is not the active single-flight inference",
                )
        elif body == "inference_request":
            native_request = request.inference_request
            if native_request.HasField("config") and native_request.config.stream:
                start_stream(request)
                continue
            if coordinator.busy():
                inference_error(
                    request,
                    inference_pb2.INFERENCE_ERROR_CODE_BUSY,
                    "W02-12 sidecar is explicit single-flight; another inference is active",
                )
                continue
            try:
                outcome = execute_unary(native_request)
            except UnaryInferenceRejected as exc:
                send(
                    _frame(
                        f"inference-error:{request.frame_id}",
                        "inference_error",
                        inference_pb2.InferenceError(
                            contract_version=common_pb2.ContractVersion(major=1, minor=2),
                            request_id=native_request.request_id,
                            attempt_id=native_request.attempt_id,
                            code=exc.code,
                            message=str(exc),
                            retryable=exc.retryable,
                        ),
                        correlation_id=request.frame_id,
                    )
                )
                continue
            send(
                _frame(
                    f"inference-chunk:{request.frame_id}",
                    "inference_chunk",
                    outcome.chunk,
                    correlation_id=request.frame_id,
                )
            )
            send(
                _frame(
                    f"inference-terminal:{request.frame_id}",
                    "inference_terminal",
                    outcome.terminal,
                    correlation_id=request.frame_id,
                )
            )
        elif body == "shutdown":
            seconds, nanos = _now_timestamp()
            stopping = runtime_pb2.RuntimeHealth(
                contract_version=contract_version(),
                runtime_id=RUNTIME_ID,
                status=runtime_pb2.RUNTIME_HEALTH_STATUS_STOPPING,
            )
            stopping.observed_at.seconds = seconds
            stopping.observed_at.nanos = nanos
            send(_frame("openjarvis-stopping", "health", stopping, correlation_id=request.frame_id))
            return 0
        else:
            adapter_error(request, "UNSUPPORTED_BODY", str(body))

def main() -> int:
    parser = argparse.ArgumentParser(description="Clever OpenJarvis supervised sidecar")
    parser.add_argument("--dump-registry", action="store_true")
    args = parser.parse_args()
    if args.dump_registry:
        _, diagnostics = discover_registry_snapshot()
        print(json.dumps(diagnostics, sort_keys=True, separators=(",", ":")))
        return 0
    return run_protocol(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
