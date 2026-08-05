#!/bin/bash
# dizical 一键回滚: 从云切回本地 SQLite (Sprint 09 增强版)
#
# 完整闭环:
#   1. 备份当前本地 SQLite (回滚前快照, 避免丢回滚前刚加的数据)
#   2. 从备份文件恢复本地 SQLite (数据文件回滚)
#   3. 清除 DATABASE_URL (环境变量 + ~/.zshrc / ~/.dizical/.env 里的配置)
#   4. 重启 kid_app (走本地 SQLite)
#   5. /health/ready 验证 + 数据抽查
#
# 用法:
#   bash scripts/rollback_to_local.sh                 # 用最新手动备份
#   bash scripts/rollback_to_local.sh <backup_file>   # 指定备份
#   bash scripts/rollback_to_local.sh --yes           # 跳过交互确认 (给 dad 5 分钟演练用)
#
# 依赖: sqlite3 (系统自带), start-prod.sh / stop-prod.sh (同目录)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCAL_DB="$PROJECT_ROOT/data/dizi.db"
BACKUP_DIR="$HOME/.dizical/backups/manual"
PORT=8765

AUTO_YES=0
if [[ "${1:-}" == "--yes" ]]; then
  AUTO_YES=1
  shift
fi

# ── 1. 备份源解析 ────────────────────────────────────────────────
BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" ]]; then
  BACKUP_FILE=$(ls -t "$BACKUP_DIR"/dizi-*.db 2>/dev/null | head -1)
fi

if [[ -z "$BACKUP_FILE" ]] || [[ ! -f "$BACKUP_FILE" ]]; then
  echo "❌ 失败: 没找到备份文件"
  echo "   用法: bash $0 [backup_file] 或 bash $0 --yes"
  echo "   自动找最新: ls -t $BACKUP_DIR/dizi-*.db | head -1"
  exit 1
fi

echo "🔥 开始: 回滚到本地 SQLite (Sprint 09 增强闭环)"
echo "   回滚源:   $BACKUP_FILE"
echo "   回滚目标: $LOCAL_DB"
echo

# ── 2. 确认 (除非 --yes) ────────────────────────────────────────
if [[ $AUTO_YES -ne 1 ]]; then
  echo "⚠️  警告: 这会覆盖当前本地 SQLite + 清除 DATABASE_URL 配置!"
  echo "   当前 LOCAL_DB 大小: $(stat -f%z "$LOCAL_DB" 2>/dev/null || echo '?') bytes"
  echo "   备份文件大小:       $(stat -f%z "$BACKUP_FILE" 2>/dev/null || echo '?') bytes"
  echo
  read -p "确认继续? (输入 yes 回滚, 其它键取消) > " CONFIRM
  if [[ "$CONFIRM" != "yes" ]]; then
    echo "❌ 取消"
    exit 1
  fi
fi

# ── 3. 回滚前快照当前本地 SQLite ────────────────────────────────
CURRENT_BACKUP="$BACKUP_DIR/dizical-pre-rollback-$(date +%Y%m%d-%H%M%S).db"
if [[ -f "$LOCAL_DB" ]]; then
  echo "   备份当前本地 SQLite → $CURRENT_BACKUP"
  sqlite3 "$LOCAL_DB" ".backup '$CURRENT_BACKUP'"
fi

# ── 4. 数据文件回滚 ─────────────────────────────────────────────
echo "   复制备份到 LOCAL_DB..."
cp "$BACKUP_FILE" "$LOCAL_DB"

