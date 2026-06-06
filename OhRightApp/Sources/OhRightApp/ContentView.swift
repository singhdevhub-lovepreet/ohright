import SwiftUI
import Combine

struct ContentView: View {
    @StateObject var viewModel = OhRightViewModel()
    @State private var selectedTab = 0
    @State private var searchText = ""
    @State private var showSettings = false

    var body: some View {
        VStack(spacing: 0) {
            header
            tabBar
            if selectedTab == 0 { searchBar }
            divider
            content
            footer
        }
        .frame(width: 400, height: 560)
        .background(Oh.bg)
        .sheet(isPresented: $showSettings) {
            SettingsView()
                .preferredColorScheme(.dark)
        }
    }

    // MARK: - Header

    private var header: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(Oh.orange)
                .frame(width: 7, height: 7)

            Text("OhRight")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(Oh.text)

            Spacer()

            Button(action: { showSettings = true }) {
                Image(systemName: "gearshape")
                    .font(.system(size: 12))
                    .foregroundColor(Oh.textFaint)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 11)
    }

    // MARK: - Tab Bar

    private var tabBar: some View {
        HStack(spacing: 0) {
            ForEach(OhRightTab.allCases, id: \.rawValue) { tab in
                Button(action: {
                    withAnimation(.easeOut(duration: 0.12)) {
                        selectedTab = tab.rawValue
                    }
                    viewModel.loadTab(tab.rawValue)
                }) {
                    VStack(spacing: 5) {
                        HStack(spacing: 4) {
                            Image(systemName: tab.icon)
                                .font(.system(size: 9))
                            Text(tab.title)
                                .font(.system(size: 10, weight: selectedTab == tab.rawValue ? .medium : .regular))
                        }
                        .foregroundColor(selectedTab == tab.rawValue ? Oh.orange : Oh.textFaint)

                        RoundedRectangle(cornerRadius: 1)
                            .fill(selectedTab == tab.rawValue ? Oh.orange : Color.clear)
                            .frame(height: 1.5)
                    }
                    .padding(.vertical, 6)
                }
                .frame(maxWidth: .infinity)
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 16)
    }

    // MARK: - Search Bar

    private var searchBar: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 11))
                .foregroundColor(Oh.textFaint)

            TextField("Ask anything about your activity...", text: $searchText, onCommit: {
                viewModel.search(query: searchText)
            })
            .textFieldStyle(.plain)
            .font(.system(size: 12))
            .foregroundColor(Oh.text)

            if !searchText.isEmpty {
                Button(action: {
                    searchText = ""
                    viewModel.searchResults = []
                    viewModel.searchMessage = nil
                }) {
                    Image(systemName: "xmark")
                        .font(.system(size: 9, weight: .medium))
                        .foregroundColor(Oh.textFaint)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Oh.surface)
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Oh.border, lineWidth: 0.5)
        )
        .padding(.horizontal, 16)
        .padding(.bottom, 8)
    }

    private var divider: some View {
        Rectangle().fill(Oh.border).frame(height: 0.5)
    }

    // MARK: - Content

    private var content: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 6) {
                switch selectedTab {
                case 0: SearchResultsView(viewModel: viewModel)
                case 1: ObsessionsView(viewModel: viewModel)
                case 2: ProductsView(viewModel: viewModel)
                case 3: StatsView(viewModel: viewModel)
                default: EmptyView()
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
        }
    }

    // MARK: - Footer

    private var footer: some View {
        HStack {
            if let date = viewModel.lastRefresh {
                Text("Updated \(date, style: .relative) ago")
                    .font(.system(size: 9))
                    .foregroundColor(Oh.textFaint)
            }
            Spacer()
            Button(action: { viewModel.loadTab(selectedTab) }) {
                HStack(spacing: 3) {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 9))
                    Text("Refresh")
                        .font(.system(size: 10, weight: .medium))
                }
                .foregroundColor(Oh.orange)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(Oh.surface.opacity(0.5))
    }
}
