import Foundation
import Testing
@testable import CleverContracts

@Test func decodesAndRoundTripsSharedEventFixture() throws {
    let packageRoot = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    let fixture = packageRoot.appendingPathComponent("../../fixtures/wire/event.bin").standardizedFileURL
    let data = try Data(contentsOf: fixture)
    let event = try Clever_V1_EventEnvelope(serializedBytes: data)
    #expect(event.messageID == "evt_cross_runtime")
    #expect(event.correlationID == "corr_cross_runtime")
    #expect(event.eventType == "contract.cross_runtime")
    let encoded = try event.serializedData()
    let again = try Clever_V1_EventEnvelope(serializedBytes: encoded)
    #expect(again.messageID == event.messageID)
}
