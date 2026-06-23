// DizicalMac - macOS menu bar app wrapping dizical web UI
//
// 启动: 菜单栏图标 (不显示 dock icon, LSUIElement=true)
// 菜单栏点击: 弹 NSMenu (打开 / 浏览器 / 退出)
// 窗口: SwiftUI Window 单例 (dock click 只激活, 不创建多窗口)
// 服务管理: 事件驱动, 按需启动 uvicorn (无定时轮询)
//
// 编译: swift build -c release
// 打包: ./scripts/build-app.sh

import SwiftUI
import AppKit
import WebKit
import Combine

// ============ 全局常量 ============
// kid-app 内嵌 webview 仍走 127.0.0.1 (最优路由), 但服务本身绑 0.0.0.0 让 iPad (局域网/Tailscale) 能访问
let DIZICAL_URL = "http://127.0.0.1:8765"
let DIZICAL_PORT = 8765
let DIZICAL_HOST = "0.0.0.0"          // ⚠️ 不要改 127.0.0.1, 否则 iPad 必 400
let DIZICAL_WORK_DIR = "/Users/mt16/dev/dizical"
let DIZICAL_PIDFILE = "/tmp/dizical-8765.pid"
let DIZICAL_LOGFILE = "/tmp/dizical-8765.log"

// 查找 uvicorn 完整路径（macOS GUI app 的 PATH 不含 /opt/homebrew/bin）
func findUvicornPath() -> String {
    let candidates = [
        "/opt/homebrew/bin/uvicorn",
        "/usr/local/bin/uvicorn",
        "/Users/mt16/.local/bin/uvicorn",
        "/usr/bin/uvicorn"
    ]
    for path in candidates {
        if FileManager.default.isExecutableFile(atPath: path) {
            return path
        }
    }
    let task = Process()
    task.executableURL = URL(fileURLWithPath: "/bin/zsh")
    task.arguments = ["-l", "-c", "which uvicorn"]
    let pipe = Pipe()
    task.standardOutput = pipe
    task.standardError = Pipe()
    try? task.run()
    task.waitUntilExit()
    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    return output.isEmpty ? "/opt/homebrew/bin/uvicorn" : output
}

let UVICORN_PATH = findUvicornPath()

// 查询 8765 端口占用进程的 PID (lsof), 用于菜单栏状态显示
// 返回 nil = 没在跑
func getUvicornPID() -> String? {
    let task = Process()
    task.executableURL = URL(fileURLWithPath: "/usr/sbin/lsof")
    task.arguments = ["-nP", "-iTCP:\(DIZICAL_PORT)", "-sTCP:LISTEN", "-t"]
    let pipe = Pipe()
    task.standardOutput = pipe
    task.standardError = Pipe()
    do {
        try task.run()
        task.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        let pid = String(data: data, encoding: .utf8)?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return (pid?.isEmpty == false) ? pid : nil
    } catch {
        return nil
    }
}

// ============ 服务状态枚举 ============
enum ServiceStatus: Equatable {
    case idle           // 空闲
    case checking       // 检查中
    case starting       // 启动中
    case running        // 运行中
    case failed(String) // 失败
    
    var description: String {
        switch self {
        case .idle: return "空闲"
        case .checking: return "检查中..."
        case .starting: return "启动中..."
        case .running: return "运行中"
        case .failed(let error): return "失败: \(error)"
        }
    }
}

// ============ 服务管理器（事件驱动，按需启动） ============
class ServiceManager: ObservableObject {
    @Published var status: ServiceStatus = .idle
    
    private var process: Process?
    private let startupTimeout: TimeInterval = 10.0
    private let maxRetries = 3
    private var retryCount = 0
    
    // MARK: - 公共方法
    
    /// 确保服务运行（按需启动）
    func ensureServiceRunning() async -> Bool {
        // 1. 快速检查端口
        if isPortOpen() {
            await MainActor.run { status = .running }
            return true
        }
        
        // 2. 启动服务
        await MainActor.run { status = .starting }
        return await startUvicorn()
    }
    
