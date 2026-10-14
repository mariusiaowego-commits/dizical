#!/usr/bin/env bash
# start-prod.sh — dizical kid-app 生产服务启动脚本
#
# 用途: 固化启动参数，避免手工拼写遗漏 --host
# 默认绑 0.0.0.0 (iPad/Tailscale 都能访问；绑 127.0.0.1 会导致 iPad 打不开)
#
# Sprint 09 (PR-A, 2026-08-05): 后端默认指云端 (Cloud MySQL 是唯一主库, 见 AGENTS.md 数据红线).
#   - 本脚本仍启动本地 uvicorn (Q10=A: 8765 本地服务保留, kid_app 走云)
#   - 数据源由 DATABASE_URL 环境变量决定: 设了 mysql:// → 连云; 未设 → 本地 SQLite (灾备/回滚)
#   - mac app 的 DIZICAL_URL 切换 UI 在 mac 项目 (不在本仓)
#
# 用法:
#   ./scripts/start-prod.sh              # 后台启动，写入 /tmp/dizical-8765.pid
#   ./scripts/start-prod.sh foreground   # 前台运行（调试用）
#
# 解释器 (P0/R3: 必须是装了 COS SDK 的那个, 选不到就硬失败, 不回落到系统解释器):
#   DIZICAL_VENV         指定 venv 目录 (默认 <repo>/.venv)
#   DIZICAL_UVICORN_BIN  直接指定 uvicorn 可执行 (最高优先级; 例: worktree 里借主仓 .venv)
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

# 2. 选 uvicorn 可执行 —— 必须用**装了 COS SDK 的解释器**起服务, 否则服务进程里 qcloud_cos
#    静默 MISSING ⇒ cos_uploader.is_available=False ⇒ 图静默回落 static/badges/ ⇒ 每张新徽章
#    都要 PR + CloudRun deploy 才可见 (2026-10-13 实测)。历史坑: 这里原本写死
#    /opt/homebrew/bin/uvicorn (shebang → python@3.14), 而 SDK 装在项目 .venv。
#    P0/R3: 非 venv 分支**硬失败**, 不再"WARNING 后拿 homebrew 起服务" —— 那正是要堵的静默回落。
#    覆盖变量 (见脚本头部):
#      DIZICAL_VENV         venv 目录 (默认 ${PROJECT_ROOT}/.venv)
#      DIZICAL_UVICORN_BIN  直接指定 uvicorn 可执行 (最高优先级; worktree 里指主仓 .venv 用)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="${DIZICAL_VENV:-${PROJECT_ROOT}/.venv}"
VENV_UVICORN="${VENV_DIR}/bin/uvicorn"
UVICORN_BIN=""
if [[ -n "${DIZICAL_UVICORN_BIN:-}" ]]; then
  if [[ -x "${DIZICAL_UVICORN_BIN}" ]]; then
    UVICORN_BIN="${DIZICAL_UVICORN_BIN}"   # 显式覆盖 (worktree / 特殊环境)
  else
    echo "ERROR: DIZICAL_UVICORN_BIN 不是可执行文件: ${DIZICAL_UVICORN_BIN}"
    exit 1
  fi
elif [[ -x "${VENV_UVICORN}" ]]; then
  UVICORN_BIN="${VENV_UVICORN}"            # 首选: 项目 venv
else
  echo "ERROR: 找不到可用的 uvicorn —— 拒绝回落系统解释器 (缺 qcloud_cos, 图会静默走 static)."
  echo "  期望路径: ${VENV_UVICORN}    (DIZICAL_VENV 可覆盖 venv 目录)"
  echo "  建 venv: python3 -m venv ${VENV_DIR} && ${VENV_DIR}/bin/pip install -r requirements.txt"
  echo "  已经有 venv 但不是这个目录 (例: worktree 要借主仓的), 显式指:"
  echo "    DIZICAL_UVICORN_BIN=/abs/path/to/.venv/bin/uvicorn ./scripts/start-prod.sh"
  exit 1
fi
echo "==> uvicorn: ${UVICORN_BIN}  (COS 是否可用见启动日志的 [cos-selfcheck] 行)"

# 3. 必须在项目根目录运行（uvicorn src.kid_app.app:app 依赖相对路径）
cd "$(dirname "$0")/.."

# 4. Sprint 26081003 v3.3.2: 启动前自动跑 web_users migrate (保证 dad 账号存在 + 打印初始密码到 log)
PYTHON_BIN=$(command -v python3.12 || command -v python3 || command -v python)
echo "==> 启动前 migrate: web_users + web_invites + dad 账号"
"${PYTHON_BIN}" src/migrate_add_web_users.py 2>&1 | tee -a "${LOGFILE}" || echo "WARNING: migrate 跑失败 (非致命, 继续启动)"

# 5. 数据源: 若 ~/.dizical/.env 存在则 source (含 MYSQL_* 云凭据)
#    - 若 DATABASE_URL 已由外部设置 → 用它 (优先级最高)
#    - 否则若 MYSQL_* 齐全 → 拼 mysql+pymysql:// URL (方案 A: 本地 8765 也连云)
#    - 否则 → 回落本地 SQLite (灾备)
DIZICAL_ENV_FILE="$HOME/.dizical/.env"
if [[ -f "$DIZICAL_ENV_FILE" ]]; then
  set -a; source "$DIZICAL_ENV_FILE"; set +a
fi
if [[ -z "${DATABASE_URL:-}" ]] && [[ -n "${MYSQL_HOST:-}" ]] && [[ -n "${MYSQL_PORT:-}" ]] && [[ -n "${MYSQL_USER:-}" ]] && [[ -n "${MYSQL_PASSWORD:-}" ]] && [[ -n "${MYSQL_DATABASE:-}" ]]; then
  export DATABASE_URL="mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}"
  echo "数据源: 云端 MySQL (DATABASE_URL 自动拼装)"
elif [[ -n "${DATABASE_URL:-}" ]]; then
  echo "数据源: 云端 MySQL (外部 DATABASE_URL)"
else
  echo "数据源: 本地 SQLite (无 DATABASE_URL/MYSQL_*, 灾备模式)"
fi

# 6. 启动
CMD=("${UVICORN_BIN}" src.kid_app.app:app --host "${HOST}" --port "${PORT}" --log-level warning)

case "${MODE}" in
  foreground)
    echo "启动 dizical kid-app (前台模式, host=${HOST}, port=${PORT})"
    echo "按 Ctrl+C 停止"
    exec "${CMD[@]}"
    ;;
  background|"")
    echo "启动 dizical kid-app (后台模式, host=${HOST}, port=${PORT})"
    nohup "${CMD[@]}" >>"${LOGFILE}" 2>&1 &
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
