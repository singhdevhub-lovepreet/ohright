import SwiftUI

struct ObsessionsView: View {
    @ObservedObject var viewModel: OhRightViewModel

    var body: some View {
        if viewModel.isLoading {
            LoadingView()
        } else if let error = viewModel.errorMessage {
            ErrorView(message: error)
        } else if viewModel.obsessions.isEmpty {
            EmptyStateView(
                icon: "flame",
                title: "Nothing here yet",
                subtitle: "Your most visited topics and interests will show up here."
            )
        } else {
            ForEach(viewModel.obsessions) { node in
                ObsessionRow(node: node)
            }
        }
    }
}

struct ObsessionRow: View {
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

                    HStack(spacing: 8) {
                        if !node.subtitle.isEmpty {
                            Text(node.subtitle)
                                .font(.system(size: 10))
                                .foregroundColor(Oh.textFaint)
                                .lineLimit(1)
                        }
                    }
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 2) {
                    if let time = node.timeSpent, !time.isEmpty {
                        Text(time)
                            .font(.system(size: 11, weight: .medium, design: .monospaced))
                            .foregroundColor(Oh.text)
                    }

                    if let revisits = node.revisits, revisits > 0 {
                        Text("\(revisits) visits")
                            .font(.system(size: 9))
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