NEW_ROW=$(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'" 2>/dev/null || echo "?")
BACKUP_ROW=$(sqlite3 "$BACKUP_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'" 2>/dev/null || echo "?")
if [[ "$NEW_ROW" != "$BACKUP_ROW" ]]; then
  echo "❌ 失败: 回滚后表数不一致 (备份=$BACKUP_ROW, 现在=$NEW_ROW)"
  exit 1
fi
echo "   ✓ 数据文件回滚完成 ($NEW_ROW 张表)"

# ── 5. 清除 DATABASE_URL (云连接配置) ───────────────────────────
echo "   清除 DATABASE_URL 配置..."
UNSET_COUNT=0

# 5a. 当前 shell 环境
if [[ -n "${DATABASE_URL:-}" ]]; then
  echo "     ✓ 当前 shell 的 DATABASE_URL 已标记清除"
  UNSET_COUNT=$((UNSET_COUNT + 1))
fi
unset DATABASE_URL || true

# 5b. ~/.zshrc (mac 登录 shell)
ZSHRC="$HOME/.zshrc"
if [[ -f "$ZSHRC" ]] && grep -q "DATABASE_URL" "$ZSHRC" 2>/dev/null; then
  cp "$ZSHRC" "$ZSHRC.bak-rollback-$(date +%Y%m%d-%H%M%S)"
  # 注释掉 export DATABASE_URL=... 行 (保留原文, 只加注释前缀)
  sed -i '' -E 's/^(export[[:space:]]+DATABASE_URL=.*)$/# [rollback] \1/' "$ZSHRC"
  echo "     ✓ ~/.zshrc 的 DATABASE_URL export 已注释 (原文件已备份)"
  UNSET_COUNT=$((UNSET_COUNT + 1))
fi

# 5c. ~/.dizical/.env (preflight/备份脚本共用凭据文件)
DIZICAL_ENV="$HOME/.dizical/.env"
if [[ -f "$DIZICAL_ENV" ]] && grep -q "DATABASE_URL\|MYSQL_PASSWORD" "$DIZICAL_ENV" 2>/dev/null; then
  cp "$DIZICAL_ENV" "$DIZICAL_ENV.bak-rollback-$(date +%Y%m%d-%H%M%S)"
  sed -i '' -E 's/^(export[[:space:]]+(DATABASE_URL|MYSQL_HOST|MYSQL_PORT|MYSQL_USER|MYSQL_PASSWORD|MYSQL_DATABASE)=.*)$/# [rollback] \1/' "$DIZICAL_ENV"
  echo "     ✓ ~/.dizical/.env 的云连接配置已注释 (原文件已备份)"
  UNSET_COUNT=$((UNSET_COUNT + 1))
fi

# 5d. 当前进程组里所有 DATABASE_URL (mac 常用 /bin/zsh 重新登录会重新读, 这里做防御)
echo "     (新终端/shell 会用已注释的配置, 不会自动连云)"

# ── 6. 重启 kid_app (走本地 SQLite) ─────────────────────────────
echo "   重启 kid_app..."
bash "$SCRIPT_DIR/stop-prod.sh" force >/dev/null 2>&1 || true
rm -f /tmp/dizical-8765.pid
sleep 1
if ! bash "$SCRIPT_DIR/start-prod.sh" background; then
  echo "❌ 失败: kid_app 启动失败, 看日志 /tmp/dizical-8765.log"
  exit 1
fi

# ── 7. /health/ready 验证 ───────────────────────────────────────
echo "   验证服务健康..."
HEALTH_OK=0
for i in {1..10}; do
  BODY=$(curl -s -m 3 "http://127.0.0.1:${PORT}/health/ready" 2>/dev/null || true)
  if echo "$BODY" | grep -q '"database"\|"ok"\|200'; then
    HEALTH_OK=1
    echo "   ✓ /health/ready: $BODY"
    break
  fi
  sleep 1
done
if [[ $HEALTH_OK -ne 1 ]]; then
  echo "⚠️  /health/ready 未确认 (可能还没就绪), 手工验证: curl http://127.0.0.1:${PORT}/health/ready"
fi

# ── 8. 数据抽查 ─────────────────────────────────────────────────
echo "   数据抽查:"
sqlite3 "$LOCAL_DB" "SELECT '   ✓ practice_sessions: ' || COUNT(*) || ' 条' FROM practice_sessions" 2>/dev/null || echo "   ? practice_sessions 表不可读"
sqlite3 "$LOCAL_DB" "SELECT '   ✓ daily_practices: ' || COUNT(*) || ' 条' FROM daily_practices" 2>/dev/null || echo "   ? daily_practices 表不可读"

echo
echo "✅ 回滚闭环完成"
echo "   - 数据已回滚到: $BACKUP_FILE"
echo "   - 回滚前快照:   $CURRENT_BACKUP"
echo "   - DATABASE_URL 已清除 ($UNSET_COUNT 处)"
echo "   - 服务已重启:   http://localhost:${PORT}"
echo
echo "下一步 (如确认云才是主库后想切回云):"
echo "   1. 恢复配置: 从 ~/.zshrc.bak-rollback-* / ~/.dizical/.env.bak-rollback-* 还原"
echo "   2. 重新 export DATABASE_URL 指向云"
echo "   3. 重启 kid_app"
