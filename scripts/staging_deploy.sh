#!/bin/bash
# dizical 一键部署到 CloudRun staging 环境
# Phase 1b 上线流程:
#   1. commit + push
#   2. CloudRun 自动 build 触发
#   3. staging_validate.sh 5 步验证
#
# 用法:
#   bash scripts/staging_deploy.sh <cloudrun_default_domain>
#   例如: bash scripts/staging_deploy.sh https://dizical-prod-282854-7-1454535414.sh.run.tcloudbase.com

set -e

CLOUD_URL="${1:?用法: bash scripts/staging_deploy.sh <cloudrun_default_domain>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCAL_DB="$PROJECT_ROOT/data/dizi.db"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "🔥 开始: 部署到 CloudRun staging"
echo "   cloud_url: $CLOUD_URL"
echo "   local_db: $LOCAL_DB"
echo "   branch: $CURRENT_BRANCH"
echo

# Step 1: 强制本地 SQLite 备份
echo "Step 1: 强制本地 SQLite 备份 (防御)"
bash "$(dirname $0)/backup_local_sqlite.sh"
echo

# Step 2: 检查工作树干净 (没未提交改动)
echo "Step 2: 检查 git 工作树"
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ 失败: 有未提交改动"
    git status --short
    echo ""
    echo "先 commit 或 stash, 再跑 staging_deploy.sh"
    exit 1
fi
echo "   ✅ 工作树干净"
echo

# Step 3: push 到远端
echo "Step 3: git push (触发 CloudRun build)"
git push origin "$CURRENT_BRANCH"
echo "   ✅ push 完成, CloudRun 正在 build..."
echo

# Step 4: 等 CloudRun 部署完成 (探测 /health)
echo "Step 4: 等 CloudRun 部署完成 (探测 /health)"
MAX_WAIT=180  # 3 分钟
WAITED=0
SLEEP=10
while [ $WAITED -lt $MAX_WAIT ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$CLOUD_URL/health" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   ✅ /health 200 (等了 ${WAITED}s)"
        break
    fi
    echo "   ⏳ 第 $((WAITED/SLEEP + 1)) 次探, 已等 ${WAITED}s, HTTP=$HTTP_CODE"
    sleep $SLEEP
    WAITED=$((WAITED + SLEEP))
done

if [ "$HTTP_CODE" != "200" ]; then
    echo "   ❌ 失败: /health 等 $MAX_WAIT 秒还没 200"
    echo "   检查 CloudRun 控制台 → 运行日志"
    exit 1
fi
echo

# Step 5: 跑 staging 验证
echo "Step 5: staging 5 步验证"
bash "$(dirname $0)/staging_validate.sh" "$CLOUD_URL"
VERIFY_EXIT=$?

echo
if [ $VERIFY_EXIT -eq 0 ]; then
    echo "🎉 staging_deploy 全部通过"
    echo ""
    echo "下一步:"
    echo "  - 让你女儿在 iPad / 小程序测试录入"
    echo "  - 你 mac web 验证能看到 (kid_app 容器连云, 浏览器访问容器默认域名)"
    echo "  - 24 小时后跑: bash scripts/staging_validate.sh $CLOUD_URL (定期抽检)"
    echo "  - 翻车回滚: bash scripts/rollback_to_local.sh"
    exit 0
else
    echo "❌ staging 验证有失败, 不要进生产"
    exit 1
fi
