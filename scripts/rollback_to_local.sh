#!/bin/bash
# dizical 一键回滚: 从云切回本地 SQLite
# Phase 1b 翻车应急: 1 行回滚到本地 SQLite
# 用法: bash scripts/rollback_to_local.sh [backup_file]

set -e

LOCAL_DB="/Users/mt16/dev/dizical/data/dizi.db"
BACKUP_DIR="$HOME/.dizical/backups/manual"
DEFAULT_BACKUP=$(ls -t "$BACKUP_DIR"/dizi-*.db 2>/dev/null | head -1)

# 参数: 指定备份文件, 或用最新手动备份
if [ -n "$1" ]; then
    BACKUP_FILE="$1"
else
    BACKUP_FILE="$DEFAULT_BACKUP"
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ 失败: 没找到备份文件"
    echo "   用法: bash $0 [backup_file]"
    echo "   自动找最新: ls -t $BACKUP_DIR/dizical-*.db"
    exit 1
fi

echo "🔥 开始: 回滚到本地 SQLite"
echo "   回滚源: $BACKUP_FILE"
echo "   回滚目标: $LOCAL_DB"
echo
echo "⚠️  警告: 这会覆盖你当前本地 SQLite!"
echo "   当前 LOCAL_DB 大小: $(stat -f%z "$LOCAL_DB" 2>/dev/null || echo "?") bytes"
echo "   备份文件大小: $(stat -f%z "$BACKUP_FILE" 2>/dev/null || echo "?") bytes"
echo
echo "确认继续? (输入 yes 回滚, 其它键取消)"
read -p "> " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ 取消 (输入非 yes)"
    exit 1
fi

# 回滚前先备份当前 LOCAL_DB (避免回滚后丢刚加的数据)
CURRENT_BACKUP="$BACKUP_DIR/dizical-pre-rollback-$(date +%Y%m%d-%H%M%S).db"
if [ -f "$LOCAL_DB" ]; then
    echo "   备份当前本地 SQLite → $CURRENT_BACKUP"
    sqlite3 "$LOCAL_DB" ".backup '$CURRENT_BACKUP'"
fi

# 执行回滚
echo "   复制备份到 LOCAL_DB..."
cp "$BACKUP_FILE" "$LOCAL_DB"

# 验证回滚
NEW_ROW=$(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'" 2>/dev/null || echo "?")
BACKUP_ROW=$(sqlite3 "$BACKUP_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'" 2>/dev/null || echo "?")

if [ "$NEW_ROW" = "$BACKUP_ROW" ]; then
    echo "✅ 完成: 回滚成功"
    echo "   LOCAL_DB: $NEW_ROW 表"
    echo "   备份文件: $BACKUP_FILE"
    echo ""
    echo "下一步:"
    echo "   1. mac 本地启动 kid_app: cd /Users/mt16/dev/dizical && python -m src.kid_app"
    echo "   2. 浏览器访问 http://localhost:8765"
    echo "   3. 验证数据回滚正常"
else
    echo "❌ 失败: 回滚后表数不一致"
    echo "   备份: $BACKUP_ROW 表"
    echo "   现在: $NEW_ROW 表"
    exit 1
fi