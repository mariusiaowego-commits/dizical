// DizicalMac - macOS menu bar app wrapping dizical web UI
//
// 启动: 不显示 dock icon, 只在菜单栏
// 菜单栏点击: 弹出 popover (WebView 显示 dizical http://127.0.0.1:8765)
// 菜单: "Open in Browser" / "Quit"
//
// 编译: swift build -c release
// 打包: ./scripts/build-app.sh

import SwiftUI
import AppKit
import WebKit

// ============ 全局常量 ============
let DIZICAL_URL = "http://127.0.0.1:8765"

// ============ AppDelegate: 菜单栏 + 窗口管理 ============
class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    private var statusItem: NSStatusItem!
    private var mainWindow: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // 1. LSUIElement=true 时 .regular 也不显示 dock icon
        //    但能在 Cmd+Tab 任务栏 / 菜单栏 显示 — 比 .accessory 更专业
        //    P0 修复: 保持 .regular, 不再切换
        NSApp.setActivationPolicy(.regular)

        // 2. 创建菜单栏图标
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            // 用自定义 .icns (女孩吹笛极简线稿, 黑白色)
            // 不放 SwiftPM bundle (避免 iconset 重名冲突), 直接从 .app/Contents/Resources 读
            let iconPath = Bundle.main.bundlePath + "/Contents/Resources/menubar-icon.icns"
            if let icon = NSImage(contentsOfFile: iconPath) {
                icon.isTemplate = true  // template mode: macOS 自动黑/白
                // 调整大小: macOS 菜单栏图标标准 18pt (@2x = 36px, @3x = 54px)
                icon.size = NSSize(width: 18, height: 18)
                button.image = icon
            } else {
                // 兜底: SF Symbol music.note
                button.image = NSImage(systemSymbolName: "music.note", accessibilityDescription: "dizical")
                button.image?.isTemplate = true
            }
            // 用户要求: 菜单栏点击 = 弹菜单, 不是直接开窗
            button.action = #selector(statusItemClicked(_:))
            button.target = self
        }

        // 3. 创建主窗口 (隐藏, 等用户点菜单再显示)
        setupMainWindow()
    }

    func setupMainWindow() {
        let window = NSWindow(
            // 用户要求: 3 倍大, 跟 27" 显示器匹配
            contentRect: NSRect(x: 100, y: 100, width: 2560, height: 1400),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "dizical"
        window.contentViewController = NSHostingController(rootView: DizicalWindowView())
        window.center()
        window.isReleasedWhenClosed = false  // 关闭时不销毁, 隐藏备用
        window.delegate = self
        self.mainWindow = window
    }

    // 用户要求: 菜单栏点击 = 弹菜单 (不是直接开窗)
    // 菜单项: 打开 dizical / 在浏览器打开 / 退出
    @objc func statusItemClicked(_ sender: AnyObject?) {
        let menu = NSMenu()

        let openItem = NSMenuItem(title: "打开 dizical", action: #selector(openWindow), keyEquivalent: "o")
        openItem.target = self
        menu.addItem(openItem)

        let inBrowserItem = NSMenuItem(title: "在浏览器打开", action: #selector(openInBrowser), keyEquivalent: "b")
        inBrowserItem.target = self
        menu.addItem(inBrowserItem)

        menu.addItem(NSMenuItem.separator())

        let quitItem = NSMenuItem(title: "退出", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem.menu = menu
        statusItem.button?.performClick(nil)
        // 菜单关闭后清空 (下次点击能重新触发)
        DispatchQueue.main.async {
            self.statusItem.menu = nil
        }
    }

    @objc func openWindow() {
        guard let window = mainWindow else { return }
        // 总是 unminimize + 提到前面 + 激活 (用户要求: Cmd+Space 打开要 focus)
        if window.isMiniaturized {
            window.deminiaturize(nil)
        }
        NSApp.activate(ignoringOtherApps: true)
        window.makeKeyAndOrderFront(nil)
    }

    // 窗口关闭: 隐藏备用, 不退出 app, 不切 activation policy
    func windowWillClose(_ notification: Notification) {
        // 不切 policy, 不退出. 窗口 hide 备用, 菜单栏图标还在
    }

    // 菜单项: Open in Browser
    @objc func openInBrowser() {
        if let url = URL(string: DIZICAL_URL) {
            NSWorkspace.shared.open(url)
        }
    }

    // 菜单项: Quit
    @objc func quit() {
        NSApp.terminate(nil)
    }

    // 用户要求: dock 点击 = 打开 dizical 窗口
    // macOS dock click 默认行为: app 已开则前置, 没开则启动
    // 修: 总是 openWindow (不管 flag) — 解决"打开但不 focus"问题
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        openWindow()
        return true
    }
}

// ============ 窗口内容: WebView 嵌 dizical ============
// P1-3 修复: 去掉顶栏工具栏, WebView 顶满窗口 (dizical 自己的 header/nav 足够)
struct DizicalWindowView: View {
    var body: some View {
        DizicalWebView(url: URL(string: DIZICAL_URL)!)
            .frame(minWidth: 800, minHeight: 500)
    }
}

// ============ WebView 包装 (SwiftUI 没有原生 WebView, 用 NSViewRepresentable 包 WKWebView) ============
// P1-2 修复: 加 customUserAgent + WKProcessPool + 外部链接拦截
struct DizicalWebView: NSViewRepresentable {
    let url: URL

    // 进程池 (cookie / localStorage 跨 WebView 共享)
    private static let processPool = WKProcessPool()

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.processPool = Self.processPool
        // 允许内联媒体自动播放
        config.mediaTypesRequiringUserActionForPlayback = []

        let webView = WKWebView(frame: .zero, configuration: config)
        // 自定义 UA, 让 dizical 后端知道是 mac app 访问
        webView.customUserAgent = "DizicalMac/0.1 (macOS) \(WKWebView().value(forKey: "userAgent") as? String ?? "")"
        webView.allowsBackForwardNavigationGestures = true
        // 导航 delegate, 拦截外部链接 (跳浏览器而不是在 app 内打开任意网站)
        webView.navigationDelegate = context.coordinator
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {
        if nsView.url != url {
            nsView.load(URLRequest(url: url))
        }
    }

    // Coordinator: 处理导航决策 (拦截外部链接)
    class Coordinator: NSObject, WKNavigationDelegate {
        func webView(_ webView: WKWebView,
                    decidePolicyFor navigationAction: WKNavigationAction,
                    decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = navigationAction.request.url else {
                decisionHandler(.allow)
                return
            }
            // 只允许 dizical localhost 链接在 app 内打开
            // 其他 (http://, https:// 外部网站) 跳系统浏览器
            if url.scheme == "http" || url.scheme == "https" {
                if url.host == "127.0.0.1" || url.host == "localhost" {
                    decisionHandler(.allow)  // 允许 dizical 内部导航
                } else {
                    decisionHandler(.cancel)
                    NSWorkspace.shared.open(url)  // 外部链接 → 浏览器
                }
            } else {
                decisionHandler(.allow)
            }
        }

        // 加载失败时, 显示友好提示 (P2-3 顺手做)
        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            showConnectionError()
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            showConnectionError()
        }

        private func showConnectionError() {
            let alert = NSAlert()
            alert.messageText = "无法连接 dizical 后端"
            alert.informativeText = "请确认 dizical 服务已启动:\n\ncd /Users/mt16/dev/dizical\npython3 -m src.kid_app start --port 8765"
            alert.alertStyle = .warning
            alert.addButton(withTitle: "好")
            alert.addButton(withTitle: "在浏览器打开")
            if alert.runModal() == .alertSecondButtonReturn {
                if let url = URL(string: DIZICAL_URL) {
                    NSWorkspace.shared.open(url)
                }
            }
        }
    }
}

// ============ 入口 ============
// 使用 SwiftUI App 协议 (比 NSApplication 老式入口更现代, 自动装菜单栏 File/Edit/View/Window/Help)
@main
struct DizicalMacApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        // 用 Window 不用 WindowGroup — Window 单例, 不允许多个窗口
        // (否则 dock 多次点击会启多个窗口, 出现"大小不一"问题)
        Window("dizical", id: "main") {
            DizicalWindowView()
        }
        .defaultSize(width: 2560, height: 1400)  // 27" 显示器匹配
        .windowResizability(.contentMinSize)  // 最小 800x500, 默认 2560x1400
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        .commands {
            // 顶部菜单栏添加 "dizical" 自定义菜单 (在 Help 之后)
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
