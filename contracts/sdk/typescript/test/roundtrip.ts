import { readFileSync } from "node:fs";
import { fromBinary, toBinary } from "@bufbuild/protobuf";
import { AdapterFrameSchema } from "../src/gen/clever/v1/adapter_pb";
import { EventEnvelopeSchema } from "../src/gen/clever/v1/events_pb";
import { InferenceRequestSchema } from "../src/gen/clever/v1/inference_pb";

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

const inferenceBytes = readFileSync(new URL("../../../fixtures/wire/inference-request.bin", import.meta.url));
const inference = fromBinary(InferenceRequestSchema, inferenceBytes);
if (inference.requestId !== "req_contract_001" || inference.attemptId !== "att_contract_001") {
  throw new Error(`inference identity mismatch: ${inference.requestId}/${inference.attemptId}`);
}
const inferenceAgain = fromBinary(InferenceRequestSchema, toBinary(InferenceRequestSchema, inference));
if (inferenceAgain.deadlineAt === undefined || inferenceAgain.principal?.userId !== "user_contract") {
  throw new Error("inference deadline/principal lost during round-trip");
}
console.log(`OK: TypeScript round-tripped event=${eventBytes.length} adapter=${adapterBytes.length} inference=${inferenceBytes.length} protobuf bytes`);