    /// 停止服务
    /// - 如果是 mac app 自己启的进程, 走 SIGTERM (Process API)
    /// - 如果是外部 (shell 脚本/systemd) 启的进程, 走 lsof 查 PID + kill() 系统调用
    /// - 两条路径都更新 status = .idle
    func stopService() {
        // 路径 A: mac app 自己启的进程, 用 Process API
        if let process = self.process, process.isRunning {
            process.terminate()
            // 等待进程结束
            let deadline = Date().addingTimeInterval(5.0)
            while process.isRunning && Date() < deadline {
                Thread.sleep(forTimeInterval: 0.1)
            }
            // 如果还在运行，强制终止
            if process.isRunning {
                process.interrupt()
            }
            DispatchQueue.main.async {
                self.status = .idle
            }
            return
        }

        // 路径 B: 外部启的进程 (shell 脚本/systemd), 用 lsof + kill 系统调用
        Task { @MainActor in
            guard let pidStr = getUvicornPID(), let pid = Int32(pidStr) else {
                // 端口都没占用, 已经停了
                self.status = .idle
                return
            }
            // 优雅 TERM
            kill(pid, SIGTERM)
            // 等最多 5 秒
            for _ in 0..<50 {
                if kill(pid, 0) != 0 { break }  // 进程没了
                try? await Task.sleep(nanoseconds: 100_000_000)
            }
            // 还活着就 KILL
            if kill(pid, 0) == 0 {
                kill(pid, SIGKILL)
                try? await Task.sleep(nanoseconds: 200_000_000)
            }
            self.status = .idle
        }
    }

    /// 重启服务
    /// - 路径 A (自己启的): 走原 stopService + ensureServiceRunning
    /// - 路径 B (外部启的): stopService (lsof+kill) + ensureServiceRunning (启一个新进程, 自己管的)
    func restartService() async -> Bool {
        // 先停 (可能停的是外部进程, 异步路径)
        stopService()
        // 等 stopService 完成 (路径 B 是 async)
        try? await Task.sleep(nanoseconds: 1_500_000_000)  // 1.5s
        retryCount = 0
        return await ensureServiceRunning()
    }
    
    // MARK: - 私有方法
    
    /// 快速检查端口是否监听（< 10ms）
    private func isPortOpen() -> Bool {
        let sock = socket(AF_INET, SOCK_STREAM, 0)
        guard sock >= 0 else { return false }
        defer { close(sock) }
        
        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = in_port_t(DIZICAL_PORT).bigEndian
        inet_pton(AF_INET, DIZICAL_HOST, &addr.sin_addr)
        
        let result = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                connect(sock, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        
        return result == 0
    }
    
    /// 启动 uvicorn 进程
    private func startUvicorn() async -> Bool {
        // 检查重试次数
        guard retryCount < maxRetries else {
            await MainActor.run { status = .failed("重试次数已达上限") }
            return false
        }
        
        retryCount += 1
        
        // 创建进程
        let newProcess = Process()
        newProcess.executableURL = URL(fileURLWithPath: UVICORN_PATH)
        newProcess.arguments = [
            "src.kid_app.app:app",
            "--host", DIZICAL_HOST,
            "--port", "\(DIZICAL_PORT)",
            "--log-level", "warning"  // 减少日志输出
        ]
        newProcess.currentDirectoryURL = URL(fileURLWithPath: DIZICAL_WORK_DIR)
        
        // 设置环境变量
        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONUNBUFFERED"] = "1"
        newProcess.environment = environment
        
        // 配置输出管道（静默模式，不捕获日志）
        let devNull = FileHandle.nullDevice
        newProcess.standardOutput = devNull
        newProcess.standardError = devNull
        
        // 进程退出处理
        newProcess.terminationHandler = { [weak self] process in
            DispatchQueue.main.async {
                self?.handleProcessTermination(process)
            }
        }
        
        // 启动进程
        do {
            try newProcess.run()
            self.process = newProcess
            return await waitForService()
        } catch {
            await MainActor.run { status = .failed("启动失败: \(error.localizedDescription)") }
            return false
        }
    }
    
    /// 等待服务就绪
    private func waitForService() async -> Bool {
        let startTime = Date()
        
        while Date().timeIntervalSince(startTime) < startupTimeout {
            if isPortOpen() {
                await MainActor.run {
                    status = .running
                    retryCount = 0
                }
                return true
            }
            
            // 检查进程是否还在运行
            if let process = process, !process.isRunning {
                await MainActor.run { status = .failed("进程异常退出") }
                return false
            }
            
            try? await Task.sleep(nanoseconds: 500_000_000) // 0.5 秒
        }
        
        await MainActor.run { status = .failed("启动超时") }
        return false
    }
    
    /// 处理进程退出
    private func handleProcessTermination(_ process: Process) {
        let exitCode = process.terminationStatus
        
        if exitCode != 0 {
            status = .failed("进程异常退出，退出码: \(exitCode)")
        } else {
            status = .idle
        }
    }
}

// ============ WebView Delegate ============
class WebViewDelegate: NSObject, WKNavigationDelegate {
    weak var serviceManager: ServiceManager?
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
    
