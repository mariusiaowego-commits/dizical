#!/bin/bash
# dizical CloudRun spike smoke test
# 用法: bash scripts/spike_smoke_test.sh <default-domain>
# 例如: bash scripts/spike_smoke_test.sh dizical-prod-282854-7-1454535414.sh.run.tcloudbase.com

set -e

DOMAIN="${1:?用法: bash scripts/spike_smoke_test.sh <default-domain> (去掉 https://)}"
URL="https://${DOMAIN}"

echo "🩺 dizical CloudRun spike smoke test"
echo "   URL: ${URL}"
echo

# 1. /health 200
echo "1. /health (期望 200):"
HTTP_CODE=$(curl -s -o /tmp/health.json -w "%{http_code}" "${URL}/health")
if [ "$HTTP_CODE" != "200" ]; then
    echo "   ❌ HTTP $HTTP_CODE"
    cat /tmp/health.json
    exit 1
fi
echo "   ✅ HTTP 200"
echo

# 5. database=ok (用 python 验, 避免 BSD grep 的中文/特殊字符 bug)
echo "5. /health database 字段 (期望 ok):"
if ! python3 -c "
import json, sys
data = json.load(open('/tmp/health.json'))
assert data['database'] == 'ok', f\"database={data['database']}\"
assert data['status'] == 'ok', f\"status={data['status']}\"
"; then
    echo "   ❌ database 不是 ok"
    cat /tmp/health.json
    exit 1
fi
echo "   ✅ database=ok (status=ok, database=ok)"
echo

# 2. /docs 200 (FastAPI swagger)
echo "2. /docs (期望 200, FastAPI swagger):"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${URL}/docs")
if [ "$HTTP_CODE" != "200" ]; then
    echo "   ❌ HTTP $HTTP_CODE"
    exit 1
fi
echo "   ✅ HTTP 200"
echo

# 3. /openapi.json 含 /health
echo "3. /openapi.json (期望含 /health):"
HTTP_CODE=$(curl -s -o /tmp/openapi.json -w "%{http_code}" "${URL}/openapi.json")
if [ "$HTTP_CODE" != "200" ]; then
    echo "   ❌ HTTP $HTTP_CODE"
    exit 1
fi
if ! python3 -c "
import json
data = json.load(open('/tmp/openapi.json'))
assert '/health' in data['paths'], 'no /health in paths'
"; then
    echo "   ❌ /health 不在 openapi.json"
    exit 1
fi
echo "   ✅ /openapi.json 含 /health"
echo

# 4. /api/bless-pool (业务 endpoint, CORS 测试)
echo "4. /api/bless-pool (期望 200, CORS 头):"
HTTP_CODE=$(curl -s -o /tmp/bless.json -w "%{http_code}" -H "Origin: http://localhost:3000" "${URL}/api/bless-pool")
if [ "$HTTP_CODE" != "200" ]; then
    echo "   ❌ HTTP $HTTP_CODE"
    cat /tmp/bless.json
    exit 1
fi
if ! curl -s -I -H "Origin: http://localhost:3000" "${URL}/api/bless-pool" 2>/dev/null | grep -qi "access-control-allow-origin"; then
    echo "   ❌ CORS 头缺失"
    exit 1
fi
echo "   ✅ HTTP 200 + CORS OK"
echo

echo "🎉 所有 smoke test PASS — spike 验证 CloudRun 跑通!"
echo
echo "下一步: 走 Phase 1 (SQLite → MySQL 真实迁移)"