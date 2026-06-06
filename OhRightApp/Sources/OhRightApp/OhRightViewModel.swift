import Foundation
import SwiftUI
import Combine

@MainActor
class OhRightViewModel: ObservableObject {
    @Published var searchResults: [OhRightNode] = []
    @Published var searchMessage: String?
    @Published var obsessions: [OhRightNode] = []
    @Published var products: [OhRightNode] = []
    @Published var stats: DashboardStats?
    @Published var screenTime: ScreenTimeData?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var lastRefresh: Date?

    private let bridge = PythonBridge.shared

    func loadTab(_ tabIndex: Int) {
        guard !isLoading else { return }
        isLoading = true
        errorMessage = nil

        Task {
            defer { isLoading = false }

            switch tabIndex {
            case 0: break
            case 1: await loadObsessions()
            case 2: await loadProducts()
            case 3: await loadScreenTime()
            default: break
            }

            lastRefresh = Date()
        }
    }

    func loadObsessions() async {
        do {
            let nodes = try await bridge.getObsessions(limit: 15)
            self.obsessions = nodes
        } catch {
            self.errorMessage = "Failed to load: \(error.localizedDescription)"
        }
    }

    func loadProducts() async {
        do {
            let nodes = try await bridge.getProducts(limit: 20)
            self.products = nodes
        } catch {
            self.errorMessage = "Failed to load: \(error.localizedDescription)"
        }
    }

    func loadScreenTime() async {
        do {
            async let timeData = bridge.getScreenTime(period: "today")
            async let statsData = bridge.getStats()
            let (time, st) = try await (timeData, statsData)
            self.screenTime = time
            self.stats = st
        } catch {
            self.errorMessage = "Failed to load: \(error.localizedDescription)"
        }
    }

    func search(query: String) {
        guard !query.trimmingCharacters(in: .whitespaces).isEmpty else {
            searchResults = []
            searchMessage = nil
            return
        }

        isLoading = true
        errorMessage = nil

        Task {
            defer { isLoading = false }

            do {
                let result = try await bridge.smartSearch(query: query)
                self.searchMessage = result.message
                self.searchResults = result.results.asList
            } catch {
                // Fallback to regular search
                do {
                    let nodes = try await bridge.search(query: query, limit: 10)
                    self.searchResults = nodes
                    self.searchMessage = nil
                } catch {
                    self.errorMessage = "Search failed: \(error.localizedDescription)"
                }
            }
        }
    }

    func openTerminal() {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/open")
        task.arguments = ["-a", "Terminal", NSString("~/.ohright").expandingTildeInPath]
        try? task.run()
    }
}
