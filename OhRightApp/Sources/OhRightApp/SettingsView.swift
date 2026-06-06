import SwiftUI

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var screenpipeOk: Bool? = nil
    @State private var dbInfo = "Checking..."

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            // Header
            HStack {
                Text("Settings")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(Oh.text)
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(Oh.textFaint)
                }
                .buttonStyle(.plain)
            }

            Rectangle().fill(Oh.border).frame(height: 0.5)

            // Info rows
            VStack(spacing: 0) {
                row("folder", "Data", "~/.ohright", true)
                row("video.fill", "Screenpipe", screenpipeLabel, true)
                row("gearshape.2", "Engine", dbInfo, false)
            }
            .background(Oh.surface)
            .cornerRadius(8)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Oh.border, lineWidth: 0.5)
            )

            Rectangle().fill(Oh.border).frame(height: 0.5)

            // Actions
            HStack {
                Button(action: openTerminal) {
                    HStack(spacing: 4) {
                        Image(systemName: "terminal")
                            .font(.system(size: 10))
                        Text("Terminal")
                            .font(.system(size: 10, weight: .medium))
                    }
                    .foregroundColor(Oh.text)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Oh.surface)
                    .cornerRadius(6)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(Oh.border, lineWidth: 0.5)
                    )
                }
                .buttonStyle(.plain)

                Spacer()

                Button(action: { NSApplication.shared.terminate(nil) }) {
                    HStack(spacing: 4) {
                        Image(systemName: "power")
                            .font(.system(size: 10))
                        Text("Quit")
                            .font(.system(size: 10, weight: .medium))
                    }
                    .foregroundColor(Oh.red)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Oh.red.opacity(0.08))
                    .cornerRadius(6)
                }
                .buttonStyle(.plain)
            }

            Spacer()

            HStack {
                Spacer()
                Text("OhRight v0.1.0")
                    .font(.system(size: 9))
                    .foregroundColor(Oh.textFaint)
                Spacer()
            }
        }
        .padding(18)
        .frame(width: 320, height: 280)
        .background(Oh.bg)
        .onAppear {
            checkScreenpipe()
            checkDb()
        }
    }

    private var screenpipeLabel: String {
        guard let ok = screenpipeOk else { return "Checking..." }
        return ok ? "Connected" : "Offline"
    }

    private func row(_ icon: String, _ label: String, _ value: String, _ showDivider: Bool) -> some View {
        VStack(spacing: 0) {
            HStack {
                Image(systemName: icon)
                    .font(.system(size: 10))
                    .foregroundColor(Oh.orange)
                    .frame(width: 16)
                Text(label)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(Oh.text)
                Spacer()
                Text(value)
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundColor(Oh.textSoft)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)

            if showDivider {
                Rectangle()
                    .fill(Oh.border.opacity(0.4))
                    .frame(height: 0.5)
                    .padding(.leading, 36)
            }
        }
    }

    private func checkScreenpipe() {
        Task {
            guard let url = URL(string: "http://localhost:3030/health") else { return }
            var req = URLRequest(url: url)
            req.timeoutInterval = 3
            do {
                let (_, resp) = try await URLSession.shared.data(for: req)
                let ok = (resp as? HTTPURLResponse)?.statusCode == 200
                await MainActor.run { screenpipeOk = ok }
            } catch {
                await MainActor.run { screenpipeOk = false }
            }
        }
    }

    private func checkDb() {
        Task {
            let path = NSString("~/.ohright/ohright.db").expandingTildeInPath
            let fm = FileManager.default
            if fm.fileExists(atPath: path),
               let attrs = try? fm.attributesOfItem(atPath: path),
               let mod = attrs[.modificationDate] as? Date {
                let r = RelativeDateTimeFormatter()
                r.unitsStyle = .abbreviated
                let str = "Updated \(r.localizedString(for: mod, relativeTo: Date()))"
                await MainActor.run { dbInfo = str }
            } else {
                await MainActor.run { dbInfo = "No data" }
            }
        }
    }

    private func openTerminal() {
        let t = Process()
        t.executableURL = URL(fileURLWithPath: "/usr/bin/open")
        t.arguments = ["-a", "Terminal", NSString("~/.ohright").expandingTildeInPath]
        try? t.run()
    }
}
