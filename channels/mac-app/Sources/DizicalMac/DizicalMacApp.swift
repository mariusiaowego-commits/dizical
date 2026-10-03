// DizicalMac - macOS menu bar app wrapping the production dizical web UI
//
// 启动: 菜单栏图标 (不显示 dock icon, LSUIElement=true)
// 菜单栏点击: 弹 NSMenu (打开 / 浏览器 / 退出)
// 窗口: SwiftUI Window 单例 (dock click 只激活, 不创建多窗口)
// 页面: 纯远端壳, 直接打开生产环境, 不管理本机 uvicorn
//
// 编译: swift build -c release
// 打包: ./scripts/build-app.sh

import SwiftUI
import AppKit
import WebKit

// ============ 全局常量 ============
let DIZICAL_REMOTE_URL = "https://dizical-prod-283401-10-1454535414.sh.run.tcloudbase.com"

private let DIZICAL_REMOTE_HOST: String? = URL(string: DIZICAL_REMOTE_URL)?.host

// ============ WebView Delegate ============
class WebViewDelegate: NSObject, WKNavigationDelegate {
    weak var webView: WKWebView?
    private var retryCount = 0
    private let maxRetries = 3

    /// 页面加载失败回调
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!,
                 withError error: Error) {
        handleLoadError(error, webView: webView)
    }

    /// 页面加载失败回调（Provisional）
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!,
                 withError error: Error) {
        handleLoadError(error, webView: webView)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        retryCount = 0
    }

    /// 网络错误重试。上限 3 次, 按次数退避, 不再拉起本机服务。
    private func handleLoadError(_ error: Error, webView: WKWebView) {
        guard isConnectionError(error) else {
            return
        }

        guard retryCount < maxRetries else {
            retryCount = 0
            return
        }

        retryCount += 1
        let attempt = retryCount

        Task {
            try? await Task.sleep(nanoseconds: UInt64(attempt) * 500_000_000)
            await MainActor.run {
                if let url = URL(string: DIZICAL_REMOTE_URL) {
                    webView.load(URLRequest(url: url))
                }
            }
        }
    }

    /// 判断是否是连接错误
    private func isConnectionError(_ error: Error) -> Bool {
        let nsError = error as NSError
        // NSURLErrorCannotConnectToHost = -1004
        // NSURLErrorNetworkConnectionLost = -1005
        // NSURLErrorNotConnectedToInternet = -1009
        return nsError.domain == NSURLErrorDomain &&
               [-1004, -1005, -1009].contains(nsError.code)
    }

    /// 生产域名留在 app 内, 其余 http(s) 外链交给系统浏览器。
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else {
            decisionHandler(.allow)
            return
        }

        if url.scheme == "http" || url.scheme == "https" {
            if url.host == DIZICAL_REMOTE_HOST {
                decisionHandler(.allow)
            } else {
                decisionHandler(.cancel)
                NSWorkspace.shared.open(url)
            }
        } else {
            decisionHandler(.allow)
        }
    }
}

// ============ AppDelegate: 菜单栏 + 顶部菜单栏 (窗口让 SwiftUI 管) ============
class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private var statusMenuItem: NSMenuItem!

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

        // 3a. 生产环境指示 (灰色, 不可点)
        statusMenuItem = NSMenuItem(title: "● 生产环境", action: nil, keyEquivalent: "")
        statusMenuItem.isEnabled = false
        menu.addItem(statusMenuItem)

        menu.addItem(NSMenuItem.separator())

        // 3b. 刷新页面
        let reloadItem = NSMenuItem(title: "刷新页面", action: #selector(reloadPage), keyEquivalent: "r")
        reloadItem.target = self
        menu.addItem(reloadItem)

        // 3c. 打开 dizical
        let openItem = NSMenuItem(title: "打开 dizical", action: #selector(openWindow), keyEquivalent: "o")
        openItem.target = self
        menu.addItem(openItem)

        // 3d. 在浏览器打开
        let browserItem = NSMenuItem(title: "在浏览器打开 dizical", action: #selector(openInBrowser), keyEquivalent: "b")
        browserItem.target = self
        menu.addItem(browserItem)

        menu.addItem(NSMenuItem.separator())

        // 3e. 退出
        let quitItem = NSMenuItem(title: "退出", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem.menu = menu
    }

    // 菜单栏点击 = 显示菜单 (statusItem.menu 自动处理, 这里不写)
    @objc func statusItemClicked(_ sender: Any?) { /* 菜单自动弹出 */ }

    // "打开 dizical" 菜单项: 激活 SwiftUI Window
    @objc func openWindow() {
        NSApp.activate(ignoringOtherApps: true)
        for window in NSApp.windows {
            if window.identifier?.rawValue == "main" || window.title == "dizical" {
                window.makeKeyAndOrderFront(nil)
                return
            }
        }
    }

    @objc func openInBrowser() {
        if let url = URL(string: DIZICAL_REMOTE_URL) {
            NSWorkspace.shared.open(url)
        }
    }

    @objc func quit() {
        NSApp.terminate(nil)
    }

    @objc func reloadPage() {
        for window in NSApp.windows {
            if let webView = findWebView(in: window.contentView) {
                webView.reload()
                return
            }
        }
    }

    private func findWebView(in view: NSView?) -> WKWebView? {
        if let webView = view as? WKWebView { return webView }
        for subview in view?.subviews ?? [] {
            if let found = findWebView(in: subview) { return found }
        }
        return nil
    }

    // dock 点击 = 激活 + 找现有 window 激活 (不创建新的)
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
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
        return false
    }
}

// ============ WebView 包装 ============
struct DizicalWebView: NSViewRepresentable {
    let url: String

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.mediaTypesRequiringUserActionForPlayback = []

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.allowsBackForwardNavigationGestures = true
        webView.navigationDelegate = context.coordinator.delegate
        context.coordinator.delegate.webView = webView

        if let page = URL(string: url) {
            webView.load(URLRequest(url: page))
        }

        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {
        if nsView.url == nil, let page = URL(string: url) {
            nsView.load(URLRequest(url: page))
        }
    }

    class Coordinator {
        let delegate: WebViewDelegate

        init() {
            delegate = WebViewDelegate()
        }
    }
}

// ============ 窗口内容 ============
struct DizicalWindowView: View {
    var body: some View {
        DizicalWebView(url: DIZICAL_REMOTE_URL)
            .ignoresSafeArea()
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
            CommandGroup(after: .appInfo) {
                Button("打开 dizical") {
                    NSApp.activate(ignoringOtherApps: true)
                    for window in NSApp.windows {
                        if window.identifier?.rawValue == "main" || window.title == "dizical" {
                            window.makeKeyAndOrderFront(nil)
                            return
                        }
                    }
                }
                .keyboardShortcut("o", modifiers: [.command])

                Button("在浏览器打开 dizical") {
                    if let url = URL(string: DIZICAL_REMOTE_URL) {
                        NSWorkspace.shared.open(url)
                    }
                }
                .keyboardShortcut("b", modifiers: [.command])
            }
        }
    }
}
