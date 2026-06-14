#!/usr/bin/env bash
# intro-status.sh — uiux-asset-library intro demo 服务状态检测
#
# 用途: 检测 9876 端口 Python http.server 是否在跑, 返 PID + 启动时间
# 用法: ./scripts/intro-status.sh
# 返回: JSON 一行 {running, pid, port, started_at, uptime_seconds}
#       running=true 时 pid/started_at/uptime_seconds 有值
#
# 配套: intro-start.sh / intro-stop.sh / intro-restart.sh

set -euo pipefail

PORT=9876
PIDFILE="/tmp/uiux-intro-9876.pid"

# 检测端口占用 (lsof 返进程列表, 取第一个 PID)
PID=""
if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  # 提取 PID (lsof 第二列 COMMAND PID USER..., 取 PID 列)
  PID=$(lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN -t 2>/dev/null | head -1)
fi

if [[ -z "${PID}" ]]; then
  # 端口空闲, 清理可能残留的 PIDFILE
  rm -f "${PIDFILE}"
  echo '{"running":false,"pid":null,"port":9876,"started_at":null,"uptime_seconds":null}'
  exit 0
fi

# 端口占用, 验证 PID 还在 (防 zombie)
if ! kill -0 "${PID}" 2>/dev/null; then
  rm -f "${PIDFILE}"
  echo '{"running":false,"pid":null,"port":9876,"started_at":null,"uptime_seconds":null,"stale":true}'
  exit 0
fi

# 读 PIDFILE 启动时间戳 (start 脚本写入时附 epoch)
STARTED_AT=""
if [[ -f "${PIDFILE}" ]]; then
  STARTED_AT=$(cat "${PIDFILE}" 2>/dev/null || echo "")
fi

# 计算 uptime (秒)
UPTIME=""
if [[ -n "${STARTED_AT}" && "${STARTED_AT}" =~ ^[0-9]+$ ]]; then
  NOW=$(date +%s)
  UPTIME=$((NOW - STARTED_AT))
fi

# 返 JSON (用 jq 如果有, 否则手工)
if command -v jq >/dev/null 2>&1; then
  jq -n \
    --argjson running true \
    --argjson pid "${PID}" \
    --argjson port "${PORT}" \
    --arg started_at "${STARTED_AT}" \
    --argjson uptime_seconds "${UPTIME:-null}" \
    '{running:$running,pid:$pid,port:$port,started_at:$started_at,uptime_seconds:$uptime_seconds}'
else
  echo "{\"running\":true,\"pid\":${PID},\"port\":${PORT},\"started_at\":\"${STARTED_AT}\",\"uptime_seconds\":${UPTIME:-null}}"
fi
