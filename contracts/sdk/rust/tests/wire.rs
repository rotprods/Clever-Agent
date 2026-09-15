use clever_contracts::{AdapterFrame, EventEnvelope, InferenceRequest};
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
fn decodes_and_round_trips_inference_request_fixture() {
    let bytes = include_bytes!("../../../fixtures/wire/inference-request.bin");
    let request = InferenceRequest::decode(&bytes[..]).expect("decode inference fixture");
    assert_eq!(request.request_id, "req_contract_001");
    assert_eq!(request.attempt_id, "att_contract_001");
    assert_eq!(request.principal.as_ref().map(|row| row.user_id.as_str()), Some("user_contract"));
    assert!(request.deadline_at.is_some());
    let encoded = request.encode_to_vec();
    let again = InferenceRequest::decode(encoded.as_slice()).expect("redecode inference request");
    assert_eq!(again.idempotency_key, "idem_contract_001");
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
