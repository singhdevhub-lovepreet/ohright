import SwiftUI
import AppKit

@main
struct OhRightApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        Settings {
            EmptyView()
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem?
    var popover: NSPopover?
    var contentViewController: NSHostingController<ContentView>?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide dock icon - we're a menu bar only app
        NSApp.setActivationPolicy(.accessory)
        
        // Create status item in menu bar
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        
        if let button = statusItem?.button {
            button.image = NSImage(systemSymbolName: "brain.head.profile", accessibilityDescription: "OhRight")
            button.image?.isTemplate = true
            button.action = #selector(togglePopover(_:))
            button.target = self
            button.sendAction(on: [.leftMouseUp, .rightMouseUp])
        }
        
        // Create popover with SwiftUI content
        let contentView = ContentView()
        let hostingController = NSHostingController(rootView: contentView)
        hostingController.view.frame.size = NSSize(width: 400, height: 560)
        self.contentViewController = hostingController
        
        popover = NSPopover()
        popover?.contentSize = NSSize(width: 400, height: 560)
        popover?.behavior = .transient
        popover?.contentViewController = hostingController
        popover?.animates = true
        popover?.appearance = NSAppearance(named: .darkAqua)
    }
    
    @objc func togglePopover(_ sender: AnyObject?) {
        guard let button = statusItem?.button, let popover = popover else { return }
        
        if popover.isShown {
            popover.performClose(sender)
        } else {
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            NSApp.activate(ignoringOtherApps: true)
        }
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        popover?.close()
    }
}