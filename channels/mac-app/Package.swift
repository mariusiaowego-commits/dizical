// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "DizicalMac",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "DizicalMac", targets: ["DizicalMac"])
    ],
    targets: [
        .executableTarget(
            name: "DizicalMac",
            path: "Sources/DizicalMac",
            resources: [
                .process("Resources")
            ]
        )
    ]
)
