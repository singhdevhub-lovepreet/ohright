import SwiftUI

struct ProductsView: View {
    @ObservedObject var viewModel: OhRightViewModel

    var body: some View {
        if viewModel.isLoading {
            LoadingView()
        } else if let error = viewModel.errorMessage {
            ErrorView(message: error)
        } else if viewModel.products.isEmpty {
            EmptyStateView(
                icon: "cart",
                title: "No products tracked",
                subtitle: "Things you research and shop for will appear here."
            )
        } else {
            ForEach(viewModel.products) { node in
                ProductRow(node: node)
            }
        }
    }
}

struct ProductRow: View {
    let node: OhRightNode
    @State private var showDetail = false
    @State private var hovered = false

    var body: some View {
        Button(action: { showDetail = true }) {
            HStack(spacing: 10) {
                Image(systemName: "cart")
                    .font(.system(size: 12))
                    .foregroundColor(Oh.orange)
                    .frame(width: 28, height: 28)
                    .background(Oh.orangeSoft)
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

                // Status + link
                VStack(alignment: .trailing, spacing: 3) {
                    if let status = node.status {
                        statusLabel(status)
                    }
                    if let url = node.url, !url.isEmpty {
                        Button(action: {
                            if let u = URL(string: url) { NSWorkspace.shared.open(u) }
                        }) {
                            HStack(spacing: 2) {
                                Image(systemName: "arrow.up.right")
                                    .font(.system(size: 7, weight: .bold))
                                Text("Open")
                                    .font(.system(size: 9))
                            }
                            .foregroundColor(Oh.orange)
                        }
                        .buttonStyle(.plain)
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

    private func statusLabel(_ status: String) -> some View {
        let color: Color = {
            switch status {
            case "active": return Oh.green
            case "dormant": return Oh.amber
            case "abandoned": return Oh.red
            default: return Oh.textFaint
            }
        }()
        let label: String = {
            switch status {
            case "active": return "Looking"
            case "dormant": return "Paused"
            case "abandoned": return "Dropped"
            default: return status
            }
        }()

        return HStack(spacing: 3) {
            Circle().fill(color).frame(width: 4, height: 4)
            Text(label)
                .font(.system(size: 9, weight: .medium))
                .foregroundColor(color)
        }
    }
}
