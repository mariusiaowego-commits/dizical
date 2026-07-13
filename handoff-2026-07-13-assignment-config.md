# Handoff: 2026-07-13 assignment 配置增强 (PR #155)

## 概要

PR #155 `feat/assignment-config-stage-images` 完成了老师要求全端配置增强。3 个 commits, +602/-56, 7 files。已 merge main + 重启 prod。

### 改动清单

| 文件 | 改动 |
|------|------|
| `src/database.py` | `save_weekly_assignment` line 632 修复 images 参数被忽略的 bug |
| `src/kid_app/app.py` | 新增 `/uploads` StaticFiles mount; prepare 页传 assign_images 到模板 |
| `src/kid_app/routes/config.py` | PUT/DELETE/upload 端点; API 返回 images/stage_order/stage_start/end; stage 字段覆盖逻辑 |
| `src/kid_app/templates/prepare.html` | 4 部分 subject-block 展示 + 图片画廊 + CSS counter a)b)c) |
| `src/kid_app/templates/practice.html` | `updateReqPanel(btn)` 改接收 btn 提取 name+id+req+images; WEEKLY_ASSIGN.images 渲染 |
| `src/kid_app/templates/config-practice-log.html` | 录入表单加 stage 字段 + 图片上传; Tab2 历史卡片 4 部分 + edit/delete + stage pill + 图片; Tab3 周总览 same |
| `.gitignore` | 加 `.hermes/` + `uv.lock` 忽略 |
| `dizical-image-style skill` | 跨 3 profile 同步 (dizical/coder/default) |

### 新 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/config/api/assignments/{lesson_date}` | 全量更新 (items/images/notes/stage) |
| DELETE | `/config/api/assignments/{lesson_date}` | 删除 |
| POST | `/config/api/assignments/upload` | 配图上传 (multipart, 存 data/uploads/raw/) |

### 未完成

1. **dizical-image-style skill 的实际调用** — 前端上传后自动调 hermes image-to-image 做风格化 (当前只存 raw, 需手动触发)
2. **图片点击放大 lightbox** — 当前用 `window.open` 新 tab 打开
3. **Practice 页 "展开全部" 本周所有科目** — 楼层 1 当前只显示选中科目, 没有展开按钮
4. **Tab2 分页** — 加载 16 周历史, 数据量大时可加前/后翻
