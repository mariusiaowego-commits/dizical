#!/bin/bash
# dizical 本地 SQLite 强制备份脚本
# Phase 1b 跑任何云操作前必跑, 用户红线保护
# 用法: bash scripts/backup_local_sqlite.sh

set -e

BACKUP_ROOT="$HOME/.dizical/backups/manual"
LOCAL_DB="/Users/mt16/dev/dizical/data/dizi.db"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_ROOT/dizi-$TIMESTAMP.db"

echo "🔥 开始: 本地 SQLite 备份"
echo "   源: $LOCAL_DB"
echo "   目标: $BACKUP_FILE"

# 检查源文件存在
if [ ! -f "$LOCAL_DB" ]; then
    echo "❌ 失败: 本地 SQLite 不存在 - $LOCAL_DB"
    echo "   可能路径错了, 或你还没本地跑过 kid_app"
    exit 1
fi

mkdir -p "$BACKUP_ROOT"

# 用 SQLite .backup 命令 (一致性快照, 不锁表, 比 cp 安全)
echo "   跑 sqlite3 .backup (一致性快照)..."
sqlite3 "$LOCAL_DB" ".backup '$BACKUP_FILE'"

# 验证备份
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ 失败: 备份文件未生成"
    exit 1
fi

# 计算大小 + 行数 + sha256
SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
ROW_COUNT=$(sqlite3 "$BACKUP_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'" 2>/dev/null || echo "?")
HASH=$(shasum -a 256 "$BACKUP_FILE" 2>/dev/null | cut -d' ' -f1 || sha256sum "$BACKUP_FILE" | cut -d' ' -f1)

echo "   备份大小: $SIZE bytes"
echo "   表数: $ROW_COUNT"
echo "   SHA256: $HASH"

# 验证: 表数一致 + 每张表行数一致 (内容等价性)
# 注: sqlite3 .backup 输出格式跟原文件不同 (含 WAL/page), 大小/哈希不同是正常的
SOURCE_ROW=$(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'" 2>/dev/null || echo "?")
SOURCE_SIZE=$(stat -f%z "$LOCAL_DB" 2>/dev/null || stat -c%s "$LOCAL_DB")

if [ "$ROW_COUNT" = "$SOURCE_ROW" ]; then
    # 深验证: 每张表行数完全一致
    MISMATCH=0
    for table in $(sqlite3 "$LOCAL_DB" "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"); do
        L=$(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM \`$table\`" 2>/dev/null || echo "?")
        B=$(sqlite3 "$BACKUP_FILE" "SELECT COUNT(*) FROM \`$table\`" 2>/dev/null || echo "?")
        if [ "$L" != "$B" ]; then
            echo "   ⚠️  表 $table: 源=$L 备份=$B"
            MISMATCH=$((MISMATCH + 1))
        fi
    done

    if [ $MISMATCH -eq 0 ]; then
        echo "✅ 完成: 备份验证通过"
        echo "   备份文件: $BACKUP_FILE"
        echo "   恢复命令: cp $BACKUP_FILE $LOCAL_DB"
    else
        echo "❌ 失败: $MISMATCH 张表行数不一致"
        exit 1
    fi
else
    echo "❌ 失败: 表数不一致"
    echo "   源: $SOURCE_ROW 表"
    echo "   备: $ROW_COUNT 表"
    exit 1
fi

# 写日志 (方便追溯)
LOG_FILE="$BACKUP_ROOT/backup.log"
mkdir -p "$(dirname $LOG_FILE)"
echo "[$(date -Iseconds)] $BACKUP_FILE $SIZE bytes $ROW_COUNT 表 sha256=$HASH" >> "$LOG_FILE"

# 清理 > 30 天的手动备份 (保留 daily/weekly 自动备份)
find "$BACKUP_ROOT" -name "dizical-*.db" -type f -mtime +30 -delete 2>/dev/null || true

echo "   (保留 30 天, 超期自动清理)"