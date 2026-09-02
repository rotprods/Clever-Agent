from __future__ import annotations

import os
import struct
import sys
import time

from clever.v1 import adapter_pb2, common_pb2, runtime_pb2

MAX = 4 * 1024 * 1024


def version(major: int = 1) -> common_pb2.ContractVersion:
    return common_pb2.ContractVersion(major=major, minor=1)


def write_frame(frame: adapter_pb2.AdapterFrame) -> None:
    payload = frame.SerializeToString(deterministic=True)
    sys.stdout.buffer.write(struct.pack(">I", len(payload)))
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


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
