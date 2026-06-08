#!/usr/bin/env bash
# start-prod.sh — dizical kid-app 生产服务启动脚本
#
# 用途: 固化启动参数，避免手工拼写遗漏 --host
# 默认绑 0.0.0.0 (iPad/Tailscale 都能访问；绑 127.0.0.1 会导致 iPad 打不开)
#
# 用法:
#   ./scripts/start-prod.sh              # 后台启动，写入 /tmp/dizical-8765.pid
#   ./scripts/start-prod.sh foreground   # 前台运行（调试用）
#
# 配套: stop-prod.sh

set -euo pipefail

PORT=8765
HOST=0.0.0.0
PIDFILE="/tmp/dizical-8765.pid"
LOGFILE="/tmp/dizical-8765.log"
MODE="${1:-background}"

# 1. 检查端口是否已被占用
if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: 端口 ${PORT} 已被占用"
  lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN
  echo ""
  echo "如果确认是残留/旧进程，先跑: ./scripts/stop-prod.sh"
  exit 1
fi

# 2. 检查 uvicorn 可执行（macOS GUI 环境下 PATH 不含 Homebrew）
UVICORN_BIN="/opt/homebrew/bin/uvicorn"
if [[ ! -x "${UVICORN_BIN}" ]]; then
  # fallback: 从 PATH 找
  if command -v uvicorn >/dev/null 2>&1; then
    UVICORN_BIN="$(command -v uvicorn)"
  else
    echo "ERROR: 找不到 uvicorn 可执行文件"
    echo "  期望路径: ${UVICORN_BIN}"
    echo "  解决: brew install uvicorn 或 python3 -m pip install uvicorn"
    exit 1
  fi
fi

# 3. 必须在项目根目录运行（uvicorn src.kid_app.app:app 依赖相对路径）
cd "$(dirname "$0")/.."

# 4. 启动
CMD=("${UVICORN_BIN}" src.kid_app.app:app --host "${HOST}" --port "${PORT}" --log-level warning)

case "${MODE}" in
  foreground)
    echo "启动 dizical kid-app (前台模式, host=${HOST}, port=${PORT})"
    echo "按 Ctrl+C 停止"
    exec "${CMD[@]}"
    ;;
  background|"")
    echo "启动 dizical kid-app (后台模式, host=${HOST}, port=${PORT})"
    nohup "${CMD[@]}" >"${LOGFILE}" 2>&1 &
    PID=$!
    echo "${PID}" >"${PIDFILE}"
    # 等 2 秒确认进程没立刻挂
    sleep 2
    if ! kill -0 "${PID}" 2>/dev/null; then
      echo "ERROR: 进程 ${PID} 启动后立刻退出，查看日志:"
      cat "${LOGFILE}"
      rm -f "${PIDFILE}"
      exit 1
    fi
    echo "  PID:     ${PID}"
    echo "  PIDFILE: ${PIDFILE}"
    echo "  LOGFILE: ${LOGFILE}"
    echo "  本机:    http://localhost:${PORT}"
    echo "  局域网:  http://10.0.0.14:${PORT}  (或本机实际 IP, ifconfig 查 inet)"
    echo "  Tailscale: http://100.67.215.121:${PORT}  (或本机 tailscale IP, tailscale ip -4 查)"
    echo ""
    echo "停止: ./scripts/stop-prod.sh"
    ;;
  *)
    echo "ERROR: 未知模式 '${MODE}'，支持: foreground | background"
    exit 2
    ;;
esac
