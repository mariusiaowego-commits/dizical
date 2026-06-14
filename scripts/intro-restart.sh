#!/usr/bin/env bash
# intro-restart.sh — uiux-asset-library intro demo 服务重启脚本
#
# 用途: stop + start 组合
# 用法: ./scripts/intro-restart.sh
#
# 配套: intro-start.sh / intro-stop.sh / intro-status.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== stop ==="
"${SCRIPT_DIR}/intro-stop.sh" || true

sleep 1

echo ""
echo "=== start ==="
"${SCRIPT_DIR}/intro-start.sh"
