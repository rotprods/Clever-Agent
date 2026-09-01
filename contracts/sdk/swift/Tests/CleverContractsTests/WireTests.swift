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

@Test func decodesAndRoundTripsAdapterHelloFixture() throws {
    let packageRoot = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    let fixture = packageRoot.appendingPathComponent("../../fixtures/wire/adapter-hello.bin").standardizedFileURL
    let data = try Data(contentsOf: fixture)
    let frame = try Clever_V1_AdapterFrame(serializedBytes: data)
    #expect(frame.frameID == "frame_hello_openjarvis")
    #expect(frame.correlationID == "corr_openjarvis_boot")
    let encoded = try frame.serializedData()
    let again = try Clever_V1_AdapterFrame(serializedBytes: encoded)
    #expect(again.frameID == frame.frameID)
}
