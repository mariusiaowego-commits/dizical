#!/bin/bash
# dizical CloudRun spike 一键部署脚本
# 用法: bash spike-deploy.sh <env_id>
# 例如: bash spike-deploy.sh dizical-prod-xxxx

set -e

ENV_ID="${1:?用法: bash spike-deploy.sh <env_id> (在 CloudRun 控制台复制)}"
SERVICE_NAME="dizical-prod"
REGION="ap-shanghai"
IMAGE_NAME="dizical-prod-spike"
IMAGE_TAG="${IMAGE_NAME}:$(date +%Y%m%d-%H%M%S)"

echo "🚀 dizical CloudRun spike 部署"
echo "  ENV_ID:     $ENV_ID"
echo "  SERVICE:    $SERVICE_NAME"
echo "  REGION:     $REGION"
echo "  IMAGE:      $IMAGE_TAG"
echo

# Step 1: 检查 cloudbase CLI
if ! command -v cloudbase &> /dev/null; then
    echo "❌ cloudbase CLI 没装, 跑: npm install -g @cloudbase/cli"
    exit 1
fi

# Step 2: 登录 (已登录会跳过)
echo "🔑 登录 CloudBase..."
cloudbase login --api-key "$CLOUDRUN_API_KEY" 2>/dev/null || {
    echo "  → 走交互登录"
    cloudbase login
}

# Step 3: 构建 Docker 镜像
echo "🐳 构建 Docker 镜像..."
cd "$(dirname "$0")/.."
docker build -t "$IMAGE_TAG" -t "${IMAGE_NAME}:latest" .

# Step 4: 给镜像打 tag (CloudRun 仓库)
echo "🏷  标记镜像..."
CLOUDRUN_REGISTRY="registry.cloudrun.com/${ENV_ID}"
docker tag "$IMAGE_TAG" "${CLOUDRUN_REGISTRY}/${IMAGE_TAG}"
docker tag "$IMAGE_TAG" "${CLOUDRUN_REGISTRY}/${IMAGE_NAME}:latest"

# Step 5: push 到 CloudRun 仓库
echo "⬆️  push 镜像到 CloudRun..."
docker push "${CLOUDRUN_REGISTRY}/${IMAGE_TAG}"
docker push "${CLOUDRUN_REGISTRY}/${IMAGE_NAME}:latest"

# Step 6: 部署到 CloudRun
echo "🚢 部署到 CloudRun..."
cloudbase run deploy "$SERVICE_NAME" \
    --image "${CLOUDRUN_REGISTRY}/${IMAGE_NAME}:latest" \
    --region "$REGION" \
    --cpu 1 \
    --memory 2 \
    --min-instances 0 \
    --max-instances 3 \
    --env "ENV=cloudrun" \
    --env "DATABASE_URL=sqlite:////tmp/dizical.db" \
    --env "JWT_SECRET=spike-temp-secret-change-in-phase-1" \
    --port 80

# Step 7: 等服务起来
echo "⏳ 等服务起来 (30s)..."
sleep 30

# Step 8: 拿默认域名
DOMAIN=$(cloudbase run service-info "$SERVICE_NAME" --region "$REGION" 2>/dev/null | grep -E "default_domain" | awk '{print $2}' | tr -d ',' | tr -d '"')
if [ -z "$DOMAIN" ]; then
    echo "⚠️  拿不到默认域名, 请到 CloudRun 控制台查看"
    echo "    https://console.cloud.tencent.com/tcb/cloudrun"
    exit 0
fi

echo
echo "✅ 部署完成!"
echo
echo "🩺 健康检查:"
curl -s "https://${DOMAIN}/health" | head -50
echo
echo
echo "🌐 公网访问:"
echo "  https://${DOMAIN}/health"
echo "  https://${DOMAIN}/api/bless-pool"