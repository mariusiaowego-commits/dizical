# 腾讯云托管 (CloudRun) 部署 FastAPI + SQLite — Spike 最佳实践

> 区域：仅 **ap-shanghai**；参考官方模板 [TencentCloudBase/cloudrun-fastapi](https://github.com/TencentCloudBase/cloudrun-fastapi) 与 [docs.cloudbase.net/run](https://docs.cloudbase.net/run/introduction)。本文件聚焦 Phase 0 spike「能不能跑起来」的最小路径。

---

## 1. 最少必要的 4 个文件 / 配置

**(a) `Dockerfile`** — 锁 pip 镜像源 + 暴露端口（必须与控制台「端口」一致）：
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip config set global.index-url https://mirrors.cloud.tencent.com/pypi/simple/ \
 && pip config set global.trusted-host mirrors.cloud.tencent.com \
 && pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**(b) 入口 `main.py`** — 绑定 `0.0.0.0`（非 `127.0.0.1`），端口读 `PORT` 环境变量。CloudRun 容器内 `PORT` 始终反映请求目标端口，硬编码端口是高频踩坑点。

**(c) `.dockerignore`** — 排除 `.venv / __pycache__ / .git / *.db / .env`，否则 SQLite / 虚拟环境被打进镜像或反向被忽略。

**(d) 控制台「服务设置」必填 3 项**：
- **端口** = 8080（与 `EXPOSE` / `CMD` 完全一致；范围 1–61000，禁用 9100）。
- **环境变量**：`PORT=8080`（spike 阶段可仅此一项）。
- **最小副本数 = 1**：spike 期间不要设 0，避免冷启动被误判为部署失败。

---

## 2. 健康检查 Endpoint 必须返回什么

CloudRun **主动 HTTP 探活**：对配置的 path 发 `GET`，**返回 HTTP 200 即判活**，3xx/4xx/5xx 一律算失败 → 实例被反复重启。

返回 body **无强约束**（JSON 文本即可），最简实现：
```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```
注意三点：path 必须真实存在（404 → 持续重启）；不要在 `/health` 内跑 SQLite 慢查询（启动期 CPU 飙高触发探活超时）；不要返回 503「starting up」当正常 — 那是反模式。

---

## 3. SQLite 在 CloudRun 容器里能用吗

**短答：能跑，但 `/tmp` 够不够不是问题 — 重启会丢数据是问题。**

- 容器**无持久化存储**：扩缩容 / 重启 / 部署新版本 → 容器文件系统被还原，写入的 `*.db` 文件消失。
- `/tmp` 是 tmpfs（内存盘），大小受容器规格限制，spike 写读能跑通，**任何写库都不能信任持久性**。
- 写本地 `*.log` 同理丢，生产必须接 CLS 日志服务。

**Phase 0 spike 用法**：`.db` 放 `/app/data/app.db`，证明 schema 能建、能读写一条；**接受重启丢失**，并在文档明写「SQLite 仅用于 spike，跑完即丢」。真要持久数据：接 MySQL / CynosDB / TDSQL-C（CloudRun 同 VPC 内网可达）。

---

## 4. 部署后验证 spike 成功的 URL

CloudRun 创建服务后**自动分配默认域名**（控制台「访问服务」直达）。格式：
```
https://<serviceName>-<envId>.ap-shanghai.run.tcloudbase.com
```
- 强制 HTTPS（443），不支持改 HTTP。
- 默认域名**仅供测试，不承诺 SLA**；生产前必须绑**已备案自定义域名**（2025-10-09 后环境会弹中间页软提醒，spike 可忽略）。

**spike 通过验证三连**（全 200 即可）：
```bash
curl -i https://<svc>-<env>.ap-shanghai.run.tcloudbase.com/         # 服务可访问
curl -i https://<svc>-<env>.ap-shanghai.run.tcloudbase.com/health   # 探活 OK 不重启
curl -i https://<svc>-<env>.ap-shanghai.run.tcloudbase.com/docs     # FastAPI Swagger 路由全注册
```

---

## 5. 常见 spike 失败的 5 个原因 + 排查

**❶ `Readiness probe failed: dial tcp ... : connection refused`** — 90% 是端口不一致。三处必须相同：控制台「端口」/ `Dockerfile` `EXPOSE` / `CMD` 启动端口。多行 `CMD` 只最后一行生效，前面的被静默忽略也是此错。

**❷ `Back-off restarting failed container`** — 代码层启动失败。排查：控制台 → 服务详情 → 「日志 / Webshell」看 `traceback`。最常见：本地 `pip install` 后未写进 `requirements.txt` → `ModuleNotFoundError`；其次本地 Python 3.12 与镜像 `python:3.11-slim` 不兼容。

**❸ Dockerfile 构建 >10 分钟报「空白」** — `pip install` 走了默认 pypi.org，国内网络抽风卡死。用 `mirrors.cloud.tencent.com/pypi/simple/` 镜像源，并把 `requirements.txt` COPY 拆独立层利用 Docker 缓存。

**❹ `xxxxxx: no such file or directory`** — 看似代码路径错，实际经常是 `.dockerignore` / `.gitignore` 把 `*.db` / `.env` / `data/` 打入了黑名单。

**❺ 访问域名报 `SERVICE_NOT_READY` / `ECONNREFUSED`** — 不是部署失败，是冷启动。最小副本数设为 0 → 30 分钟无请求缩容到 0 → 下次请求正在冷启动。spike 设最小 1 避免误判。

---

## Phase 0 spike DoD

- [ ] `curl /`、`/health`、`/docs` 三个全 200
- [ ] SQLite 写一行读一行 OK（接受重启丢失）
- [ ] 控制台「实例」至少 1 个 Running
- [ ] 日志采集到 CLS（不要只依赖 Webshell — 容器重启即丢）

**Phase 0 不做**：接 MySQL / 自定义域名 / CI/CD / 灰度 / HTTPS 证书 / 扩缩容调优 — 留给 Phase 1+。