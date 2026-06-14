#!/usr/bin/env bash
# intro-start.sh — uiux-asset-library intro demo 服务启动脚本
#
# 用途: 启动 Python http.server 服务 9876 端口, 服务 dizical/demos/dizicute-intro/intro.html
# 默认绑 0.0.0.0 (跟 dizical 8765 主服务一致)
#
# 用法:
#   ./scripts/intro-start.sh              # 后台启动
#   ./scripts/intro-start.sh foreground   # 前台运行（调试用）
#
# 配套: intro-stop.sh / intro-restart.sh / intro-status.sh
#
# 铁律:
#   - 端口占用检测 (跟 start-prod.sh 同风格)
#   - PIDFILE 写入 /tmp/uiux-intro-9876.pid (内容是 epoch timestamp, 给 status.sh 算 uptime)
#   - 2s 存活检查 (启动失败回滚)
#   - 绝对路径 Python (macOS GUI app PATH 不含 Homebrew, AGENTS.md §启动坑点)
#   - 必须在 uiux-asset-library 仓根运行 (相对路径 ../visual-assets/...)

set -euo pipefail

PORT=9876
HOST=0.0.0.0
PIDFILE="/tmp/uiux-intro-9876.pid"
LOGFILE="/tmp/uiux-intro-9876.log"
MODE="${1:-background}"

# 1. 检查端口是否已被占用
if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: 端口 ${PORT} 已被占用"
  lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN
  echo ""
  echo "如果确认是残留/旧进程，先跑: ./scripts/intro-stop.sh"
  exit 1
fi

# 2. 检查 Python 可执行（macOS GUI 环境下 PATH 不含 Homebrew）
PYTHON_BIN="/usr/local/bin/python3"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    echo "ERROR: 找不到 python3 可执行文件"
    echo "  期望路径: ${PYTHON_BIN}"
    exit 1
  fi
fi

# 3. 必须在 uiux-asset-library 仓根运行（intro.html 用相对路径 ../../visual-assets/）
UIUX_ROOT="/Users/mt16/dev/uiux-asset-library"
if [[ ! -d "${UIUX_ROOT}" ]]; then
  echo "ERROR: 找不到 uiux-asset-library 仓: ${UIUX_ROOT}"
  exit 1
fi

# 4. 启动
CMD=("${PYTHON_BIN}" -m http.server --bind "${HOST}" "${PORT}")

case "${MODE}" in
  foreground)
    echo "启动 intro demo (前台模式, host=${HOST}, port=${PORT})"
    echo "按 Ctrl+C 停止"
    cd "${UIUX_ROOT}"
    exec "${CMD[@]}"
    ;;
  background|"")
    cd "${UIUX_ROOT}"
    nohup "${CMD[@]}" >"${LOGFILE}" 2>&1 &
    PID=$!
    # PIDFILE 写 epoch 时间戳 (status.sh 用来算 uptime)
    date +%s >"${PIDFILE}"
    # 等 2 秒确认进程没立刻挂
    sleep 2
    if ! kill -0 "${PID}" 2>/dev/null; then
      echo "ERROR: 进程 ${PID} 启动后立刻退出，查看日志:"
      cat "${LOGFILE}"
      rm -f "${PIDFILE}"
      exit 1
    fi
    echo "  PID:     ${PID}"
    echo "  PIDFILE: ${PIDFILE} (内容是 epoch 时间戳)"
    echo "  LOGFILE: ${LOGFILE}"
    echo "  本机:    http://localhost:${PORT}/demos/dizicute-intro/intro.html"
    echo "  局域网:  http://10.0.0.43:${PORT}/demos/dizicute-intro/intro.html  (或本机实际 IP)"
    echo ""
    echo "停止: ./scripts/intro-stop.sh"
    echo "状态: ./scripts/intro-status.sh"
    ;;
  *)
    echo "ERROR: 未知模式 '${MODE}'，支持: foreground | background"
    exit 2
    ;;
esac
