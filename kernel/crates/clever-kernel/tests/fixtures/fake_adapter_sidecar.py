from __future__ import annotations

import os
import struct
import sys
import time

from clever.v1 import adapter_pb2, common_pb2, inference_pb2, runtime_pb2

MAX = 4 * 1024 * 1024


def version(major: int = 1) -> common_pb2.ContractVersion:
    return common_pb2.ContractVersion(major=major, minor=1)


def write_frame(frame: adapter_pb2.AdapterFrame) -> None:
    payload = frame.SerializeToString(deterministic=True)
    sys.stdout.buffer.write(struct.pack(">I", len(payload)))
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def framed_bytes(value: adapter_pb2.AdapterFrame) -> bytes:
    payload = value.SerializeToString(deterministic=True)
    return struct.pack(">I", len(payload)) + payload


def write_fragmented_utf8_frame(value: adapter_pb2.AdapterFrame) -> None:
    wire = framed_bytes(value)
    needle = "hé".encode("utf-8")
    index = wire.find(needle)
    if index < 0:
        raise SystemExit(92)
    split = index + 2  # after ASCII h plus first byte (0xc3) of é
    sys.stdout.buffer.write(wire[:split])
    sys.stdout.buffer.flush()
    time.sleep(0.01)
    sys.stdout.buffer.write(wire[split:])
    sys.stdout.buffer.flush()


def write_coalesced(*values: adapter_pb2.AdapterFrame) -> None:
    sys.stdout.buffer.write(b"".join(framed_bytes(value) for value in values))
    sys.stdout.buffer.flush()


def inference_version() -> common_pb2.ContractVersion:
    return common_pb2.ContractVersion(major=1, minor=2)


def stream_chunk(request, sequence: int, text: str) -> adapter_pb2.AdapterFrame:
    body = inference_pb2.InferenceChunk(
        contract_version=inference_version(),
        request_id=request.request_id,
        attempt_id=request.attempt_id,
        sequence=sequence,
        text_delta=text,
    )
    return frame(
        f"stream-chunk-{sequence}",
        "inference_chunk",
        body,
        correlation_id="__REQUEST_FRAME__",
    )


def stream_terminal(request, final_sequence: int) -> adapter_pb2.AdapterFrame:
    body = inference_pb2.InferenceTerminal(
        contract_version=inference_version(),
        request_id=request.request_id,
        attempt_id=request.attempt_id,
        final_sequence=final_sequence,
        finish_reason=inference_pb2.INFERENCE_FINISH_REASON_STOP,
        usage=inference_pb2.InferenceUsage(
            measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN
        ),
    )
    return frame(
        "stream-terminal",
        "inference_terminal",
        body,
        correlation_id="__REQUEST_FRAME__",
    )


def cancelled_terminal(request, final_sequence: int) -> adapter_pb2.AdapterFrame:
    body = inference_pb2.InferenceTerminal(
        contract_version=inference_version(),
        request_id=request.request_id,
        attempt_id=request.attempt_id,
        final_sequence=final_sequence,
        finish_reason=inference_pb2.INFERENCE_FINISH_REASON_CANCELLED,
        usage=inference_pb2.InferenceUsage(
            measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN
        ),
    )
    return frame(
        "stream-cancelled-terminal",
        "inference_terminal",
        body,
        correlation_id="__REQUEST_FRAME__",
    )


def require_cancel(envelope, request):
    cancel_frame = read_frame()
    if cancel_frame is None or cancel_frame.WhichOneof("body") != "inference_cancel":
        raise SystemExit(93)
    cancel = cancel_frame.inference_cancel
    if cancel.target_request_id != request.request_id or cancel.target_attempt_id != request.attempt_id:
        raise SystemExit(94)
    ack = frame(
        f"cancel-ack:{cancel_frame.frame_id}",
        "inference_cancel",
        cancel,
        correlation_id=cancel_frame.frame_id,
    )
    write_frame(ack)
    return cancel_frame


def read_frame() -> adapter_pb2.AdapterFrame | None:
    prefix = sys.stdin.buffer.read(4)
    if not prefix:
        return None
    if len(prefix) != 4:
        raise SystemExit(90)
    (length,) = struct.unpack(">I", prefix)
    payload = sys.stdin.buffer.read(length)
    if len(payload) != length:
        raise SystemExit(91)
    frame = adapter_pb2.AdapterFrame()
    frame.ParseFromString(payload)
    return frame


def frame(frame_id: str, body_name: str, body: object, *, major: int = 1, correlation_id: str = "") -> adapter_pb2.AdapterFrame:
    result = adapter_pb2.AdapterFrame(
        contract_version=version(major),
        frame_id=frame_id,
        correlation_id=correlation_id,
    )
    getattr(result, body_name).CopyFrom(body)
    return result


