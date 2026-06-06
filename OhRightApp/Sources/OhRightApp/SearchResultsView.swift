import SwiftUI

struct SearchResultsView: View {
    @ObservedObject var viewModel: OhRightViewModel

    var body: some View {
        if viewModel.isLoading {
            LoadingView()
        } else if let error = viewModel.errorMessage {
            ErrorView(message: error)
        } else if viewModel.searchResults.isEmpty {
            EmptyStateView(
                icon: "magnifyingglass",
                title: "Search your activity",
                subtitle: "Try something like \"what product was I looking at last week?\""
            )
        } else {
            if let msg = viewModel.searchMessage {
                Text(msg)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(Oh.textSoft)
                    .padding(.bottom, 4)
            }

            ForEach(viewModel.searchResults) { node in
                ResultRow(node: node)
            }
        }
    }
}

struct ResultRow: View {
    let node: OhRightNode
    @State private var showDetail = false
    @State private var hovered = false

    var body: some View {
        Button(action: { showDetail = true }) {
            HStack(spacing: 10) {
                Image(systemName: Oh.categoryIcon(node.type))
                    .font(.system(size: 12))
                    .foregroundColor(Oh.categoryColor(node.type))
                    .frame(width: 28, height: 28)
                    .background(Oh.categoryColor(node.type).opacity(0.1))
                    .cornerRadius(6)

                VStack(alignment: .leading, spacing: 3) {
                    Text(node.title)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(Oh.text)
                        .lineLimit(1)

                    if !node.subtitle.isEmpty {
                        Text(node.subtitle)
                            .font(.system(size: 10))
                            .foregroundColor(Oh.textFaint)
                            .lineLimit(1)
                    }
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 2) {
                    Text(node.type)
                        .font(.system(size: 9, weight: .medium))
                        .foregroundColor(Oh.categoryColor(node.type))

                    if let time = node.timeSpent, !time.isEmpty {
                        Text(time)
                            .font(.system(size: 9, design: .monospaced))
                            .foregroundColor(Oh.textFaint)
                    }
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(hovered ? Oh.surfaceRaised : Oh.surface)
            .cornerRadius(8)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { h in withAnimation(.easeOut(duration: 0.1)) { hovered = h } }
        .popover(isPresented: $showDetail, attachmentAnchor: .rect(.bounds), arrowEdge: .trailing) {
            NodeDetailView(node: node)
                .frame(width: 280)
                .padding(14)
                .background(Oh.bg)
                .preferredColorScheme(.dark)
        }
    }
}
