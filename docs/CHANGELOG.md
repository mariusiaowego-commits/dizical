# Changelog — dizical

所有对本项目有意义的功能、修复、变更都会记录在此文件。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

> 口语版变化可看本地 `STATUS.md` / `vibe-coding-log.md` / `handoff-*.md`（**不上 GitHub**，见 [DOCS-POLICY.md](DOCS-POLICY.md)）。

---

## [Unreleased]

### Security（隐私清理）
- **GitHub 隐私清理** —— `STATUS.md` / `vibe-coding-log.md` 不再推送 GitHub（之前误入 main，commit 52692ed 之前多次出现；现 .gitignore 已加固含 `/` 前缀 + `docs/STATUS.md` 兜底）
- **`docs/handoff-archive/`** —— 历史 handoff 全部本地归档，不再推送
- 新增 [docs/DOCS-POLICY.md](DOCS-POLICY.md) 声明哪些文档属于"本地 agent 协作参考"，对访客不可见

### Changed（变更）
- `README.md` 同步至 v3.3.4（web user auth + 测试 505 passed），修正文档引用（STATUS/vibe/handoff 改为"本地参考不上 GitHub"）
- `.gitignore` 加固隐私文件规则（含 `/STATUS.md` 严格前缀、`docs/STATUS.md` 兜底、`docs/handoff-*.md` 兜底）

---

## [2026-08-12] — v3.3.4 web user auth Phase 1 (login_page + register + 3 套环境密码同步)

### Added（新增）
- **`/login` 路由** + `/register` 自助注册（Phase 1 内网环境，3 套环境密码同步 — local/staging/cloud）
- **`src/auth.py`** —— PBKDF2-SHA256 密码哈希（salted）+ session 管理
- **`src/kid_app/auth_page.py`** —— login/register 路由（iPad 友好卡片布局）

### Changed（变更）
- **login_page RedirectResponse** —— 已登录访问 /login 返 500 bug 修复（缺失 import），pytest 加 edge-case 防御
- **复制按钮 fallback** —— 旧浏览器无 clipboard API 时降级为选中态
- **密码最少 6 位** 强制校验

### Tests
- 268+ pytest passed（v3.3.4 closeout），0 死分支

---

## [2026-07-01] — V2.10 badge 图重生 + rembg 抠图

### Added（新增）
- 装 **rembg[cpu]** (2.0.76) + onnxruntime (1.27.0) 到 `.venv-service/`
  - badge-image skill 现在 PIL + rembg 双保险直接跑通 (旧版只有 PIL 阈值, gpt-image-2 浅灰背景去不掉)
