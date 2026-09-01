use clever_contracts::{AdapterFrame, EventEnvelope};
use prost::Message;

#[test]
fn decodes_and_round_trips_shared_event_fixture() {
    let bytes = include_bytes!("../../../fixtures/wire/event.bin");
    let event = EventEnvelope::decode(&bytes[..]).expect("decode shared event fixture");
    assert_eq!(event.message_id, "evt_cross_runtime");
    assert_eq!(event.correlation_id, "corr_cross_runtime");
    assert_eq!(event.event_type, "contract.cross_runtime");
    let encoded = event.encode_to_vec();
    let again = EventEnvelope::decode(encoded.as_slice()).expect("redecode encoded event");
    assert_eq!(again.message_id, event.message_id);
}

#[test]
fn decodes_and_round_trips_adapter_hello_fixture() {
    let bytes = include_bytes!("../../../fixtures/wire/adapter-hello.bin");
    let frame = AdapterFrame::decode(&bytes[..]).expect("decode shared adapter fixture");
    assert_eq!(frame.frame_id, "frame_hello_openjarvis");
    assert_eq!(frame.correlation_id, "corr_openjarvis_boot");
    let encoded = frame.encode_to_vec();
    let again = AdapterFrame::decode(encoded.as_slice()).expect("redecode adapter frame");
    assert_eq!(again.frame_id, frame.frame_id);
}
