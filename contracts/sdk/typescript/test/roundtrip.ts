import { readFileSync } from "node:fs";
import { fromBinary, toBinary } from "@bufbuild/protobuf";
import { AdapterFrameSchema } from "../src/gen/clever/v1/adapter_pb";
import { EventEnvelopeSchema } from "../src/gen/clever/v1/events_pb";

const eventBytes = readFileSync(new URL("../../../fixtures/wire/event.bin", import.meta.url));
const event = fromBinary(EventEnvelopeSchema, eventBytes);
if (event.messageId !== "evt_cross_runtime" || event.correlationId !== "corr_cross_runtime") {
  throw new Error(`wire semantic mismatch: ${event.messageId}/${event.correlationId}`);
}
const eventAgain = fromBinary(EventEnvelopeSchema, toBinary(EventEnvelopeSchema, event));
if (eventAgain.eventType !== "contract.cross_runtime") {
  throw new Error(`round-trip eventType mismatch: ${eventAgain.eventType}`);
}

const adapterBytes = readFileSync(new URL("../../../fixtures/wire/adapter-hello.bin", import.meta.url));
const adapter = fromBinary(AdapterFrameSchema, adapterBytes);
if (adapter.frameId !== "frame_hello_openjarvis" || adapter.correlationId !== "corr_openjarvis_boot") {
  throw new Error(`adapter wire mismatch: ${adapter.frameId}/${adapter.correlationId}`);
}
const adapterAgain = fromBinary(AdapterFrameSchema, toBinary(AdapterFrameSchema, adapter));
if (adapterAgain.frameId !== adapter.frameId) {
  throw new Error(`adapter round-trip mismatch: ${adapterAgain.frameId}`);
}
console.log(`OK: TypeScript round-tripped event=${eventBytes.length} adapter=${adapterBytes.length} protobuf bytes`);
