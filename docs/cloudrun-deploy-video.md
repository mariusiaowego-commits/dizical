---
title: CloudRun 部署清单 — 老师要求示范视频 (S4)
tags: [dizical, sprint-26083001, cloudrun, deploy, sop, video]
source: ai-agent
updated: 2026-08-30
---

# CloudRun 部署清单 — 老师要求示范视频 (Sprint 26083001 S4)

> 配套 skill: `hermes: dizical-cloudrun-deploy` (5 步 SOP 全流程) + `tencent-cloudrun-pattern` (PITFALL 大全)
> 本文件只列**视频部署相关**的增量检查, 通用 5 步 SOP 见 skill。

## Step 0 — 前置: CloudRun 配置校对 (视频需求)

| 检查项 | 现状 (`Dockerfile` / `cloudrun.yaml` / `~/.dizical/.env`) | 视频需求 | 结论 |
|--------|------|---------|------|
| 请求超时 | CloudRun 默认 15 min; 容器 uvicorn 无超时 | 200MB/4G ≈ 1-2 min | ✅ 默认够, 无需改 |
| **body size 限制** | **CloudRun / 网关层默认约 32MB** (未在项目内实测, 需控制台确认) | 视频最大 200MB | ⚠️ **必确认/调** (见下) |
| COS 环境变量 | `COS_BUCKET` `COS_REGION` `COS_SECRET_ID` `COS_SECRET_KEY` 已在 `~/.dizical/.env`, is_available=True | 无需新增 | ✅ 就绪 |

### ⚠️ body size 限制 — 关键差距

- 当前上传走 `POST /config/api/assignments/upload-video` **直接进容器** (multipart), 中间**没有独立 nginx**, 只有 CloudRun 网关。
- **腾讯云托管 (CloudRun) 网关层请求体上限**: 平台未在项目文档实测, 计划/PRD 标记 "CloudRun 默认 32MB 可能不够, 需确认"。**上线前必须在 CloudRun 控制台确认上行 body 上限是否 ≥ 200MB**。
- **推荐改法 (3 选 1, 按复杂度升序)**:
  1. **控制台确认 + 上调**: 若 CloudRun 服务设置提供请求体大小上限配置, 调到 ≥200MB; 不改代码。 (最简单, 先试)
  2. **Dockerfile 加 nginx 反代**: 容器内加 nginx 前置 (`client_max_body_size 200m`), uvicorn 在后面。**会改 Dockerfile + 端口链 (nginx:80 → uvicorn:8080), CloudRun healthcheck/端口配置也要跟着对齐** — 复杂度最高, 最不推荐 (动现有稳定架构)。
  3. **前端直传 COS (签名 URL 分片)**: 绕过网关, 浏览器拿 COS 签名直接分片传桶, 服务端只存 metadata。**v1 未做 (Sprint 明确不做断点续传), 列为未来扩展**; 若 200MB 上行确实被网关卡死, 这是唯一根治路。
- **结论**: 先做方案 1 (控制台确认上限, 够就什么都不用动); 若平台硬限 32MB 且不可调, 升级到方案 3 (签名直传)。方案 2 尽量避免 (动容器架构)。

## Step 1 — 本地测试全过

```bash
cd ~/dev/dizical
pytest tests/test_upload_video_cos.py tests/test_video_upload_ui.py tests/test_video_practice_modal.py -q
```
- 期望 3 文件全 PASS (S1: 7 case + S2: 10 case + S3: 6 case, 共 23)
- 全量 `pytest -q` 也跑一遍确认无回归

## Step 2 — 部署快照 `.cloudrun-deploy-new/` 跟 git HEAD 对齐 (AGENTS.md pitfall 40 SOP)

