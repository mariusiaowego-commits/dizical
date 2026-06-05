// DizicalMac - macOS menu bar app wrapping dizical web UI
//
// 启动: 菜单栏图标 (不显示 dock icon, LSUIElement=true)
// 菜单栏点击: 弹 NSMenu (打开 / 浏览器 / 退出)
// 窗口: SwiftUI Window 单例 (dock click 只激活, 不创建多窗口)
//
// 编译: swift build -c release
// 打包: ./scripts/build-app.sh

import SwiftUI
import AppKit
import WebKit

// ============ 全局常量 ============
let DIZICAL_URL = "http://127.0.0.1:8765"

// ============ AppDelegate: 菜单栏 + 顶部菜单栏 (窗口让 SwiftUI 管) ============
class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!

    func applicationDidFinishLaunching(_ notification: Notification) {
        // 1. 设置 activation policy (regular 让 Cmd+Tab 看到, LSUIElement 让 dock 不显示)
        NSApp.setActivationPolicy(.regular)

        // 2. 创建菜单栏图标
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            // 优先用 collapse icon 资源, 没有则用 SF Symbol
            if let iconPath = Bundle.main.bundlePath + "/Contents/Resources/menubar-icon.icns" as String?,
               let icon = NSImage(contentsOfFile: iconPath) {
                icon.isTemplate = true
                icon.size = NSSize(width: 18, height: 18)
                button.image = icon
            } else {
                button.image = NSImage(systemSymbolName: "music.note", accessibilityDescription: "dizical")
                button.image?.isTemplate = true
            }
            // 菜单栏点击 = 弹菜单 (不直接开窗, 防误点)
            button.action = #selector(statusItemClicked(_:))
            button.target = self
        }

        // 3. 菜单栏菜单项
        let menu = NSMenu()
        let openItem = NSMenuItem(title: "打开 dizical", action: #selector(openWindow), keyEquivalent: "o")
        openItem.target = self
        menu.addItem(openItem)
        let browserItem = NSMenuItem(title: "在浏览器打开 dizical", action: #selector(openInBrowser), keyEquivalent: "b")
        browserItem.target = self
        menu.addItem(browserItem)
        menu.addItem(NSMenuItem.separator())
        let quitItem = NSMenuItem(title: "退出", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)
        statusItem.menu = menu
    }

    // 菜单栏点击 = 显示菜单 (statusItem.menu 自动处理, 这里不写)
    @objc func statusItemClicked(_ sender: Any?) { /* 菜单自动弹出 */ }

    // "打开 dizical" 菜单项: 激活 SwiftUI Window
    @objc func openWindow() {
        // 用 NSApp activate + SwiftUI Window 自动 manage 自身
        NSApp.activate(ignoringOtherApps: true)
        // 找现有 window 激活 (不创建新的)
        for window in NSApp.windows {
            if window.identifier?.rawValue == "main" || window.title == "dizical" {
                window.makeKeyAndOrderFront(nil)
                return
            }
        }
        // 没找到: 跳过 (SwiftUI Window 应该自动管理)
    }

    @objc func openInBrowser() {
        if let url = URL(string: DIZICAL_URL) {
            NSWorkspace.shared.open(url)
        }
    }

    @objc func quit() {
        NSApp.terminate(nil)
    }

    // dock 点击 = 激活 + 找现有 window 激活 (不创建新的)
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        // 找 SwiftUI Window 激活
        for window in NSApp.windows {
            if window.identifier?.rawValue == "main" || window.title == "dizical" {
                window.makeKeyAndOrderFront(nil)
                return true
            }
        }
        return true
    }

    // 用户要求: Cmd+W = hide (不退出), Cmd+Q = 退出
    // 关窗 ≠ 退 app. 关窗后菜单栏还在, dock click 重新显示窗口
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return false  // 关窗不退出, app 保留在 dock + 菜单栏
    }
}

// ============ WebView 包装 ============
struct DizicalWebView: NSViewRepresentable {
    let url: String

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.mediaTypesRequiringUserActionForPlayback = []
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.allowsBackForwardNavigationGestures = true
        if let url = URL(string: url) {
            webView.load(URLRequest(url: url))
        }
        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {
        // no-op
    }
}

// ============ 窗口内容 (WebView 顶满) ============
struct DizicalWindowView: View {
    var body: some View {
        DizicalWebView(url: DIZICAL_URL)
    }
}

// ============ 入口 ============
// 使用 SwiftUI App 协议 (比 NSApplication 老式入口更现代, 自动装菜单栏 File/Edit/View/Window/Help)
@main
struct DizicalMacApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        // 用 Window 不用 WindowGroup — Window 单例, dock 点多次 = 同一窗口
        Window("dizical", id: "main") {
            DizicalWindowView()
        }
        .defaultSize(width: 2560, height: 1400)  // 27" 显示器匹配
        .windowResizability(.contentMinSize)
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        .commands {
            // 顶部菜单栏添加 dizical 自定义菜单 (File 菜单区)
            CommandGroup(after: .appInfo) {
                Button("在浏览器打开 dizical") {
                    if let url = URL(string: DIZICAL_URL) {
                        NSWorkspace.shared.open(url)
                    }
                }
                .keyboardShortcut("b", modifiers: [.command])
            }
        }
    }
}
