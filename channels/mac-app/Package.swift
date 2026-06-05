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
                // 只 process app icon (用于 Dock / Launchpad)
                // menubar icon 不放 bundle (运行时直接读), 避免 iconset 重名冲突
                .process("Resources/dizical.iconset")
            ]
        )
    ]
)