```bash
cd ~/dev/dizical
# 关键文件 md5 对齐
for f in Dockerfile cloudrun.yaml requirements.txt pyproject.toml; do
  g=$(git show HEAD:$f | md5 | awk '{print $1}')
  d=$(md5 -q .cloudrun-deploy-new/$f)
  [ "$g" = "$d" ] && echo "OK  $f" || echo "STALE $f"
done
# src/ 校验: deployment-clone 用 git archive 提, 不用 checkout 污染主仓
git archive HEAD src | tar -x -C .cloudrun-deploy-new/src/
```
> pitfall 40: 不一致 = 上次 sync 后又 commit 没重跑, 必 STALE 再 deploy, 否则部署的是老代码。

## Step 3 — 验证 cos_uploader 生产可用 (真实行为, 不只 is_available)

- `cos_uploader.is_available` 在 prod env = True (4 个 COS_* env 齐全)
- **`cos_uploader.upload_stream` 真打 COS**: 部署后走一次业务动作 (传一张图/小视频), 看返回 URL:
  - `https://{bucket}.tcb.qcloud.la/videos/...` → ✅ 走 COS
  - `/uploads/videos/...` (本地路径) → ❌ COS 没生效, 检查 env / qcloud_cos 依赖 (pitfall 28: pyproject + requirements.txt 双写)
- ⚠️ 自检会产生副作用 (COS 留测试对象 + 可能建空 daily), 验完按 pitfall 37 清理

## Step 4 — docker build + push + CloudRun deploy

```bash
# 走传统 5 步 SOP (dizical-cloudrun-deploy skill): auth → rsync src → deploy
# mcp: manageCloudRun(action='deploy', serverName='dizical-prod', targetPath='/Users/mt16/dev/dizical/.cloudrun-deploy')
```
- **targetPath 必须是 `.cloudrun-deploy`** (子目录, 不是项目根 — 项目根镜像 3.37GB create_failed 坑 #2)
- 轮询 `queryCloudRun(action='detail')` 等 `latestDeploy.Status == normal` + `FlowRatio == 100` + `HasTraffic == true` (5-8 分钟)
- MCP 180s timeout ≠ deploy 失败 (DeployId 变了 = 真发起, 别盲 retry)

## Step 5 — 平台健康检查 + post-deploy 验上传

- **健康检查端口**: 容器内 `8080` (跟现有图片 SOP 一致) — Dockerfile EXPOSE/CMD/HEALTHCHECK/cloudrun.yaml healthcheck 全部 8080, 别写成容器本地 8765 (坑: 075 deploy_failed)

```bash
# 平台健康检查 (liveness)
curl -s -o /dev/null -w "%{http_code}\n" "https://dizical-prod-283401-10-1454535414.sh.run.tcloudbase.com/health/live?cb=$(date +%s)"

# post-deploy: 上传端点可达 + multipart 真传
curl -s "https://dizical-prod-283401-10-1454535414.sh.run.tcloudbase.com/config/api/assignments/upload-video?cb=$(date +%s)" -F "file=@tests/fixtures/sample.mp4" | python3 -m json.tool
```
- 期望: 返回 `{ok:true, url: "https://{bucket}.tcb.qcloud.la/videos/{uuid}.mp4", ...}` → 视频真的到 COS
- 若返 413 / 网关 502 → body size 被网关拦, 回 Step 0 方案解决
- 清测试对象 (pitfall 37)

## 验证清单 (部署后必走)

- [ ] pytest 3 文件全 PASS + 全量无回归 (Step 1)
- [ ] `.cloudrun-deploy-new/` 关键文件 md5 = git HEAD (Step 2)
- [ ] COS is_available=True + upload_stream 实际返 tcb.qcloud.la URL (Step 3)
- [ ] deploy normal + FlowRatio 100 + HasTraffic true (Step 4)
- [ ] `/health/live` + `/config/api/assignments/upload-video` 200 (Step 5)
- [ ] dad 跨端验收: iPhone Safari / iPad Safari / Mac Safari / Mac WKWebView (上传 → 录入绑科目 → 练习/prepare 页 modal 播放)

## 相关
- 长期参考: `reference/teacher-requirement-video.md`
- deploy skill: `hermes: dizical-cloudrun-deploy`
- 数据红线/收尾: `AGENTS.md`