- 创建 `.venv-service/` venv, 服务从 `.venv-service/bin/uvicorn` 启动
- `streak_1_v2.png` / `streak_3_v2.png` / `streak_7_v2.png` — rembg-cleaned 备份 (PR #143 副产物)
- `.gitignore` 加 `.venv-service/`

### Changed（变更）
- **PR #143** streak_1/3 风格还原 (V1 era 原版风格, 不是 V2 era chibi girl + 大数字 模板):
  - **streak_1** 新图: **绿色拟人化竹笛** + 4 颗粉红心形 (无数字). browser vision 实测确认.
  - **streak_3** 新图: **chibi girl + 笛子 + 金红橙火焰环绕** (火焰像 halo, 无数字). browser vision 实测确认.
  - **streak_7** 保持: chibi girl + 大金色 7.
- 边缘质量: 硬 alpha mask (alpha < 128 → 0, 否则 255), 0 partial alpha 像素

### Removed（移除）
- `streak_7_v1.png` (PR #140 PIL-only 版, 被 v2 supersede)

### Tested
- pytest 12/12 通过 (PR #139 + #101 旧测试不破)
- Browser vision 校验 3 张卡: 风格全部对
- 服务 PID 25221, `.venv-service/bin/uvicorn`, port 8765 live

---

## [2026-07-01] — V2.9 streak+badge 终章

### Fixed（修复）
- **PR #138** —— streak_*/lucky_61_*.milestone 永久解锁。`streak_7/14/30` 等里程碑以前用「今日往前 streak」永远 calc 不出，现在改为「历史上首次连续 ≥ N 天」后永久解锁。
- **PR #138** —— `lucky_61_YYYY` 改 milestone（不再 seasonal 当月 60 min 判断）；历史首次对应年份 06-01 练过 → 永久解锁。
- **PR #138** —— `/achievements` + `/badges` 弹窗 `modal-desc` 文字居中（加 `display: block; text-align: center`）。

### Added（新增）
- **PR #139** —— `POST /config/api/badge/replace-image-from-draft` 端点。换已有 badge 的图不写 achievements/stats 表；走 `badge_db.update_badge_current` UPDATE old is_current=0 + INSERT new is_current=1。老图保留作历史版本（is_current=0），可直接回滚。

### Changed（变更）
- **PR #141** —— `CalcResult.condition` 文案从工程视角改为小朋友视角：
  - unlocked: `你在 2025-10-03 第一次连着打卡 7 天` (含达成日)
  - locked: `连着打卡 100 天就能拿到` (直白条件)
- **PR #141** —— `lucky_61_YYYY` 同款改法 (六一儿童节当天练过 / 6月1日练习就能拿到).

### Fixed（修复 - 数据）
- **PR #141** —— 补 DB migration：生产 DB 里 `lucky_61_*` category 从 `seasonal` → `milestone` (PR #138 漏掉的 DB 同步).

### Assets（资源）
- **PR #140** —— 重生 streak_1/3/7 图：
  - `static/badges/streak_1_v1.png` (1024×1024 RGBA, 49.3% transparent)
  - `static/badges/streak_3_v1.png` (1024×1024 RGBA, 45.0% transparent)
  - `static/badges/streak_7_v1.png` (1024×1024 RGBA, 49.9% transparent)
- 老图（`streak_1/3/7.png`）保留，DB `is_current=0` 不删。
- `_v1.png` 命名 = 0 padding，差后续版本前不会撞。

### Tests
- `tests/test_replace_image_endpoint.py` — PR #139 新单测 5/5:
  - happy_path / wrong_status (400) / unknown_badge (404) / draft_without_image (400) / invalid_draft_id (404)
- `tests/test_achieved_at_override.py` — 历史 7/7 不破。

---

## [2026-06-30] — V2.6/V2.7/V2.8 badge workflow 多版迭代

### V2.8 (PR #137)
- 待确认 badge 预览图 404 修复 —— 加 `GET /config/api/badge/draft-image` 端点走 FileResponse 返 `.tmp/` 真图（draft 期间图片路径不在 static mount 下导致 404）。
- 双重 path traversal 防御 (draft_id 字符白名单 + image.path `relative_to(_badge_data_dir)`)。

### V2.7 (PR #136)
- 待确认 badge UX 重构 (Option C 卡片+行内化+脚部) —— 4 个 chip 元素从灰底深字调整为暖白底，dizicute 6 色 token 零扩展。

### V2.6 (PR #134)
- badge 表单 UI 重构 dizicute 对齐 + 拆 CSS + 4 轮 UI 调优。

### V2.6 (PR #135 早些时候)
- 去背工作流 V2.6 —— PIL 阈值 + rembg 双路无条件执行 + system-python 保底（`gpt-image-2` 浅灰背景模型 fallback）。

---

## [2026-06-16] — V2.4/V2.5 钥匙 badge 工作流

### V2.5 (PR #101)
- unlock_strategy 字段：纪念章 `immediate`（commit 时直接 achieved=Y + achieved_at=now）/ `calc`（走 calc 评估）。
- 考级 1-10 通用 achieved_at_override。

### V2.4 (PR #100)
- cond_text 字段独立，modal-cond 3 级 fallback: `cond (calc)` > `cond_text (user/AI)` > `desc (zh_story)`。

### V2.4 (PR #98)
- badge workflow 6 bug 完整修复。

---

## [更早版本]

见 [docs/handoff-archive/](../handoff-archive/)（本地归档，**不上 GitHub**，见 [DOCS-POLICY.md](DOCS-POLICY.md)）
及之前 PR（按 commit 历史：`git log --oneline`）。

---

## 版本与部署一致性自检

部署前请确认本地 HEAD = origin/main：

```bash
git rev-parse HEAD
git rev-parse origin/main   # 应当输出一致
```

不一致：

```bash
git fetch origin
git pull origin main --ff-only
```
