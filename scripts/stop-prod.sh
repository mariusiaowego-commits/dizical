#!/usr/bin/env bash
# stop-prod.sh — dizical kid-app 生产服务停止脚本
#
# 用法:
#   ./scripts/stop-prod.sh              # 优雅停服（TERM, 给 5 秒）
#   ./scripts/stop-prod.sh force        # 强杀（KILL）

set -euo pipefail

PORT=8765
PIDFILE="/tmp/dizical-8765.pid"
MODE="${1:-graceful}"

# 1. 优先用 PIDFILE
PID=""
if [[ -f "${PIDFILE}" ]]; then
  PID="$(cat "${PIDFILE}")"
fi

# 2. fallback: 用 lsof 找占用端口的进程
if [[ -z "${PID}" ]] || ! kill -0 "${PID}" 2>/dev/null; then
  PID="$(lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN -t 2>/dev/null || true)"
fi

if [[ -z "${PID}" ]]; then
  echo "端口 ${PORT} 没有 dizical kid-app 进程在跑（无需停止）"
  rm -f "${PIDFILE}"
  exit 0
fi

echo "停止 dizical kid-app (PID ${PID}, mode=${MODE})"
case "${MODE}" in
  graceful|"")
    kill -TERM "${PID}" 2>/dev/null || true
    # 等最多 5 秒
    for i in {1..10}; do
      if ! kill -0 "${PID}" 2>/dev/null; then
        echo "  ✓ 进程已停止"
        rm -f "${PIDFILE}"
        exit 0
      fi
      sleep 0.5
    done
    echo "  ⚠ 进程未响应 TERM，5 秒超时"
    echo "  强杀: ./scripts/stop-prod.sh force"
    exit 1
    ;;
  force)
    kill -KILL "${PID}" 2>/dev/null || true
    sleep 0.5
    if kill -0 "${PID}" 2>/dev/null; then
      echo "  ✗ KILL 后进程仍在，PID 漂移?"
      exit 1
    fi
    echo "  ✓ 强杀完成"
    rm -f "${PIDFILE}"
    exit 0
    ;;
  *)
    echo "ERROR: 未知模式 '${MODE}'，支持: graceful | force"
    exit 2
    ;;
esac
