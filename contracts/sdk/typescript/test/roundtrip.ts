import { readFileSync } from "node:fs";
import { fromBinary, toBinary } from "@bufbuild/protobuf";
import { EventEnvelopeSchema } from "../src/gen/clever/v1/events_pb";

const bytes = readFileSync(new URL("../../../fixtures/wire/event.bin", import.meta.url));
const event = fromBinary(EventEnvelopeSchema, bytes);
if (event.messageId !== "evt_cross_runtime" || event.correlationId !== "corr_cross_runtime") {
  throw new Error(`wire semantic mismatch: ${event.messageId}/${event.correlationId}`);
}
const encoded = toBinary(EventEnvelopeSchema, event);
const again = fromBinary(EventEnvelopeSchema, encoded);
if (again.eventType !== "contract.cross_runtime") {
  throw new Error(`round-trip eventType mismatch: ${again.eventType}`);
}
console.log(`OK: TypeScript decoded and round-tripped ${bytes.length} protobuf bytes`);
