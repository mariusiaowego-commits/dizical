# dizical CloudRun spike 部署指南

## 目标

验证: 把 dizical 现有 FastAPI 后端 (Python) 部署到腾讯云托管 (CloudRun), 通过公网 HTTPS 访问 `/health` 端点.

## 准备 (你做, 3 步, 不阻塞我)

### Step 1: 注册小程序 AppID

访问 https://mp.weixin.qq.com → 立即注册 → 选"个人"主体 → 填身份证 + 微信扫码.

**预计时间**: 0.5-1 天 (个人主体当天通过).

**拿到**: 形如 `wx1234567890abcdef` 的 AppID.

### Step 2: 开通 CloudRun (5 分钟)

1. 登录微信公众平台 (用刚注册的 AppID)
2. 左侧菜单 → 云服务 → 云托管 (CloudRun)
3. 点 "开通" → 同意协议 → 开通成功

**拿到**: 一个环境 (env), 形如 `dizical-prod-xxxx`.

### Step 3: 建 MySQL 实例 (Phase 1 用, spike 不用)

spike 阶段先用 SQLite 验证跑通, MySQL 在 Phase 1 再建.

**spike 你只需要做完 Step 1 + Step 2**, 拿到 env_id 给我.

---

## 我做的 (你做完 Step 1+2 后告诉我 env_id)

| 步骤 | 我做的 |
|------|--------|
| 1 | 改 Dockerfile + cloudrun.yaml 适配你的 env_id |
| 2 | 跑 `bash scripts/spike-deploy.sh <env_id>` |
| 3 | 等 ~2 分钟, CloudRun 自动拉镜像 + 启动容器 |
| 4 | curl 验证 `/health` 返回 `{"status":"ok",...}` |
| 5 | 你在小程序开发者工具 / 浏览器 / Mac 浏览器访问, 看到真页面 |

---

## 你需要本地装 (spike 前)

### Docker Desktop (必需)

```bash
brew install --cask docker
# 启动 Docker Desktop, 等图标变绿
docker --version  # 验证
```

### cloudbase CLI (必需)

```bash
npm install -g @cloudbase/cli
cloudbase --version  # 验证
```

### 环境变量 (推荐)

```bash
# 你的 env_id 申请下来后, 加到 ~/.zshrc
export CLOUDRUN_ENV_ID="dizical-prod-xxxx"
export CLOUDRUN_API_KEY="your-cloudbase-api-key"  # 在 cloudbase 控制台创建
```

---

## 跑 spike (你拿到 env_id 后)

```bash
cd /Users/mt16/dev/dizical
bash scripts/spike-deploy.sh "$CLOUDRUN_ENV_ID"
```

跑完会输出:

```
🩺 健康检查:
{
  "status": "ok",
  "service": "dizical",
  "env": "cloudrun",
  "database": "ok",
  "db_error": null,
  "lesson_count": 0,
  "timestamp": "2026-07-16T..."
}

🌐 公网访问:
  https://dizical-prod-xxx-xxxx.gz.apigw.tencentcs.com/release/dizical/health
  https://dizical-prod-xxx-xxxx.gz.apigw.tencentcs.com/release/dizical/api/bless-pool
```

复制这两个 URL 在浏览器打开, 能看到 JSON 响应 = spike 成功.

---

## Spike 通过后的下一步

✅ 通过 → 我开始 Phase 1 (数据库迁移 SQLite → MySQL)
❌ 失败 → 给我错误信息, 我 24 小时内排查

---

## 常见问题 (预答)

### Q: spike 阶段为啥用 SQLite 不直接上 MySQL?

A: spike 只验证 CloudRun 能跑 FastAPI. MySQL 是 Phase 1 才上, spike 阶段没必要把网络/连接池/迁移都验一遍. 一步一步来, 每次只验一件事.

### Q: 数据会不会丢? spike 阶段用 SQLite?

A: 不会, 容器是临时的, 重启后 /tmp 里的 .db 文件清空. 你本地 SQLite 还在原位, 数据安全. Phase 1 改 MySQL 后, 容器重启数据不丢.

### Q: 我能在 CloudRun 控制台看容器日志吗?

A: 能, CloudRun → 服务列表 → dizical-prod → 日志 → 实时查看 uvicorn 输出.

### Q: 部署需要多久?

A: 首次构建 ~3-5 分钟 (装 Python 依赖), 后续增量部署 < 30 秒.

### Q: 免费额度够吗?

A: spike 阶段 (1-2 天) 用的资源 < 1 元, 100% 在免费额度内.

---

## 相关文档

- [architecture.md](../docs/cloudrun-architecture.md) - 完整架构
- [migration-plan.md](../docs/cloudrun-migration-plan.md) - 5 天实施计划
- [functions-catalog.md](../docs/cloudrun-functions-catalog.md) - 67 endpoint 清单