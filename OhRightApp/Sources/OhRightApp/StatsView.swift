import SwiftUI

struct StatsView: View {
    @ObservedObject var viewModel: OhRightViewModel

    var body: some View {
        if viewModel.isLoading {
            LoadingView()
        } else if let error = viewModel.errorMessage {
            ErrorView(message: error)
        } else if let time = viewModel.screenTime {
            screenTimeView(time)
        } else {
            EmptyStateView(
                icon: "clock",
                title: "No activity yet",
                subtitle: "Start using your computer and OhRight will track where your time goes."
            )
        }
    }

    // MARK: - Screen Time

    @ViewBuilder
    private func screenTimeView(_ data: ScreenTimeData) -> some View {
        // Total time header
        VStack(spacing: 2) {
            Text("\(data.totalHours, specifier: "%.1f")h")
                .font(.system(size: 28, weight: .bold, design: .rounded))
                .foregroundColor(Oh.text)
            Text("tracked today")
                .font(.system(size: 10))
                .foregroundColor(Oh.textFaint)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)

        // Category breakdown
        if !data.categories.isEmpty {
            VStack(spacing: 0) {
                ForEach(Array(data.categories.prefix(8).enumerated()), id: \.element.id) { index, cat in
                    categoryRow(cat, maxMinutes: data.categories.first?.minutes ?? 1)

                    if index < min(7, data.categories.count - 1) {
                        Rectangle()
                            .fill(Oh.border.opacity(0.4))
                            .frame(height: 0.5)
                            .padding(.leading, 38)
                    }
                }
            }
            .background(Oh.surface)
            .cornerRadius(10)
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Oh.border, lineWidth: 0.5)
            )
        }

        // Summary stats
        if let stats = viewModel.stats {
            summaryRow(stats)
        }
    }

    private func categoryRow(_ cat: ScreenTimeCategory, maxMinutes: Double) -> some View {
        HStack(spacing: 10) {
            Image(systemName: Oh.categoryIcon(cat.category))
                .font(.system(size: 11))
                .foregroundColor(Oh.categoryColor(cat.category))
                .frame(width: 22)

            Text(cat.category)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(Oh.text)

            Spacer()

            // Time bar
            let fraction = maxMinutes > 0 ? CGFloat(cat.minutes / maxMinutes) : 0
            RoundedRectangle(cornerRadius: 2)
                .fill(Oh.categoryColor(cat.category).opacity(0.3))
                .frame(width: 50 * fraction, height: 4)
                .frame(width: 50, alignment: .trailing)

            Text(cat.display)
                .font(.system(size: 10, weight: .medium, design: .monospaced))
                .foregroundColor(Oh.textSoft)
                .frame(width: 36, alignment: .trailing)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 9)
    }

    private func summaryRow(_ stats: DashboardStats) -> some View {
        HStack(spacing: 0) {
            summaryItem("\(stats.topicsTracked)", "topics")
            summaryDivider
            summaryItem("\(stats.active)", "active")
            summaryDivider
            summaryItem("\(stats.captures)", "captures")
            summaryDivider
            summaryItem("\(stats.insights)", "insights")
        }
        .background(Oh.surface)
        .cornerRadius(10)
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(Oh.border, lineWidth: 0.5)
        )
    }

    private func summaryItem(_ value: String, _ label: String) -> some View {
        VStack(spacing: 2) {
            Text(value)
                .font(.system(size: 14, weight: .bold, design: .rounded))
                .foregroundColor(Oh.text)
            Text(label)
                .font(.system(size: 9))
                .foregroundColor(Oh.textFaint)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
    }

    private var summaryDivider: some View {
        Rectangle()
            .fill(Oh.border.opacity(0.4))
            .frame(width: 0.5, height: 28)
    }
}
