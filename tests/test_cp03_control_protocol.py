from __future__ import annotations
from io import BytesIO
import unittest
from unittest.mock import patch
from adapters.openjarvis import sidecar as s

class Fragmented(BytesIO):
    def read(self, size=-1):
        return super().read(min(size, 1) if size >= 0 else 1)

def encode(frame):
    stream = BytesIO(); s.write_frame(stream, frame); return stream.getvalue()

def ack(**changes):
    body = s.adapter_pb2.AdapterHelloAck(contract_version=s.contract_version(), adapter_id=s.ADAPTER_ID, accepted=True, max_frame_bytes=s.MAX_FRAME_BYTES, negotiated_features=s.hello_frame().hello.supported_features)
    for key, value in changes.items():
        setattr(body, key, value)
    result = s._frame("kernel-ack", "hello_ack", body); result.correlation_id = "openjarvis-hello"
    return result

def request(name="q1", body="health_request"):
    cls = {"health_request": s.adapter_pb2.AdapterHealthRequest, "registry_snapshot_request": s.adapter_pb2.RegistrySnapshotRequest, "cancel": s.adapter_pb2.AdapterCancel, "shutdown": s.adapter_pb2.AdapterShutdown}[body]
    return s._frame(name, body, cls())

class ControlProtocolTests(unittest.TestCase):
    def run_control(self, frames):
        output = BytesIO()
        with patch.object(s, "discover_registry_snapshot", return_value=(s.adapter_pb2.RegistrySnapshot(runtime_id=s.RUNTIME_ID), {"unsupported_registries": []})):
            code = s.run_protocol(BytesIO(b"".join(encode(f) for f in frames)), output)
        output.seek(0); replies = []
        while (frame := s.read_frame(output)) is not None:
            replies.append(frame)
        return code, replies

    def test_fragmented_prefix_and_payload(self):
        expected = request()
        self.assertEqual(s.read_frame(Fragmented(encode(expected))), expected)
    def test_empty_body_is_rejected(self):
        f = s.adapter_pb2.AdapterFrame(contract_version=s.contract_version(), frame_id="q1")
        with self.assertRaises(ValueError): s.read_frame(BytesIO(encode(f)))
    def test_empty_frame_id_is_rejected(self):
        f = request(); f.frame_id = ""
        with self.assertRaises(ValueError): s.read_frame(BytesIO(encode(f)))
    def test_truncated_prefix_is_rejected(self):
        with self.assertRaises(EOFError): s.read_frame(BytesIO(b"\x00\x00"))
    def test_initial_hello_has_no_correlation(self):
        self.assertEqual(s.hello_frame().correlation_id, "")
    def test_ack_identity_mismatch(self):
        self.assertEqual(self.run_control([ack(adapter_id="unrelated")])[0], 64)
    def test_ack_correlation_mismatch(self):
        f = ack(); f.correlation_id = "other"
        self.assertEqual(self.run_control([f])[0], 64)
    def test_ack_version_mismatch(self):
        f = ack(); f.hello_ack.contract_version.major = 9
        self.assertEqual(self.run_control([f])[0], 64)
    def test_ack_frame_limit_invalid(self):
        for value in (0, s.MAX_FRAME_BYTES + 1):
            self.assertEqual(self.run_control([ack(max_frame_bytes=value)])[0], 64)
    def test_ack_missing_feature(self):
        f = ack(); del f.hello_ack.negotiated_features[:]
        self.assertEqual(self.run_control([f])[0], 64)
    def test_all_control_responses_are_correlated(self):
        frames = [request(f"q{i}", kind) for i, kind in enumerate(["registry_snapshot_request", "health_request", "cancel", "shutdown"])]
        code, responses = self.run_control([ack(), *frames])
        self.assertEqual(code, 0)
        self.assertEqual([f.correlation_id for f in responses[1:]], [f.frame_id for f in frames])
        self.assertEqual(len({f.frame_id for f in responses}), 5)
    def test_replay_is_error_and_closes(self):
        code, responses = self.run_control([ack(), request(), request()])
        self.assertEqual(code, 65); self.assertEqual(responses[-1].error.code, "INVALID_CONTROL_REQUEST")
    def test_expired_request_is_error(self):
        f = request(); f.deadline_at.seconds = 1
        code, responses = self.run_control([ack(), f])
        self.assertEqual(code, 65); self.assertEqual(responses[-1].error.code, "DEADLINE_EXCEEDED")
    def test_negotiated_inbound_limit(self):
        f = request(body="cancel"); f.cancel.reason = "x" * 1500
        with self.assertRaises(ValueError): self.run_control([ack(max_frame_bytes=1024), f])

if __name__ == "__main__": unittest.main()
