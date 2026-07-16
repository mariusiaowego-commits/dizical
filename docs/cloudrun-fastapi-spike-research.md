# 腾讯云托管 (CloudRun) 部署 Python FastAPI + SQLite — Phase 0 Spike 清单

> 目的：验证「CloudRun 能跑起来 FastAPI + SQLite」这一最小命题。不接 MySQL、不改业务。  
> 参考：腾讯云官方文档 + `TencentCloudBase/cloudrun-fastapi` 官方模板 + 微信云托管 FAQ。  
> 区域：CloudRun 当前仅支持**上海 (ap-shanghai)**。

---

## 1. 最少必要的 4 个文件 / 配置

参考官方模板 [TencentCloudBase/cloudrun-fastapi](https://github.com/TencentCloudBase/cloudrun-fastapi/blob/main/Dockerfile) 与 [d.../docs/cloud-run.md](https://github.com/TencentCloudBase/cloudrun-nestjs/blob/main/docs/cloud-run.md)（同源），最少要这 4 件：

### (a) `Dockerfile` — 用腾讯云 pip 镜像源，避免构建超时 / 网络中断
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
关键点：`EXPOSE` 和 `CMD` 里的端口必须**与控制台填写的「端口」完全一致**，否则部署报 `Readiness probe failed`。

### (b) 入口 `main.py` — `host=0.0.0.0`, 读 `PORT` 环境变量
```python
import os
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
async def root():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```
绑定 `0.0.0.0`（不是 `127.0.0.1`），否则容器外访问不到。

### (c) `.dockerignore` — 防止 `.venv / __pycache__ / .git` 被 COPY 进镜像
```
__pycache__ .venv venv *.pyc .git .env .dockerignore
```

### (d) 控制台「服务设置」必填 3 项
- **端口**：8080（和 `EXPOSE` / `CMD` 一致；端口范围 1–61000，**禁用 9100**）。
- **环境变量**：spike 阶段不强需；后续若接 DB 再加 `DB_HOST / DB_PORT / DB_PASSWORD`。
- **实例副本数最小值**：spike 设 **1**（不要 0），否则冷启动期间访问会拿到 `SERVICE_NOT_READY`，会让人误判部署失败。

> 部署方式二选一：上传代码包（推荐 spike，自带 Dockerfile 自动构建） / 拉取镜像（需要先开容器镜像服务访问管理，多一步）。

---

## 2. 健康检查 Endpoint 必须返回什么

CloudRun 的「健康检查」是**平台主动探活**：模拟 `GET /health`（或你配置的 path），**返回 HTTP 200 即视为存活**。系统据此判 `Readiness probe failed` / `Liveness probe failed`。  
返回字段**没有强约束** — 内容不重要，**status code 是 200** 才算数；3xx/4xx/5xx 全部算失败。

Phase 0 spike 最简实现：

```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```
注意三件事：
- **path 必须真实存在**，否则每次探活 → 404 → 探活失败 → 实例被反复重启（`Back-off restarting failed container`）。
- **不要在这里读写 SQLite 慢查询**，否则启动期 CPU 飙高 + 探活超时 → 又触发重启。
- 不要返回 503「starting up」当「正常」 — 那会被当成存活信号，但流量进不来；要么返回 200 让它「真的 OK」，要么直接不挂这个 endpoint。

---

## 3. SQLite 在 CloudRun 容器里能用吗 — 重点

**短答：能跑，但 /tmp 不是「够」不够的问题 — 是「会丢」。**

- 容器是**无持久化存储**的（官方原话：「容器不支持持久化存储，容器扩缩容/重启自愈时写入的文件会被还原」）。**重启 / 缩容到 0 再扩 / 部署新版本 → SQLite 文件消失**。
- `/tmp` 是 tmpfs（内存盘），大小受容器规格限制；Phase 0 spike 写读「能跑通」，**但任何写库都不能信任持久性**。
- 写日志到 `/app/logs/*.log` 同理会丢，日志必须走 CLS 采集 → 腾讯云日志服务。

**Phase 0 spike 的 SQLite 用法建议**：

| 用途 | 推荐 | 不推荐 |
|---|---|---|
| spike 「能启动」验证 | 把 `.db` 放在 `/app/data/app.db`，证明 schema 能建、能读 | 用 `:memory:` — 证明不了 IO |
| spike 「能写一条」验证 | 同上，写一行读一行；**接受重启丢失** | 想做持久化测试 |
| 真要持久数据 | 接 MySQL / CynosDB / TDSQL-C（CloudRun 同 VPC 内网可达） | 写本地 `*.db` 假装生产 |

Phase 0 文档里要明写一句「SQLite 仅用于 spike，跑完即丢」，避免被前端当成「后端已经接好数据库」。

---

## 4. 部署后验证 spike 成功的 URL

CloudRun 创建服务后**自动分配默认域名**（控制台「访问服务」按钮直达）。格式：

```
https://<serviceName>-<envId>.ap-shanghai.run.tcloudbase.com
```
- `<serviceName>`：你建服务时起的名字（小写字母+数字+横线）。
- `<envId>`：CloudBase 环境 ID。
- **强制 HTTPS，默认 443**；不支持改 HTTP。
- 注意：**默认域名仅供测试用，不承诺 SLA**；生产前必须绑**已备案的自定义域名**（2025-10-09 后的环境会弹「访问提示中间页」软提醒，spike 阶段可忽略）。

**Phase 0 spike 通过验证的命令**（两条都 200 即可）：
```bash
curl -i https://<serviceName>-<envId>.ap-shanghai.run.tcloudbase.com/
curl -i https://<serviceName>-<envId>.ap-shanghai.run.tcloudbase.com/health
curl -i https://<serviceName>-<envId>.ap-shanghai.run.tcloudbase.com/docs   # FastAPI Swagger
```
第一条验证「服务可访问」，第二条验证「探活不被重启」，第三条验证「应用代码完整启动」。

---

## 5. 常见 spike 失败的 5 个原因 + 排查

下面 5 条均来自 [CloudRun 官方 FAQ PDF](https://main.qcloudimg.com/raw/document/product/pdf/1243_59521_cn.pdf) 与 [微信云托管 FAQ](https://developers.weixin.qq.com/minigame/dev/wxcloudrun/src/guide/service/faq.html)，**spike 阶段最高频**：

### ❶ `Readiness probe failed: dial tcp ... : connection refused`
**90% 是端口不一致**。  
排查链：
1. 控制台「服务设置 → 端口」填的是 `?`
2. `Dockerfile` 里 `EXPOSE ?`
3. `CMD` / `uvicorn --port ?` 里启动的是 `?`  
三个 `?` 必须**完全相同**。  
补充：多行 `CMD` 只有最后一行生效（Docker 官方规则），前面的会被静默忽略 → 也是这个错。

### ❷ `Back-off restarting failed container` / `check pod status is not ok`
**代码层面启动失败**（不是平台问题）。  
排查：
1. 控制台 → 服务详情 → 「日志」/「Webshell」进容器，看 `python main.py` 的 `traceback`。
2. 最常见：本地 `pip install xxx` 后没写进 `requirements.txt` → 镜像里没这个包 → `ModuleNotFoundError`。
3. 第二个常见：本地用的 Python 3.12，Dockerfile 用 `python:3.11-slim` → 语法 / typing 不兼容。

### ❸ Dockerfile 构建超时（>10 分钟）→ 报「无报错日志」「空白」
**spike 最隐蔽**。  
原因：`pip install` 走了默认 pypi.org，国内网络抽风 → 卡死直到超时。  
解决：用上面 (a) 里的 `mirrors.cloud.tencent.com/pypi/simple/` 镜像源，并把 `requirements.txt` COPY 独立成一层（利用 Docker 缓存）。

### ❹ `xxxxxx: no such file or directory`
看似代码路径错，**实际经常是 `.dockerignore` 把文件忽略了**。  
排查：检查 `.gitignore` / `.dockerignore` 里有没有 `*.db` / `.env` / `data/` 等被打入黑名单 — 有就去掉。

### ❺ 服务能起，但访问域名报 `SERVICE_NOT_READY` / `connect ECONNREFUSED`
**不是部署失败，是冷启动**。  
副本数最小值设了 0，30 分钟无请求 → 缩容到 0 → 再次请求时正在冷启动。  
spike 阶段把最小副本数设 **1**（会持续产生一点费用，但 spike 无所谓），避免误判。

---

## Phase 0 spike 通过标准 (DoD)

- [ ] `curl /` 返回 200，body 含 FastAPI 标识 JSON
- [ ] `curl /health` 返回 200
- [ ] `curl /docs` 返回 200（证明 FastAPI 路由都注册了）
- [ ] SQLite 写一行读一行 OK（接受重启丢失）
- [ ] 控制台「服务监控 → 实例」至少 1 个 Running
- [ ] 日志采集到 CLS（不要只看 Webshell — 容器重启后就没了）

**spike 不做的事**（留给 Phase 1+）：接 MySQL、自定义域名、CI/CD 流水线、灰度发布、HTTPS 证书、多实例扩缩容调优。

