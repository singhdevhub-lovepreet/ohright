import SwiftUI

// MARK: - Error View

struct ErrorView: View {
    let message: String

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 14))
                .foregroundColor(Oh.amber)
            Text(message)
                .font(.system(size: 11))
                .foregroundColor(Oh.textSoft)
                .lineLimit(3)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Oh.amber.opacity(0.06))
        .cornerRadius(8)
    }
}

// MARK: - Empty State

struct EmptyStateView: View {
    let icon: String
    let title: String
    let subtitle: String

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 24))
                .foregroundColor(Oh.textFaint)
            Text(title)
                .font(.system(size: 13, weight: .medium))
                .foregroundColor(Oh.textSoft)
            Text(subtitle)
                .font(.system(size: 11))
                .foregroundColor(Oh.textFaint)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 240)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 40)
    }
}

// MARK: - Loading

struct LoadingView: View {
    var body: some View {
        HStack {
            Spacer()
            ProgressView()
                .scaleEffect(0.6)
                .tint(Oh.orange)
            Spacer()
        }
        .frame(height: 60)
    }
}

// MARK: - Node Detail Popover

struct NodeDetailView: View {
    let node: OhRightNode

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack(spacing: 8) {
                Image(systemName: Oh.categoryIcon(node.type))
                    .font(.system(size: 14))
                    .foregroundColor(Oh.categoryColor(node.type))
                VStack(alignment: .leading, spacing: 1) {
                    Text(node.title)
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundColor(Oh.text)
                        .lineLimit(2)
                    Text(node.type)
                        .font(.system(size: 10))
                        .foregroundColor(Oh.textFaint)
                }
            }

            if !node.subtitle.isEmpty {
                Text(node.subtitle)
                    .font(.system(size: 11))
                    .foregroundColor(Oh.textSoft)
                    .lineLimit(4)
            }

            Rectangle().fill(Oh.border).frame(height: 0.5)

            // Info rows
            VStack(alignment: .leading, spacing: 6) {
                if let time = node.timeSpent, !time.isEmpty {
                    infoRow("clock", "Time spent", time)
                }
                if let revisits = node.revisits {
                    infoRow("eye", "Views", "\(revisits)")
                }
                if let status = node.status {
                    infoRow("circle.fill", "Status", status.capitalized)
                }
                if let lastSeen = node.lastSeen, !lastSeen.isEmpty {
                    infoRow("calendar", "Last seen", formatDate(lastSeen))
                }
            }

            if let url = node.url, !url.isEmpty, let nsURL = URL(string: url) {
                Rectangle().fill(Oh.border).frame(height: 0.5)
                Button(action: { NSWorkspace.shared.open(nsURL) }) {
                    HStack(spacing: 4) {
                        Image(systemName: "arrow.up.right")
                            .font(.system(size: 8, weight: .bold))
                        Text(url)
                            .font(.system(size: 10))
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                    .foregroundColor(Oh.orange)
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func infoRow(_ icon: String, _ label: String, _ value: String) -> some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
                .font(.system(size: 8))
                .foregroundColor(Oh.textFaint)
                .frame(width: 12)
            Text(label)
                .font(.system(size: 10))
                .foregroundColor(Oh.textFaint)
                .frame(width: 65, alignment: .leading)
            Text(value)
                .font(.system(size: 10, weight: .medium))
                .foregroundColor(Oh.text)
        }
    }

    private func formatDate(_ s: String) -> String {
        let f = ISO8601DateFormatter()
        if let d = f.date(from: s) {
            let r = RelativeDateTimeFormatter()
            r.unitsStyle = .abbreviated
            return r.localizedString(for: d, relativeTo: Date())
        }
        return s
    }
}
