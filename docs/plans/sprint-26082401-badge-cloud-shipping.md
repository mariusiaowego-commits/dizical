# Sprint 26082401: badge 工作流云原生化 (轻量版)

> 日期: 2026-08-24
> 作者: coder + agy (Gemini 3.7 Flash) reference
> 状态: 启动

## 触发

dad 在 /config/badge 提交新 badge 草稿 (join_exam_23), 后端返 `draft_id=a547a6`,
dad 切到 hermes chat 准备调 `/badge-image a547a6` 时, 发现 draft 文件不存在.

三路验证:
1. `data/lib/badge_data/` 目录 0 个 draft JSON
2. `list_drafts()` 返空
3. session_search 找不到该草稿的创建记录

## 根因 (agy + coder 双 audit 确认)

**dizical 上云 (Sprint 09, 2026-07-17) 后, badge V2 工作流的本地文件契约没适配云原生**:

- `badge_draft.py` (V2 设计, 2026-06-12) 走 `lib/badge_data/{draft_id}.json` 文件契约
- `cos_client.py` (PR #227, 2026-08-03) 解决 `/uploads` 容器重启丢图, **但只覆盖 uploads, 没碰 badge**
- CloudRun `dizical-prod` 容器 (MCP `queryCloudRun` detail 验证):
  - `VolumesConf: []` — 无任何持久化卷挂载
  - `OperationMode: alwaysScale, MinNum=1, MaxNum=4` — 容器会扩缩
  - Image: `dizical-prod-100-20260818134918` (8-18 部署)

dad UI 看到的 `a547a6` POST 实际写到了 **CloudRun 容器 OverlayFS `/app/data/lib/badge_data/`**,
接口返 200 OK + draft_id, 但容器跟本地 Mac 物理隔离, 容器重启/换实例后文件丢失.

**附加发现 (agy)**:
- `badge_workflow.py:201` `move_tmp_to_static()` commit 时复制 PNG 到容器内 `static/badges/`
- 同样问题: commit 后图跟容器, 容器换镜像 = 图 404 挂图
- 当前 `achievement_badges` 表所有 url 都是 `/static/badges/*.png` (12 条), 容器一旦换镜像全 404

## dad 拍板方向 (2026-08-24)

dad: "我可能真的这样配置流程不会出现在云端实现. 生图工作流都是本地也不影响, 直到真正生图完成后, 把所有数据传到 badge 表里 (在云端的), 这样云端的 badge 都是正常的"

**轻量版方案**:
- 草稿 + 生图 + PNG 全部在本地 Mac 走 (`data/lib/badge_data/` + `static/badges/` 不动)
- commit 时 PNG 上传 COS + 写云端 MySQL 三表 (achievements + achievement_badges + achievement_stats)
- 云端 iPad / 用户只看到 commit 后的成品 badge

## 改动 (半天, 4 个文件)

### 1. `src/kid_app/badge_workflow.py` (主改)
`api_commit_from_draft` 在 `move_tmp_to_static()` 之后 + `insert_badge_row()` 之前插入:

```python
# V3.0 (2026-08-24): PNG 走 COS, 写完整 https URL 到 achievement_badges.url
from src.kid_app.cos_client import cos_uploader
final_url = None
if cos_uploader.is_available:
    # 生产路径: 上传到 COS, 写公开 URL
    static_path = badge_draft.static_path_for(req.draft_id, image_version)  # 待实现
    png_bytes = Path(static_path).read_bytes()
    cos_key = f"badges/{badge_id}_v{image_version}.png"
    try:
        final_url = cos_uploader.upload(cos_key, png_bytes, content_type="image/png")
    except RuntimeError as e:
        return JSONResponse({"ok": False, "error": f"COS 上传失败: {e}"}, status_code=500)
else:
    # 本地 fallback: 老路径 (跟 V2 完全一致)
    static_path = badge_draft.move_tmp_to_static(req.draft_id, image_version)
    final_url = f"/static/badges/{badge_id}_v{image_version}.png"
```

`insert_badge_row(conn, url=final_url, ...)` 改用 final_url 取代硬编码 `/static/badges/...`。

### 2. `src/kid_app/badge_draft.py` (新增 helper)
```python
def static_path_for(draft_id: str, version: int) -> Path:
    """返回 .tmp/{draft_id}_v{version}.png 的实际路径, 不复制.

    用于 V3 commit: 先复制 tmp 到 static (老逻辑) 或读 tmp 直接上传 COS (新逻辑).
    """
    return tmp_path_for(draft_id, version)
```

### 3. `tests/test_badge_cos_shipping.py` (新增)
- mock cos_uploader.is_available = True → 验证 url 写 COS URL
- mock cos_uploader.is_available = False → 验证 url 写 /static/badges/ (fallback)
- mock COS 上传失败 → 验证返 500, DB 无写入

### 4. `docs/PRDs/AI-PRD-badge-cos-shipping-260824.md` (新增)
PRD 文档, 描述架构变更 + 测试覆盖.

## 验证

### 本地 (无 COS env)
- pytest test_badge_cos_shipping 全 PASS
- 走 /config/badge 提交新 draft → 本地 8765 + SQLite + 写 /static/badges/ (跟 V2 一致, 无回归)

### 云端 (.env 有 COS_* + DATABASE_URL=mysql://)
- 部署 dizical-prod-test 到 CloudRun
- curl 提交 draft → COS 上传 + 云 DB 写
- iPad 访问云端 /achievements → 看 COS 图 ✅

### 关键不变量
- 老 `static/badges/*.png` (12 条) 不动, Docker COPY 进镜像永远有效
- `achievement_badges.url` 字段类型兼容 (相对路径 / 绝对 URL 都支持)
- iPad / 云端前端 `<img src>` 两种 url 都能加载

## 不做 (跟 v1 / v2 / v3 方案区分)

| 不做项 | 原因 |
|--------|------|
| 重构 `badge_draft.py` 走 DB | dad 拍板: 草稿工作流只在本地, 不需要 DB 化 |
| `badge_drafts` 新表 | 同上 |
| Skill V2.7 改 multipart upload | 本地 file 契约 + 老 Skill 路径完全保留, 不需要改 |
| 双模 migration 脚本 | 不动 DB schema, 不需要 migration |
| 存量 `static/badges/*.png` 批量迁 COS | Docker COPY 进镜像, 不动; 增量走 COS |

## 风险降级

1. **COS 上传失败**: 直接返 500, DB 零写入, draft 保留 `draft_awaiting_confirm` 状态 (幂等可重试)
2. **本地 COS 未配置**: is_available=False → fallback 老路径, 完全向后兼容
3. **PNG 损坏**: tmp_path_for 已存在, 不影响 (PIL 验证在 step 2 skill 跑过)
4. **COS 公开读 URL 泄露**: badge 图 0 PII (PRIVACY.md §一/§二 已确认), 不构成隐私风险

## Sprint 时间线

- 2026-08-24 4:30pm: plan + 文档沉淀 (当前)
- 2026-08-24 5:00pm: feat/badge-cos-shipping 分支 + 主改 + 测试
- 2026-08-24 6:30pm: 本地 pytest + 云端 dry-run
- 2026-08-24 7:00pm: PR feat/badge-cos-shipping 给 dad merge

## 跟之前 sprint 关联

- PR #227 (2026-08-03): `/uploads 切 COS` — 复用 `cos_uploader` 基础设施
- PR #260 (2026-08-10): web_users v3.3 — DATA 上云, **漏改 badge** (本 sprint 补)
- Sprint 09 (2026-07-17): 切云加固 — 没碰 badge file contract