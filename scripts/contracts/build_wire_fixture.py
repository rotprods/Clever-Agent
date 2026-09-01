from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "contracts/sdk/python/gen"
if str(GENERATED) not in sys.path:
    sys.path.insert(0, str(GENERATED))

from google.protobuf.json_format import MessageToDict
from clever.v1 import common_pb2, events_pb2, identity_pb2


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
    wire_dir = ROOT / "contracts/fixtures/wire"
    wire_dir.mkdir(parents=True, exist_ok=True)
    binary = event.SerializeToString(deterministic=True)
    (wire_dir / "event.bin").write_bytes(binary)
    decoded = events_pb2.EventEnvelope.FromString(binary)
    assert decoded.message_id == event.message_id
    canonical = MessageToDict(decoded, preserving_proto_field_name=False, use_integers_for_enums=False)
    (wire_dir / "event.protobuf.json").write_text(json.dumps(canonical, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK: Python produced deterministic {len(binary)}-byte shared wire fixture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
