#!/usr/bin/env bash
# intro-stop.sh — uiux-asset-library intro demo 服务停止脚本
#
# 用途: 优雅停 9876 端口 Python http.server, 清理 PIDFILE
# 用法: ./scripts/intro-stop.sh
#
# 配套: intro-start.sh / intro-restart.sh / intro-status.sh

set -euo pipefail

PORT=9876
PIDFILE="/tmp/uiux-intro-9876.pid"

# 1. 优先用 PIDFILE 的 PID (start 写入的进程)
PID=""
if [[ -f "${PIDFILE}" ]]; then
  PID=$(cat "${PIDFILE}" 2>/dev/null || echo "")
fi

# 2. 兜底用 lsof 找端口占用进程 (PIDFILE 可能 stale)
if [[ -z "${PID}" ]] || ! kill -0 "${PID}" 2>/dev/null; then
  if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
    PID=$(lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN -t 2>/dev/null | head -1)
  fi
fi

# 3. 没进程就退出
if [[ -z "${PID}" ]] || ! kill -0 "${PID}" 2>/dev/null; then
  echo "intro demo 服务未运行 (端口 ${PORT} 空闲)"
  rm -f "${PIDFILE}"
  exit 0
fi

# 4. SIGTERM 优雅停
echo "停止 intro demo 服务 (PID ${PID}, 端口 ${PORT})..."
kill -TERM "${PID}" 2>/dev/null || true

# 5. 等 3 秒确认优雅退出
for _ in 1 2 3; do
  sleep 1
  if ! kill -0 "${PID}" 2>/dev/null; then
    echo "  ✅ 已停止"
    rm -f "${PIDFILE}"
    exit 0
  fi
done

# 6. 兜底 SIGKILL (强 kill)
echo "  ⚠️  进程未响应 SIGTERM, 强 kill"
kill -KILL "${PID}" 2>/dev/null || true
sleep 1
rm -f "${PIDFILE}"
echo "  ✅ 已强 kill"
