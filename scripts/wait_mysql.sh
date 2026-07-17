#!/bin/bash
# Wait for MySQL external address to be ready, then test connection
# 用法: bash scripts/wait_mysql.sh <external-host> [timeout-seconds]

set -e

HOST="${1:?用法: bash scripts/wait_mysql.sh <external-host> [timeout-seconds]}"
TIMEOUT="${2:-300}"  # 默认 5 分钟

echo "⏳ 等待 MySQL 外网地址 $HOST 可连接 (最多 ${TIMEOUT}s)..."
echo

START=$(date +%s)
ATTEMPT=0

while true; do
    ATTEMPT=$((ATTEMPT + 1))
    NOW=$(date +%s)
    ELAPSED=$((NOW - START))

    if [ $ELAPSED -gt $TIMEOUT ]; then
        echo "❌ 超时 ${TIMEOUT}s, MySQL 还没好"
        exit 1
    fi

    # 试连
    if python3 -c "
import os
import pymysql
try:
    conn = pymysql.connect(
        host='$HOST',
        port=3306,
        user='root',
        password=os.environ['MYSQL_PASSWORD'],
        connect_timeout=3,
    )
    cur = conn.cursor()
    cur.execute('SELECT VERSION()')
    print(f'✅ MySQL 连接成功! 版本: {cur.fetchone()[0]}')
    conn.close()
except Exception as e:
    raise SystemExit(1)
" 2>/dev/null; then
        echo
        echo "🎉 外网地址 $HOST 可用了!"
        echo "   耗时: ${ELAPSED}s, 尝试 $ATTEMPT 次"
        exit 0
    fi

    echo "  ⏳ 第 $ATTEMPT 次, 已等 ${ELAPSED}s, 还没好..."
    sleep 10
done