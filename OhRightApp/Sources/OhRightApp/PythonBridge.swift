import Foundation

// MARK: - Python Bridge

actor PythonBridge {
    static let shared = PythonBridge()

    private let ohrightPath = NSString("~/.ohright").expandingTildeInPath
    private let pythonPath: String = {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        p.arguments = ["python3"]
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = Pipe()
        do {
            try p.run()
            p.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let path = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
               !path.isEmpty {
                return path
            }
        } catch {}
        return "/usr/bin/python3"
    }()

    private init() {}

    // MARK: - Generic Query

    func runQuery(_ command: String, args: [String] = []) async throws -> Data {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = [ohrightPath + "/query.py", command] + args
        process.currentDirectoryURL = URL(fileURLWithPath: ohrightPath)

        let pipe = Pipe()
        let errPipe = Pipe()
        process.standardOutput = pipe
        process.standardError = errPipe

        try process.run()
        process.waitUntilExit()

        let data = pipe.fileHandleForReading.readDataToEndOfFile()

        guard process.terminationStatus == 0 else {
            let errorOutput = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw PythonBridgeError.commandFailed(errorOutput)
        }

        return data
    }

    // MARK: - Commands

    func getObsessions(limit: Int = 10) async throws -> [OhRightNode] {
        let data = try await runQuery("obsessions")
        return try JSONDecoder().decode([OhRightNode].self, from: data)
    }

    func getProducts(limit: Int = 15) async throws -> [OhRightNode] {
        let data = try await runQuery("products")
        return try JSONDecoder().decode([OhRightNode].self, from: data)
    }

    func getAbandoned(limit: Int = 15) async throws -> [OhRightNode] {
        let data = try await runQuery("abandoned")
        return try JSONDecoder().decode([OhRightNode].self, from: data)
    }

    func getStats() async throws -> DashboardStats {
        let data = try await runQuery("stats")
        return try JSONDecoder().decode(DashboardStats.self, from: data)
    }

    func getScreenTime(period: String = "today") async throws -> ScreenTimeData {
        let data = try await runQuery("screen_time", args: [period])
        return try JSONDecoder().decode(ScreenTimeData.self, from: data)
    }

    func search(query: String, limit: Int = 10) async throws -> [OhRightNode] {
        let data = try await runQuery("search", args: [query])
        return try JSONDecoder().decode([OhRightNode].self, from: data)
    }

    func smartSearch(query: String) async throws -> SmartSearchResult {
        let data = try await runQuery("smart_search", args: [query])
        return try JSONDecoder().decode(SmartSearchResult.self, from: data)
    }

    func getRecent(hours: Int = 1) async throws -> [OhRightNode] {
        let data = try await runQuery("recent", args: ["\(hours)"])
        return try JSONDecoder().decode([OhRightNode].self, from: data)
    }

    func getContext() async throws -> ContextSnapshot {
        let data = try await runQuery("context")
        return try JSONDecoder().decode(ContextSnapshot.self, from: data)
    }

    func runOrchestratorCycle() async throws -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = [ohrightPath + "/orchestrator.py"]
        process.currentDirectoryURL = URL(fileURLWithPath: ohrightPath)

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = Pipe()

        try process.run()
        process.waitUntilExit()

        let output = pipe.fileHandleForReading.readDataToEndOfFile()
        return String(data: output, encoding: .utf8) ?? ""
    }
}

// MARK: - Errors

enum PythonBridgeError: LocalizedError {
    case commandFailed(String)
    case decodingError(String)
    case notFound

    var errorDescription: String? {
        switch self {
        case .commandFailed(let msg): return "Command failed: \(msg)"
        case .decodingError(let msg): return "Failed to parse response: \(msg)"
        case .notFound: return "OhRight not found at expected path"
        }
    }
}
