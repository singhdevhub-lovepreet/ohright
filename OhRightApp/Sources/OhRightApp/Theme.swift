import SwiftUI

// MARK: - Color Extension

extension Color {
    init(hex: UInt, alpha: Double = 1) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xff) / 255,
            green: Double((hex >> 8) & 0xff) / 255,
            blue: Double(hex & 0xff) / 255,
            opacity: alpha
        )
    }
}

// MARK: - Design Tokens

enum Oh {
    // Surfaces — warm dark, not pure black
    static let bg = Color(hex: 0x111111)
    static let surface = Color(hex: 0x1A1A1A)
    static let surfaceRaised = Color(hex: 0x222222)
    static let border = Color(hex: 0x2D2D2D)

    // Text
    static let text = Color(hex: 0xECECEC)
    static let textSoft = Color(hex: 0x999999)
    static let textFaint = Color(hex: 0x555555)

    // Accent
    static let orange = Color(hex: 0xE8713A)
    static let orangeSoft = Color(hex: 0xE8713A, alpha: 0.12)

    // Status
    static let green = Color(hex: 0x5CB85C)
    static let amber = Color(hex: 0xE0A63A)
    static let red = Color(hex: 0xD9534F)

    // Categories
    static func categoryColor(_ cat: String) -> Color {
        switch cat.lowercased() {
        case "shopping": return Color(hex: 0xE8713A)
        case "coding": return Color(hex: 0x5B9BD5)
        case "learning": return Color(hex: 0x9B59B6)
        case "browsing": return Color(hex: 0x3498DB)
        case "media": return Color(hex: 0xE74C8B)
        case "messaging": return Color(hex: 0x2ECC71)
        case "productivity": return Color(hex: 0x1ABC9C)
        case "travel": return Color(hex: 0xF39C12)
        case "career": return Color(hex: 0x8E44AD)
        case "projects": return Color(hex: 0x2980B9)
        case "finance": return Color(hex: 0x27AE60)
        case "health": return Color(hex: 0xE74C3C)
        case "entertainment": return Color(hex: 0xE91E63)
        case "system": return Color(hex: 0x7F8C8D)
        case "habits": return Color(hex: 0x00BCD4)
        case "interests": return Color(hex: 0xFF9800)
        default: return Color(hex: 0x95A5A6)
        }
    }

    static func categoryIcon(_ cat: String) -> String {
        switch cat.lowercased() {
        case "shopping": return "cart"
        case "coding": return "laptopcomputer"
        case "learning": return "book"
        case "browsing": return "globe"
        case "media": return "play.circle.fill"
        case "messaging": return "bubble.left.fill"
        case "productivity": return "checklist"
        case "travel": return "airplane"
        case "career": return "briefcase"
        case "projects": return "hammer"
        case "finance": return "dollarsign.circle"
        case "health": return "heart.fill"
        case "entertainment": return "gamecontroller"
        case "system": return "gearshape"
        case "habits": return "repeat"
        case "interests": return "star"
        default: return "circle.fill"
        }
    }
}
