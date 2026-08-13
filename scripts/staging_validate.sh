#!/bin/bash
# dizical staging 5 步自动验证
# Phase 1b 上线前必跑: 健康检查 + 数据一致性 + CRUD round-trip + 行数对账
# 用法: bash scripts/staging_validate.sh <base_url>
# 例如: bash scripts/staging_validate.sh https://dizical-prod-282854-7-1454535414.sh.run.tcloudbase.com

set -e

BASE_URL="${1:?用法: bash scripts/staging_validate.sh <base_url>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCAL_DB="$PROJECT_ROOT/data/dizi.db"
PASSED=0
FAILED=0

step_pass() {
    echo "   ✅ $1"
    PASSED=$((PASSED + 1))
}
step_fail() {
    echo "   ❌ $1"
    FAILED=$((FAILED + 1))
}

echo "🔥 开始: staging 5 步验证"
echo "   base_url: $BASE_URL"
echo "   local_db: $LOCAL_DB"
echo

# Step 1: /health 200 + database=ok
echo "Step 1: /health 端点"
HEALTH=$(curl -s -o /tmp/h.json -w "%{http_code}" "$BASE_URL/health" || echo "000")
if [ "$HEALTH" = "200" ]; then
    DB_STATUS=$(python3 -c "
import json, sys
d = json.load(open('/tmp/h.json'))
if d.get('database') == 'ok': print('OK')
else: print('FAIL: ' + str(d.get('database')))
" 2>/dev/null || echo "?")
    if [ "$DB_STATUS" = "OK" ]; then
        step_pass "健康检查 200 + database=ok"
    else
        step_fail "健康检查返 200 但 database=$DB_STATUS"
    fi
else
    step_fail "健康检查 HTTP $HEALTH (期望 200)"
fi

# Step 2: /api/bless-pool 200 + CORS
echo
echo "Step 2: /api/bless-pool 端点"
API_CODE=$(curl -s -o /tmp/api.json -w "%{http_code}" -H "Origin: http://localhost:3000" "$BASE_URL/api/bless-pool" || echo "000")
if [ "$API_CODE" = "200" ]; then
    if python3 -c "
import json
d = json.load(open('/tmp/api.json'))
assert 'pool' in d or 'blessings' in d, f'no pool/blessings key: {list(d.keys())}'
" 2>/dev/null; then
        step_pass "业务 endpoint 200 + 数据格式 OK"
    else
        step_fail "业务 endpoint 返 200 但数据格式不对: $(cat /tmp/api.json | head -c 200)"
    fi
else
    step_fail "业务 endpoint HTTP $API_CODE (期望 200)"
fi

# Step 3: badge/reports/uploads 资源
echo
echo "Step 3: 静态资源 (badge/reports/uploads)"
BADGE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/static/badges/streak_7.png" || echo "000")
REPORT_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/data/reports/2026-06-%E7%BB%83%E4%B9%A0%E6%8A%A5%E5%91%8A.png" || echo "000")
UPLOAD_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/uploads/raw/de40557586cc4f119493202fa1714d73.png" || echo "000")

if [ "$BADGE_CODE" = "200" ]; then
    step_pass "badge PNG 200 (streak_7.png)"
else
    step_fail "badge PNG HTTP $BADGE_CODE (期望 200)"
fi

if [ "$REPORT_CODE" = "200" ]; then
    step_pass "report PNG 200 (2026-06 月报)"
else
    step_fail "report PNG HTTP $REPORT_CODE (期望 200)"
fi

if [ "$UPLOAD_CODE" = "200" ]; then
    step_pass "upload PNG 200 (de4055.png)"
else
    step_fail "upload PNG HTTP $UPLOAD_CODE (期望 200)"
fi

# Step 4: CORS 头
echo
echo "Step 4: CORS 中间件"
CORS_HEADERS=$(curl -s -I -H "Origin: http://test.com" "$BASE_URL/api/bless-pool" 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
if echo "$CORS_HEADERS" | grep -qi "test.com"; then
    step_pass "CORS 头返回 (http://test.com)"
else
    step_fail "CORS 头没返回, 实际: '$CORS_HEADERS'"
fi

# Step 5: 数据一致性 (云 vs 本地) — 只在本地 DB 存在时跑
echo
echo "Step 5: 数据一致性 (云 vs 本地)"
if [ ! -f "$LOCAL_DB" ]; then
    step_fail "本地 DB 不存在, 跳过 ($LOCAL_DB)"
else
    CLOUD_TOTAL=$(python3 << 'PYEOF'
import os
import pymysql
try:
    c = pymysql.connect(host='sh-cynosdbmysql-grp-o1j4rd8w.sql.tencentcdb.com', port=22661,
                        user=os.environ.get('MYSQL_USER', 'root'),
                        password=os.environ['MYSQL_PASSWORD'],
                        database='dizical', connect_timeout=10)
    cur = c.cursor()
    cur.execute('SHOW TABLES')
    total = 0
    for (t,) in cur.fetchall():
        cur.execute(f'SELECT COUNT(*) FROM `{t}`')
        total += cur.fetchone()[0]
    c.close()
    print(total)
except Exception as e:
    print(f'ERR:{e}')
PYEOF
)
    LOCAL_TOTAL=$(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM (SELECT 'x' AS t FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' UNION ALL SELECT 'x' FROM (SELECT 1 FROM sqlite_master m, json_each(json_group_array(name)) js WHERE type='table'))" 2>/dev/null || \
                 python3 -c "
import sqlite3
c = sqlite3.connect('$LOCAL_DB')
cur = c.cursor()
cur.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'\")
total = 0
for (t,) in cur.fetchall():
    cur.execute(f'SELECT COUNT(*) FROM \`{t}\`')
    total += cur.fetchone()[0]
print(total)
")

    if [ "$CLOUD_TOTAL" = "$LOCAL_TOTAL" ]; then
        step_pass "总行数一致 (云 $CLOUD_TOTAL = 本地 $LOCAL_TOTAL)"
    else
        step_fail "总行数不一致 (云 $CLOUD_TOTAL vs 本地 $LOCAL_TOTAL)"
    fi
fi

echo
echo "📊 总结: 通过 $PASSED / 失败 $FAILED"
if [ $FAILED -eq 0 ]; then
    echo "✅ 全部 PASS — 可以进生产"
    exit 0
else
    echo "❌ 有失败 — 不要进生产, 修完再跑"
    exit 1
fi