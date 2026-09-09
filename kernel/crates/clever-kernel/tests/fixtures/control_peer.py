"""Controlled adversarial peer for W02-05. It does not load an LLM."""
from __future__ import annotations
import sys
import time
import fake_adapter_sidecar as wire


def main() -> int:
    mode = sys.argv[1]
    hello = wire.hello()
    if mode == "peer-limit":
        hello.hello.max_frame_bytes = 512
    wire.write_frame(hello)
    ack = wire.read_frame()
    if ack is None or ack.WhichOneof("body") != "hello_ack" or not ack.hello_ack.accepted:
        return 64
    count = 0
    while True:
        request = wire.read_frame()
        if request is None:
            return 0
        count += 1
        kind = request.WhichOneof("body")
        stopping = kind == "shutdown"
        status = wire.runtime_pb2.RUNTIME_HEALTH_STATUS_STOPPING if stopping else wire.runtime_pb2.RUNTIME_HEALTH_STATUS_READY
        health = wire.health(status)
        if mode == "late" and count == 1:
            time.sleep(0.3)
        if mode == "unspecified":
            health.status = 0
        if mode == "false-green":
            health.dropped_event_count = 1
        if mode == "wrong-runtime":
            health.runtime_id = "other-principal-runtime"
        if mode == "peer-limit":
            health.status = wire.runtime_pb2.RUNTIME_HEALTH_STATUS_DEGRADED
            health.degradation_reasons.append("x" * 2048)
        correlation = request.frame_id
        if mode == "mismatch" or (mode == "mismatch-once" and count == 1):
            correlation = "unrelated-request"
        response = wire.frame(f"reply:{request.frame_id}", "health", health, correlation_id=correlation)
        if mode == "no-body":
            response.ClearField("health")
        wire.write_frame(response)
        if stopping:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
