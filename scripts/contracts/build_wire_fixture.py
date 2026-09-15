from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "contracts/sdk/python/gen"
if str(GENERATED) not in sys.path:
    sys.path.insert(0, str(GENERATED))

from google.protobuf.json_format import MessageToDict
from google.protobuf.timestamp_pb2 import Timestamp
from clever.v1 import adapter_pb2, common_pb2, events_pb2, identity_pb2, inference_pb2, runtime_pb2


def timestamp(value: datetime) -> Timestamp:
    result = Timestamp()
    result.FromDatetime(value)
    return result


def write_message(message, stem: str) -> int:
    wire_dir = ROOT / "contracts/fixtures/wire"
    wire_dir.mkdir(parents=True, exist_ok=True)
    binary = message.SerializeToString(deterministic=True)
    (wire_dir / f"{stem}.bin").write_bytes(binary)
    decoded = type(message).FromString(binary)
    canonical = MessageToDict(decoded, preserving_proto_field_name=False, use_integers_for_enums=False)
    (wire_dir / f"{stem}.protobuf.json").write_text(json.dumps(canonical, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return len(binary)


def main() -> int:
    event = events_pb2.EventEnvelope(
        contract_version=common_pb2.ContractVersion(major=1, minor=0),
        message_id="evt_cross_runtime",
        correlation_id="corr_cross_runtime",
        causation_id="root_cross_runtime",
        producer=common_pb2.RuntimeOwner(runtime_id="contract-fixture", adapter_id="cp02"),
        principal=identity_pb2.PrincipalRef(user_id="user_demo", device_id="device_demo"),
        session_id="ses_demo",
        goal_id="goal_demo",
        classification=common_pb2.DATA_CLASSIFICATION_INTERNAL,
        event_type="contract.cross_runtime",
        payload=common_pb2.Payload(schema_uri="clever://fixtures/cross-runtime/v1", content_type="application/json", data=b"{}"),
    )
    event_bytes = write_message(event, "event")

    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    adapter = adapter_pb2.AdapterFrame(
        contract_version=common_pb2.ContractVersion(major=1, minor=1),
        frame_id="frame_hello_openjarvis",
        correlation_id="corr_openjarvis_boot",
        sent_at=timestamp(now),
        deadline_at=timestamp(now + timedelta(seconds=5)),
        hello=adapter_pb2.AdapterHello(
            contract_version=common_pb2.ContractVersion(major=1, minor=1),
            adapter_id="openjarvis",
            runtime=runtime_pb2.RuntimeDescriptor(
                contract_version=common_pb2.ContractVersion(major=1, minor=1),
                runtime_id="openjarvis-sidecar",
                runtime_kind="cognitive-runtime",
                implementation_version="pinned-72033b8",
            ),
            upstream_repository="open-jarvis/OpenJarvis",
            upstream_commit="72033b8ec288aa067ce4530ff9d96bf231e9c4e5",
            max_frame_bytes=4 * 1024 * 1024,
            supported_features=["registry.snapshot", "health", "cancel", "shutdown"],
        ),
    )
    adapter_bytes = write_message(adapter, "adapter-hello")
    decoded = adapter_pb2.AdapterFrame.FromString(adapter.SerializeToString())
    assert decoded.frame_id == "frame_hello_openjarvis"
    assert decoded.hello.upstream_commit == "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"
    assert decoded.hello.runtime.runtime_kind == "cognitive-runtime"

    inference = inference_pb2.InferenceRequest(
        contract_version=common_pb2.ContractVersion(major=1, minor=2),
        request_id="req_contract_001",
        attempt_id="att_contract_001",
        principal=identity_pb2.PrincipalRef(user_id="user_contract", device_id="device_contract"),
        session_id="ses_contract_001",
        engine_id="openjarvis.engine.default",
        model_id="fixture-model",
        inputs=[
            inference_pb2.InferenceInput(role=inference_pb2.INFERENCE_ROLE_SYSTEM, content="Answer with one bounded sentence."),
            inference_pb2.InferenceInput(role=inference_pb2.INFERENCE_ROLE_USER, content="What is the current contract version?"),
        ],
        config=inference_pb2.InferenceConfig(
            max_output_tokens=128,
            temperature=0.2,
            top_p=0.95,
            stop_sequences=["<END>"],
            stream=True,
        ),
        deadline_at=timestamp(datetime(2026, 9, 15, 18, 0, 5, tzinfo=timezone.utc)),
        idempotency_key="idem_contract_001",
    )
    inference_bytes = write_message(inference, "inference-request")
    inference_decoded = inference_pb2.InferenceRequest.FromString(inference.SerializeToString())
    assert inference_decoded.request_id == "req_contract_001"
    assert inference_decoded.attempt_id == "att_contract_001"
    assert inference_decoded.deadline_at.ToDatetime(tzinfo=timezone.utc) > now
    print(f"OK: Python produced event={event_bytes} adapter_hello={adapter_bytes} inference={inference_bytes} protobuf bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