def hello(major: int = 1) -> adapter_pb2.AdapterFrame:
    message = adapter_pb2.AdapterHello(
        contract_version=version(major),
        adapter_id="fake.adapter",
        runtime=runtime_pb2.RuntimeDescriptor(
            contract_version=version(major),
            runtime_id="fake-runtime",
            runtime_kind="python-test-sidecar",
            implementation_version="fake-1",
            process_id=str(os.getpid()),
        ),
        upstream_repository="https://example.invalid/fake",
        upstream_commit="fake-commit",
        max_frame_bytes=MAX,
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
    return frame("fake-hello", "hello", message, major=major)


def health(status: int) -> runtime_pb2.RuntimeHealth:
    return runtime_pb2.RuntimeHealth(
        contract_version=version(),
        runtime_id="fake-runtime",
        status=status,
    )


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "valid"
    if mode == "crash":
        return 23
    if mode == "silent":
        time.sleep(2)
        return 0
    if mode == "oversized":
        sys.stdout.buffer.write(struct.pack(">I", MAX + 1))
        sys.stdout.buffer.flush()
        return 0
    if mode == "partial":
        sys.stdout.buffer.write(struct.pack(">I", 16) + b"abc")
        sys.stdout.buffer.flush()
        return 0
    if mode == "unknown-major":
        write_frame(hello(9))
        return 0

    write_frame(hello())
    ack = read_frame()
    if ack is None or ack.WhichOneof("body") != "hello_ack" or not ack.hello_ack.accepted:
        return 64

    if mode == "flood":
        time.sleep(0.15)
        for index in range(64):
            write_frame(
                frame(
                    f"flood-{index}",
                    "health",
                    health(runtime_pb2.RUNTIME_HEALTH_STATUS_READY),
                )
            )
        time.sleep(2)
        return 0
    if mode == "byte-flood":
        time.sleep(0.15)
        error = adapter_pb2.AdapterError(
            code="BYTE_FLOOD",
            message="x" * 8192,
            retryable=False,
        )
        write_frame(frame("byte-flood", "error", error))
        time.sleep(2)
        return 0
    if mode == "no-read-after-hello":
        time.sleep(5)
        return 0

    if mode.startswith("stream-"):
        envelope = read_frame()
        if envelope is None or envelope.WhichOneof("body") != "inference_request":
            return 65
        request = envelope.inference_request
        first = stream_chunk(request, 1, "hé")
        second = stream_chunk(request, 2, "llo")
        terminal = stream_terminal(request, 2)
        for value in (first, second, terminal):
            value.correlation_id = envelope.frame_id
        if mode == "stream-valid":
            write_fragmented_utf8_frame(first)
            write_coalesced(second, terminal)
            return 0
        if mode == "stream-duplicate":
            duplicate = stream_chunk(request, 1, "duplicate")
            duplicate.correlation_id = envelope.frame_id
            write_coalesced(first, duplicate, terminal)
            return 0
        if mode == "stream-reordered":
            write_coalesced(second, terminal)
            return 0
        if mode == "stream-eof":
            write_frame(first)
            return 0
        if mode == "stream-cancel-before":
            require_cancel(envelope, request)
            cancelled = cancelled_terminal(request, 0)
            cancelled.correlation_id = envelope.frame_id
            write_frame(cancelled)
            return 0
        if mode == "stream-cancel-during":
            write_frame(first)
            require_cancel(envelope, request)
            cancelled = cancelled_terminal(request, 1)
            cancelled.correlation_id = envelope.frame_id
            write_frame(cancelled)
            return 0
        if mode == "stream-cancel-ignore":
            write_frame(first)
            require_cancel(envelope, request)
            time.sleep(2)
            return 0
        if mode == "stream-cancel-after-terminal":
            one_terminal = stream_terminal(request, 1)
            one_terminal.correlation_id = envelope.frame_id
            write_coalesced(first, one_terminal)
            cancel_frame = read_frame()
            if cancel_frame is None or cancel_frame.WhichOneof("body") != "inference_cancel":
                return 67
            error = adapter_pb2.AdapterError(
                code="CANCEL_ALREADY_TERMINAL",
                message="target already terminal",
                retryable=False,
            )
            write_frame(
                frame(
                    f"cancel-error:{cancel_frame.frame_id}",
                    "error",
                    error,
                    correlation_id=cancel_frame.frame_id,
                )
            )
            time.sleep(0.2)
            return 0
        return 66

    while True:
        request = read_frame()
        if request is None:
            return 0
        body = request.WhichOneof("body")
        if body == "registry_snapshot_request":
            entry = adapter_pb2.NativeRegistryEntry(
                primitive=adapter_pb2.REGISTRY_PRIMITIVE_ENGINE,
                key="fake-engine",
                implementation="fake.module.Engine",
                native_type="type",
                metadata={
                    "registry_class": "EngineRegistry",
                    "policy_override": "allow",
                    "secret_seen": str(bool(os.getenv("CLEVER_TEST_SECRET"))).lower(),
                },
            )
            snapshot = adapter_pb2.RegistrySnapshot(runtime_id="fake-runtime", entries=[entry])
            write_frame(frame(f"registry:{request.frame_id}", "registry_snapshot", snapshot, correlation_id=request.frame_id))
        elif body == "health_request" or body == "cancel":
            write_frame(frame(f"health:{request.frame_id}", "health", health(runtime_pb2.RUNTIME_HEALTH_STATUS_READY), correlation_id=request.frame_id))
        elif body == "shutdown":
            write_frame(frame(f"shutdown:{request.frame_id}", "health", health(runtime_pb2.RUNTIME_HEALTH_STATUS_STOPPING), correlation_id=request.frame_id))
            return 0
        else:
            error = adapter_pb2.AdapterError(code="UNSUPPORTED", message=str(body), retryable=False)
            write_frame(frame(f"error:{request.frame_id}", "error", error, correlation_id=request.frame_id))


if __name__ == "__main__":
    raise SystemExit(main())
