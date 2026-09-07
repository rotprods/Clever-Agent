"""Single-flight control protocol. Cancellation here is NOT inference cancellation."""
from __future__ import annotations

from collections import deque
from types import ModuleType
from typing import BinaryIO
import time


def serve(stdin: BinaryIO, stdout: BinaryIO, api: ModuleType) -> int:
    snapshot, diagnostics = api.discover_registry_snapshot()
    hello = api.hello_frame()
    api.write_frame(stdout, hello)
    first = api.read_frame(stdin)
    if first is None or first.WhichOneof("body") != "hello_ack":
        return 64
    ack = first.hello_ack
    required = set(hello.hello.supported_features)
    if (not ack.accepted or ack.adapter_id != api.ADAPTER_ID
            or first.correlation_id != hello.frame_id
            or ack.contract_version.major != api.WIRE_MAJOR
            or not 0 < ack.max_frame_bytes <= api.MAX_FRAME_BYTES
            or set(ack.negotiated_features) != required):
        return 64
    limit = ack.max_frame_bytes
    # Bounded replay cache. Deadline checks additionally reject expired older IDs;
    # durable epochs and inference attempt IDs remain a later contract task.
    recent: deque[str] = deque(maxlen=64)
    while True:
        request = api.read_frame(stdin, max_frame_bytes=limit)
        if request is None:
            return 0
        kind = request.WhichOneof("body")
        code = None
        if request.frame_id in recent or request.correlation_id:
            code = "INVALID_CONTROL_REQUEST"
        elif request.HasField("deadline_at"):
            deadline = request.deadline_at
            if not 0 <= deadline.nanos < 1_000_000_000:
                code = "INVALID_DEADLINE"
            elif deadline.seconds * 1_000_000_000 + deadline.nanos <= time.time_ns():
                code = "DEADLINE_EXCEEDED"
        if code:
            response = api._frame("unused", "error", api.adapter_pb2.AdapterError(code=code, message=code, retryable=False))
        elif kind == "registry_snapshot_request":
            response = api._frame("unused", "registry_snapshot", snapshot)
        elif kind in {"health_request", "cancel"}:
            # W01 control-only compatibility: no generation worker exists. A health
            # reply to cancel cannot be used as evidence of stopping inference.
            response = api.health_frame(reasons=diagnostics["unsupported_registries"])
        elif kind == "shutdown":
            response = api.health_frame()
            response.health.status = api.runtime_pb2.RUNTIME_HEALTH_STATUS_STOPPING
        else:
            response = api._frame("unused", "error", api.adapter_pb2.AdapterError(
                code="UNSUPPORTED_CONTROL_FRAME", message="No inference or tool execution in this control lane", retryable=False,
            ))
        response.frame_id = f"reply:{request.frame_id}"
        response.correlation_id = request.frame_id
        api.write_frame(stdout, response, max_frame_bytes=limit)
        if code:
            return 65
        recent.append(request.frame_id)
        if kind == "shutdown":
            return 0
