import Foundation

// MARK: - Data Models

struct OhRightNode: Codable, Identifiable, Hashable {
    var id: String
    let title: String
    let subtitle: String
    let type: String
    let status: String?
    let timeSpent: String?
    let revisits: Int?
    let lastSeen: String?
    let url: String?

    enum CodingKeys: String, CodingKey {
        case title, subtitle, type, status, revisits, url
        case timeSpent = "time_spent"
        case lastSeen = "last_seen"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        title = try c.decode(String.self, forKey: .title)
        subtitle = try c.decodeIfPresent(String.self, forKey: .subtitle) ?? ""
        type = try c.decodeIfPresent(String.self, forKey: .type) ?? ""
        status = try c.decodeIfPresent(String.self, forKey: .status)
        timeSpent = try c.decodeIfPresent(String.self, forKey: .timeSpent)
        revisits = try c.decodeIfPresent(Int.self, forKey: .revisits)
        lastSeen = try c.decodeIfPresent(String.self, forKey: .lastSeen)
        url = try c.decodeIfPresent(String.self, forKey: .url)
        id = title
    }
}

struct ScreenTimeData: Codable {
    let period: String
    let totalHours: Double
    let categories: [ScreenTimeCategory]

    enum CodingKeys: String, CodingKey {
        case period
        case totalHours = "total_hours"
        case categories
    }
}

struct ScreenTimeCategory: Codable, Identifiable {
    let category: String
    let minutes: Double
    let hours: Double
    let display: String
    let percentage: Double
    let events: Int

    var id: String { category }
}

struct DashboardStats: Codable {
    let topicsTracked: Int
    let active: Int
    let sleeping: Int
    let dropped: Int
    let captures: Int
    let insights: Int
    let categories: [String: Int]

    enum CodingKeys: String, CodingKey {
        case active, sleeping, dropped, captures, insights, categories
        case topicsTracked = "topics_tracked"
    }
}

struct SmartSearchResult: Codable {
    let message: String
    let results: SmartResults

    enum SmartResults: Codable {
        case list([OhRightNode])
        case dict([String: AnyCodable])

        init(from decoder: Decoder) throws {
            let container = try decoder.singleValueContainer()
            if let arr = try? container.decode([OhRightNode].self) {
                self = .list(arr)
            } else {
                self = .dict([:])
            }
        }

        func encode(to encoder: Encoder) throws {
            var container = encoder.singleValueContainer()
            switch self {
            case .list(let arr): try container.encode(arr)
            case .dict(_): try container.encode([String: String]())
            }
        }

        var asList: [OhRightNode] {
            switch self {
            case .list(let arr): return arr
            case .dict: return []
            }
        }
    }
}

// Minimal AnyCodable for dict case
struct AnyCodable: Codable {
    init(from decoder: Decoder) throws {}
    func encode(to encoder: Encoder) throws {}
}

struct ContextSnapshot: Codable {
    let activeTopics: [ActiveTopic]
    let recentlyDropped: [DroppedTopic]
    let timestamp: String

    enum CodingKeys: String, CodingKey {
        case activeTopics = "active_topics"
        case recentlyDropped = "recently_dropped"
        case timestamp
    }
}

struct ActiveTopic: Codable, Identifiable {
    let label: String
    let type: String
    var id: String { label }
}

struct DroppedTopic: Codable, Identifiable {
    let label: String
    let lastSeen: String
    var id: String { label }

    enum CodingKeys: String, CodingKey {
        case label
        case lastSeen = "last_seen"
    }
}

// MARK: - Tab Enum

enum OhRightTab: Int, CaseIterable {
    case search = 0
    case obsessions = 1
    case products = 2
    case dashboard = 3

    var title: String {
        switch self {
        case .search: return "Search"
        case .obsessions: return "Focus"
        case .products: return "Research"
        case .dashboard: return "Time"
        }
    }

    var icon: String {
        switch self {
        case .search: return "magnifyingglass"
        case .obsessions: return "flame"
        case .products: return "cart"
        case .dashboard: return "clock"
        }
    }
}
