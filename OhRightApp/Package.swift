// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "OhRightApp",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "OhRightApp", targets: ["OhRightApp"])
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "OhRightApp",
            path: "Sources/OhRightApp"
        )
    ]
)