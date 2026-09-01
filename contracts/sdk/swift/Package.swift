// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "CleverContracts",
    products: [.library(name: "CleverContracts", targets: ["CleverContracts"])],
    dependencies: [
        .package(url: "https://github.com/apple/swift-protobuf.git", exact: "1.38.1")
    ],
    targets: [
        .target(name: "CleverContracts", dependencies: [.product(name: "SwiftProtobuf", package: "swift-protobuf")]),
        .testTarget(name: "CleverContractsTests", dependencies: ["CleverContracts"])
    ]
)
