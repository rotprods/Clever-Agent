"""Lifecycle adversary for W02-04. Never loads an LLM or accesses the network."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time


def handshake() -> None:
    wire.write_frame(wire.hello())
    ack = wire.read_frame()
    if ack is None or ack.WhichOneof("body") != "hello_ack" or not ack.hello_ack.accepted:
        raise SystemExit(64)


def grandchild(pid_file: str) -> int:
    Path(pid_file).write_text(str(os.getpid()), encoding="utf-8")
    time.sleep(60)
    return 0


def cleanup_marker(path: str) -> int:
    Path(path).write_text("cleanup-ran\n", encoding="utf-8")
    return 0


def cleanup_hang(path: str) -> int:
    Path(path).write_text("cleanup-started\n", encoding="utf-8")
    time.sleep(60)
    return 0


def serve(mode: str) -> int:
    global wire
    import fake_adapter_sidecar as wire
    handshake()
    if mode == "spawn-grandchild":
        pid_file = os.environ["CLEVER_LIFECYCLE_PID_FILE"]
        subprocess.Popen(
            [sys.executable, __file__, "grandchild", pid_file],
            stdin=subprocess.DEVNULL,
            stdout=sys.stdout,
            stderr=sys.stderr,
            close_fds=True,
        )
    while True:
        request = wire.read_frame()
        if request is None:
            return 0
        body = request.WhichOneof("body")
        if body == "shutdown":
            response = wire.frame(
                f"shutdown:{request.frame_id}",
                "health",
                wire.health(wire.runtime_pb2.RUNTIME_HEALTH_STATUS_STOPPING),
                correlation_id=request.frame_id,
            )
            wire.write_frame(response)
            if mode == "stopping-hang":
                time.sleep(60)
            return 0
        if body == "health_request" or body == "cancel":
            wire.write_frame(
                wire.frame(
                    f"health:{request.frame_id}",
                    "health",
                    wire.health(wire.runtime_pb2.RUNTIME_HEALTH_STATUS_READY),
                    correlation_id=request.frame_id,
                )
            )
        else:
            error = wire.adapter_pb2.AdapterError(code="UNSUPPORTED", message=str(body), retryable=False)
            wire.write_frame(wire.frame(f"error:{request.frame_id}", "error", error, correlation_id=request.frame_id))


def main() -> int:
    mode = sys.argv[1]
    if mode == "grandchild":
        return grandchild(sys.argv[2])
    if mode == "cleanup-marker":
        return cleanup_marker(sys.argv[2])
    if mode == "cleanup-hang":
        return cleanup_hang(sys.argv[2])
    return serve(mode)


if __name__ == "__main__":
    raise SystemExit(main())