    /// 处理加载错误
    private func handleLoadError(_ error: Error, webView: WKWebView) {
        // 检查是否是连接错误
        guard isConnectionError(error) else {
            return
        }
        
        // 检查重试次数
        guard retryCount < maxRetries else {
            retryCount = 0
            return
        }
        
        retryCount += 1
        
        // 尝试启动服务并重试
        Task {
            guard let serviceManager = serviceManager else { return }
            
            if await serviceManager.ensureServiceRunning() {
                // 等待一小段时间让服务完全就绪
                try? await Task.sleep(nanoseconds: 500_000_000)
                
                // 重试加载
                await MainActor.run {
                    if let url = URL(string: DIZICAL_URL) {
                        webView.load(URLRequest(url: url))
                    }
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
    
    /// 重置重试计数
    func resetRetryCount() {
        retryCount = 0
    }
    
    // 限制外部链接在浏览器打开
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, 
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else {
            decisionHandler(.allow)
            return
        }
        
        if url.scheme == "http" || url.scheme == "https" {
            if url.host == "127.0.0.1" || url.host == "localhost" {
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
    private let serviceManager = ServiceManager()
    private var statusMenuItem: NSMenuItem!
    private var startMenuItem: NSMenuItem!
    private var restartMenuItem: NSMenuItem!
    private var stopMenuItem: NSMenuItem!

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

        // 3a. 状态显示 (灰色, 不可点)
        statusMenuItem = NSMenuItem(title: "● 检查中...", action: nil, keyEquivalent: "")
        statusMenuItem.isEnabled = false
        menu.addItem(statusMenuItem)

        menu.addItem(NSMenuItem.separator())

        // 3b. 启动
        startMenuItem = NSMenuItem(title: "启动服务", action: #selector(startService), keyEquivalent: "s")
        startMenuItem.target = self
        menu.addItem(startMenuItem)

        // 3c. 重启
        restartMenuItem = NSMenuItem(title: "重启服务", action: #selector(restartService), keyEquivalent: "r")
        restartMenuItem.target = self
        menu.addItem(restartMenuItem)

        // 3d. 停止
        stopMenuItem = NSMenuItem(title: "停止服务", action: #selector(stopService), keyEquivalent: "x")
        stopMenuItem.target = self
        menu.addItem(stopMenuItem)

        menu.addItem(NSMenuItem.separator())

        // 3e. 刷新页面
        let reloadItem = NSMenuItem(title: "刷新页面", action: #selector(reloadPage), keyEquivalent: "r")
        reloadItem.target = self
        menu.addItem(reloadItem)

        // 3f. 打开 dizical
        let openItem = NSMenuItem(title: "打开 dizical", action: #selector(openWindow), keyEquivalent: "o")
        openItem.target = self
        menu.addItem(openItem)

        // 3f. 在浏览器打开
        let browserItem = NSMenuItem(title: "在浏览器打开 dizical", action: #selector(openInBrowser), keyEquivalent: "b")
        browserItem.target = self
        menu.addItem(browserItem)

        menu.addItem(NSMenuItem.separator())

        // 3g. 退出
        let quitItem = NSMenuItem(title: "退出", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem.menu = menu

        // 4. 监听 serviceManager.status 变化, 联动菜单栏 UI (@Published 用 Combine sink)
        serviceManager.$status
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in
                self?.refreshMenuState()
            }
            .store(in: &cancellables)

        // 5. 启动时主动检查一次 (不等用户点)
        Task { @MainActor in
            _ = await serviceManager.ensureServiceRunning()
            self.refreshMenuState()
        }
    }

    // Combine 订阅存储
    private var cancellables = Set<AnyCancellable>()

    // MARK: - 菜单栏 UI 状态更新
    private func refreshMenuState() {
        let s = serviceManager.status
        // 状态文字
        switch s {
        case .idle:
            statusMenuItem.title = "○ 空闲 (未运行)"
        case .checking:
            statusMenuItem.title = "● 检查中..."
        case .starting:
            statusMenuItem.title = "● 启动中..."
        case .running:
            statusMenuItem.title = "● 运行中 (PID \(getUvicornPID() ?? "?"))"
        case .failed(let err):
            statusMenuItem.title = "✗ 失败: \(err)"
        }
        // 按钮可用性: 启动中/检查中 时禁用所有控制按钮
        let busy = (s == .starting || s == .checking)
        startMenuItem.isEnabled = !busy && s != .running
        restartMenuItem.isEnabled = !busy
        stopMenuItem.isEnabled = !busy && s == .running
    }

    deinit {
        // Combine sink 跟 cancellables 走, 无需手动 removeObserver
    }

    // 菜单栏点击 = 显示菜单 (statusItem.menu 自动处理, 这里不写)
    @objc func statusItemClicked(_ sender: Any?) { /* 菜单自动弹出 */ }

    // MARK: - 服务控制
    @objc func startService() {
        Task { @MainActor in
            _ = await serviceManager.ensureServiceRunning()
        }
    }

    @objc func restartService() {
        Task { @MainActor in
            _ = await serviceManager.restartService()
        }
    }

    @objc func stopService() {
        serviceManager.stopService()
    }

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
        // Cmd+Q: 真正退出, 停服务
        serviceManager.stopService()
        NSApp.terminate(nil)
    }

    @objc func reloadPage() {
        // Cmd+R: 刷新 WKWebView 页面 (清缓存重载)
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

    // mac app 退出 (Cmd+Q) 时清理服务, 防止孤儿进程
    func applicationWillTerminate(_ notification: Notification) {
        serviceManager.stopService()
    }
}

// ============ 启动状态视图 ============
struct ServiceStatusView: View {
    @ObservedObject var serviceManager: ServiceManager
    let onRetry: () -> Void
    
    var body: some View {
        VStack(spacing: 20) {
            // 状态图标
            statusIcon
            
            // 状态文本
            statusText
            
            // 进度指示器
            if serviceManager.status == .starting || serviceManager.status == .checking {
                ProgressView()
                    .scaleEffect(1.5)
            }
            
            // 操作按钮
            actionButtons
        }
        .padding(40)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(NSColor.windowBackgroundColor))
    }
    
    private var statusIcon: some View {
        Group {
            switch serviceManager.status {
            case .idle:
                Image(systemName: "circle")
                    .font(.system(size: 60))
                    .foregroundColor(.gray)
            case .checking:
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 60))
                    .foregroundColor(.blue)
            case .starting:
                Image(systemName: "arrow.triangle.2.circlepath")
                    .font(.system(size: 60))
                    .foregroundColor(.orange)
            case .running:
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 60))
                    .foregroundColor(.green)
            case .failed:
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 60))
                    .foregroundColor(.red)
            }
        }
    }
    
    private var statusText: some View {
        Group {
            switch serviceManager.status {
            case .idle:
                Text("准备就绪")
                    .font(.title2)
            case .checking:
                Text("正在检查服务状态...")
                    .font(.title2)
            case .starting:
                Text("正在启动 dizical 服务...")
                    .font(.title2)
            case .running:
                Text("服务运行中")
                    .font(.title2)
                    .foregroundColor(.green)
            case .failed(let error):
                VStack(spacing: 8) {
                    Text("启动失败")
                        .font(.title2)
                        .foregroundColor(.red)
                    Text(error)
                        .font(.body)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
            }
        }
    }
    
    private var actionButtons: some View {
        Group {
            switch serviceManager.status {
            case .failed:
                Button("重试") {
                    onRetry()
                }
                .buttonStyle(.borderedProminent)
            default:
                EmptyView()
            }
        }
    }
}

// ============ WebView 包装 ============
struct DizicalWebView: NSViewRepresentable {
    @ObservedObject var serviceManager: ServiceManager
    let url: String
    
    func makeCoordinator() -> Coordinator {
        Coordinator(serviceManager: serviceManager)
    }

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.mediaTypesRequiringUserActionForPlayback = []
        
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.allowsBackForwardNavigationGestures = true
        webView.navigationDelegate = context.coordinator.delegate
        
        // 保存 webView 引用
        context.coordinator.delegate.webView = webView
        
        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {
        // 当服务状态变为 running 时加载页面
        if serviceManager.status == .running {
            if let url = URL(string: url) {
                nsView.load(URLRequest(url: url))
            }
        }
    }
    
    class Coordinator {
        let delegate: WebViewDelegate
        
        init(serviceManager: ServiceManager) {
            delegate = WebViewDelegate()
            delegate.serviceManager = serviceManager
        }
    }
}

// ============ 窗口内容 ============
struct DizicalWindowView: View {
    @StateObject private var serviceManager = ServiceManager()
    @State private var isServiceReady = false
    
    var body: some View {
        ZStack {
            // 背景
            Color(NSColor.windowBackgroundColor)
                .ignoresSafeArea()
            
            // 内容
            if isServiceReady {
                DizicalWebView(serviceManager: serviceManager, url: DIZICAL_URL)
                    .ignoresSafeArea()
            } else {
                ServiceStatusView(serviceManager: serviceManager) {
                    // 重试按钮
                    Task {
                        isServiceReady = await serviceManager.restartService()
                    }
                }
            }
        }
        .onAppear {
            // 启动时检查并启动服务
            Task {
                isServiceReady = await serviceManager.ensureServiceRunning()
            }
        }
        .onDisappear {
            // Cmd+W 关窗 ≠ 退出. 服务继续在后台跑 (iPad 仍能访问)
            // 停止服务只在 applicationWillTerminate (Cmd+Q) 时执行
        }
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