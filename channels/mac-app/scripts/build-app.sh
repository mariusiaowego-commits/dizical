#!/bin/bash
# DizicalMac build script
# 编译 + 打包成 .app bundle
# 输出: build/DizicalMac.app

set -e

cd "$(dirname "$0")/.."

echo "🔨 Building DizicalMac (release)..."
swift build -c release

# 找编译产物
BIN_PATH=$(swift build -c release --show-bin-path)
APP_NAME="DizicalMac"
APP_DIR="build/${APP_NAME}.app"

echo "📦 Packaging into ${APP_DIR}..."

# 清理旧 bundle
rm -rf "${APP_DIR}"

# 创建标准 .app bundle 结构
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"

# 复制二进制
cp "${BIN_PATH}/${APP_NAME}" "${APP_DIR}/Contents/MacOS/${APP_NAME}"

# Info.plist
cat > "${APP_DIR}/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>DizicalMac</string>
    <key>CFBundleDisplayName</key>
    <string>dizical</string>
    <key>CFBundleExecutable</key>
    <string>DizicalMac</string>
    <key>CFBundleIdentifier</key>
    <string>local.dizical.mac</string>
    <key>CFBundleVersion</key>
    <string>0.3.1</string>
    <key>CFBundleShortVersionString</key>
    <string>0.3.1</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>CFBundleIconFile</key>
    <string>dizical-icon</string>
    <key>CFBundleIconName</key>
    <string>dizical-icon</string>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsLocalNetworking</key>
        <true/>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
</dict>
</plist>
PLIST

# PkgInfo
echo "APPL????" > "${APP_DIR}/Contents/PkgInfo"

# 复制 Resources (强制覆盖, 确保最新)
if [ -d "Sources/DizicalMac/Resources" ]; then
    cp -Rf Sources/DizicalMac/Resources/* "${APP_DIR}/Contents/Resources/" 2>/dev/null || true
fi

# 复制 app icon (dizical-icon.icns) - 强制覆盖旧版
if [ -f "Sources/DizicalMac/Resources/dizical-icon.icns" ]; then
    cp -f "Sources/DizicalMac/Resources/dizical-icon.icns" "${APP_DIR}/Contents/Resources/dizical-icon.icns"
    echo "🎨 App icon installed (forced overwrite)"
fi

# 加可执行权限
chmod +x "${APP_DIR}/Contents/MacOS/${APP_NAME}"

echo ""
echo "✅ Done!"
echo "📍 ${APP_DIR}"
echo ""
echo "Run with:"
echo "  open ${APP_DIR}"
echo ""

# 自动 copy 到 /Applications (让 Spotlight / Launchpad 能找到)
if [ -d "${APP_DIR}" ]; then
    echo "📦 Copying to /Applications..."
    rm -rf "/Applications/${APP_NAME}.app"
    cp -R "${APP_DIR}" "/Applications/${APP_NAME}.app"
    echo "✅ Installed to /Applications/${APP_NAME}.app"
    echo ""
    echo "Launch with:"
    echo "  open /Applications/${APP_NAME}.app"
    echo "  (或 Cmd+Space 搜 'dizical')"
fi
