"""Hostile control peer. Unknown wire fields must still count toward frame limits."""
import struct
import sys
import time
import fake_adapter_sidecar as base
from clever.v1 import runtime_pb2

def main() -> int:
    mode = sys.argv[1]
    hello = base.hello()
    if mode in ("negotiated-limit", "wire-padding"): hello.hello.max_frame_bytes = 512
    base.write_frame(hello)
    if base.read_frame() is None: return 64
    sequence = 0
    while True:
        request = base.read_frame()
        if request is None: return 0
        sequence += 1
        kind = request.WhichOneof("body")
        health = base.health(runtime_pb2.RUNTIME_HEALTH_STATUS_READY)
        if kind == "shutdown": health.status = runtime_pb2.RUNTIME_HEALTH_STATUS_STOPPING
        correlation = request.frame_id
        if mode == "wrong-correlation": correlation = "another-request"
        if mode == "unspecified": health.status = runtime_pb2.RUNTIME_HEALTH_STATUS_UNSPECIFIED
        if mode == "false-ready": health.dropped_event_count = 1
        if mode == "ready-with-reason": health.degradation_reasons.append("engine offline")
        if mode == "negotiated-limit":
            health.status = runtime_pb2.RUNTIME_HEALTH_STATUS_DEGRADED
            health.degradation_reasons.append("x" * 2048)
        if mode == "late-health" and sequence == 1: time.sleep(0.25)
        response = base.frame(f"response-{sequence}", "health", health, correlation_id=correlation)
        if mode == "empty-frame-id": response.frame_id = ""
        if mode == "wire-padding":
            # Unknown length-delimited field 99, length 2048. Prost discards it.
            payload = response.SerializeToString() + b'\x9a\x06\x80\x10' + b'x' * 2048
            sys.stdout.buffer.write(struct.pack('>I', len(payload)) + payload)
            sys.stdout.buffer.flush()
        else:
            base.write_frame(response)
        if kind == "shutdown": return 0

if __name__ == "__main__": raise SystemExit(main())
