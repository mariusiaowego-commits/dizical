# PRD: 老师要求 Web UI 增强 (assignment-config-stage-images)

> **接续**: `.hermes/plans/assign-phase1b-image-storage.md` (CLI 端的 images 字段已落地)
> **当前分支**: `feat/assignment-config-stage-images`
> **当前日期**: 2026-07-13
> **作者**: coder agent (MiniMax-M3)
> **状态**: PRD 阶段（待用户 ack 后进入 tech-spec 落地）

## §1 背景

`weekly_assignments` 表 + CLI/Web 录入页 + prepare 页展示已经全部就绪，**但 config 配置台有 4 个真实缺口**：

| # | 缺口 | 影响 |
|---|------|------|
| ① | **stage 字段缺失** | DB 自动算 stage_start/end/order，但 UI 完全不能手动覆盖；如果老师改课，stage_end 跟实际节奏脱节 |
| ② | **编辑/删除入口缺失** | 25 行历史数据写错只能 SQL 改；卡片只展示，无操作按钮 |
| ③ | **图片上传链路完全没接** | `images` 列已在 DB，`data/assignment_images/` 目录已建且 `.gitignore`，但 HTTP API 整条链路都没传 `images` |
| ④ | **"本周老师要求"语义错** | `practice.py:310` 用 `get_weekly_assignment(week_start)`（lesson_date 落在周一），lesson_date=周六时永远查不到 |

## §2 目标 (Goals)

1. 老师要求录入表单补 stage 字段（3 个可选 input，留空走自动）
2. 老师要求录入表单补图片上传（**走通用"上传原图 → AI 风格化卡片"工作流**，非裸上传）
3. 历史卡片支持编辑/删除（卡片内联展开，不用 modal）
4. "本周老师要求"周次匹配改用 `get_weekly_assignment_for_week`（lesson_date <= week_start 的最近一条）
5. **全端 assignments 展示重新排版**（prepare / practice / config practice-log Tab2 / Tab3 → 统一结构）
6. 沉淀通用"上传原图 → AI 风格化卡片"工作流（dizical-image-style skill），未来 assignments / practice log / praise 都能复用
7. 所有改动走 PR 流程：测试 + 文档 + 收尾 checklist

## §3 非目标 (Non-Goals)

- 不做图片 OCR / 智能识别（V1 简单优先）
- 不做图片缩略图 / EXIF 清理 / GPS 脱敏（V2 再加）
- 不做孤儿文件清理（删图直接删文件 + DB 引用）
- 不动 `practice_assign` CLI 命令（phase 1b 已落地，本次只补 Web UI）
- **不做新设计系统**：风格化 prompt 用 dizicute token 描述（珊瑚红 #FF6B6B + 暖白 #FFF8F0 + chibi Q版），不引入新 hex / 新风格
- **不改 badge workflow 的 image_path 上传模式**：badge 有自己的去背/上传流水线（`docs/badge-image-workflow.md` V2.6），跟本次通用工作流独立演进
- **不动 practice 页的计时器 / 科目选择 / 仪表盘**：只改 assignment 展示楼层，不动其他楼层

## §4 用户故事

### US-1: 家长录老师要求
- 进入 `/config/practice-log` → 切到「老师要求」tab
- 看到录入表单：上课日期、多个「科目 + 要求」条目、老师补充说明、stage 三字段、可选配图
- 填完提交，看到「✅ 老师要求已录入」toast
- 历史列表刷新，看到刚录入的卡片在最上面

### US-2: 家长配图（走通用 AI 风格化卡片工作流）
- 在录入表单底部看到「📷 添加配图」按钮
- 点击 → 文件选择器（接受 jpg/png/heic）
- **选完后自动走"上传原图 → AI 风格化卡片"工作流**（dizical-image-style skill）：
  1. 原图上传到 `data/uploads/raw/{uuid}.{ext}`（保留原图，DB 存引用）
  2. agent 拼 dizicute 风格化 prompt（含珊瑚红 #FF6B6B / 暖白 #FFF8F0 / chibi Q版 / "保留原图构图和细节"）
  3. 调 hermes `image_generate`（**image-to-image 模式** + 原图作 reference）→ 风格化卡片
  4. 风格化结果存 `data/uploads/styled/{uuid}.png`
  5. DB `images` 字段存 `/static/uploads/styled/{uuid}.png`（最终展示用）
- UI 显示：缩略图用风格化结果（不是原图），每张图可单独删除（删除 = 删原图 + 删风格化 + 删 DB 引用）
- **保留原图**：用户上传的原图**永久保留**（可作为未来重新风格化的素材，不丢）
- **历史风格化结果版本化**：同一原图多次风格化时，保留所有版本（`styled/{uuid}_v{n}.png`），UI 默认展示最新版

### US-2.5: 通用 AI 风格化卡片工作流（未来复用）
- **本 PR 必须把通用工作流沉淀为 skill**（dizical-image-style）：
  - 输入：原图（jpg/png/heic）+ 风格描述（默认 dizicute，可指定）
  - 输出：风格化卡片 PNG（透明背景 / dizicute 配色）
  - 调用方式：命令行 `hermes chat -q "..." -t image_style --profile dizical` 跟 badge-image skill 一致
- 未来应用场景（不在本 PR 实现）：
  - practice log 配图（练习照片 → 风格化展示）
  - praise 配图（孩子照片 → 风格化表扬卡）
  - achievements 配图（活动照片 → 风格化纪念章）
- skill 文档：`~/.hermes/profiles/dizical/skills/dizical-image-style/SKILL.md`（跨 3 profile symlink 同步）

### US-3: 家长编辑历史要求
- 历史卡片右上角看到 ✏️ / 🗑 按钮
- ✏️ → 卡片内联展开成表单，预填当前值
- 修改完点「💾 保存」→ 卡片收起 + 列表刷新
- 🗑 → confirm dialog → 「真的要删除 X月X日 的老师要求？」→ 确认 → 卡片消失

### US-4: 前端 assignments 展示统一结构（4 个露出点）

assignments 信息在前端的统一展示结构（**4 部分**）：
1. **科目名称**（item.name）
2. **科目 ID**（item.item_id）
3. **要求**（requirements / requirement），多条用 a) b) c) 编号
4. **图片卡片**（images → 风格化结果 /static/uploads/styled/…），无图时不显示

**日期 / 第 X 期 显示规则**：
- 页面已限定"本周"→ 不额外显示日期（prepare / practice / config-practice-log Tab3 本周总览）
- 历史列表（config-practice-log Tab2）→ **必须显示** lesson_date + stage_order（第 X 期）

**4 个露出点各自的改动**：

| # | 页面 | 路由 | 当前状态 | 改动 |
|---|------|------|----------|------|
| 1 | **prepare 页** | `/prepare` | `assignment-card` 显示 sage 渐变卡片 + 科目:要求列表 | `assign_items_html` 改为 4 部分结构 + images 图片画廊。天数/起止日期由后端算"本周" |
| 2 | **practice 页** | `/practice` | `floor-req` 一层卡片 + `reqTip` 内文字 | `updateReqPanel()` 改为显示 4 部分 + images。`WEEKLY_ASSIGN` 数据已在前端 |
| 3 | **config-practice-log Tab2** | `/config/practice-log` (#tab-assign) | 历史列表卡片显示 📅日期 + 科目:要求 | 卡片改为 4 部分结构 + images + 日期 + stage_order（第 X 期）|
| 4 | **config-practice-log Tab3** | `/config/practice-log` (#tab-week) | `weekAssignmentCard` 只显示文字 | 改为 4 部分结构 + images。已限定本周 → 不额外显示日期 |

### US-4.1 prepare 页（kid-app 起点页）详细展示设计

```
第 X 期 · 老师要求
─────────────────────────────────
▼ 单吐练习    (item_id: 23)
    a) ♩=82 两天
    b) ♩=84 两天
    c) 注意口风不要漏气
  
  [ 风格化图片卡片 ]
  [ 风格化图片卡片 ]

▼ 长音练习    (item_id: 17)  
    a) 低音 765 一组
    b) 高音 1一组
  
  无配图
─────────────────────────────────
```

- 每个科目展开为一个 `assignment-subject` 区块
- 图片卡片行：flex-wrap 布局，每张图 120-160px 宽（平板）/ 适应屏幕
- 无图时不占位
- "第 X 期"来自 stage_order，prepare 页已限定本周 → 不显示日期

### US-4.2 practice 页详细展示设计

```
🎯 老师要求 ────────────────────
  
  [选择科目后展开]
  
  ▼ 单吐练习    (item_id: 23)
    a) ♩=82 两天
    b) ♩=84 两天
  
  [风格化图片卡片]
  
  [其他科目要求折叠在"展开全部"后面]
────────────────────────────────
```

- 当前选中科目高亮显示它的 requirements + images
- 点击"展开全部"可看本周所有科目要求
- 楼层 1 的高度自适应（图片多时 scrollable）

### US-4.3 config-practice-log Tab2 历史详细展示设计

```
📅 2025-11-15  · 第 2 期
  
▼ 单吐练习      (item_id: 23)
  a) ♩=82

▼ 右手开合练习  (item_id: 18)
  a) 3孔-1天
  b) 3+2-2天
  c) 3+2+1孔-3天

无配图

────────────────────────
  
📅 2025-11-08  · 第 1 期
  
▼ 乐曲练习      (item_id: 15)
  a) 以小节为单位反复练习

  [风格化图片卡片]
  [风格化图片卡片]
  
💬 老师补充：新曲子练习步骤：吹（1）...
```

- 每张卡片头部显示 📅 lesson_date + · 第 N 期
- 科目区块可折叠（默认全部展开）
- images 在卡片底部，flex-wrap 布局
- 编辑/删除按钮在卡片右上角（US-3）

## §5 验收标准 (Acceptance Criteria)

```
□ Stage 字段
  □ 录入表单显示 stage_start / stage_end / stage_order 三个 input
  □ 留空 → 自动算（保持现有行为）
  □ 填值 → 用 UI 值覆盖自动算
  □ UI 文字明确说"留空按上次课自动推算"
  □ DB 落库正确（手动测：填 stage_order=99，查 DB 是 99）

□ 图片上传 + AI 风格化（核心）
  □ 录入表单底部有「添加配图」按钮
  □ 选 jpg/png/heic → 原图存 data/uploads/raw/{uuid}.{ext}
  □ **自动触发 dizical-image-style skill**：image-to-image 模式 + dizicute 风格 prompt
  □ 风格化结果存 data/uploads/styled/{uuid}_v1.png，4 角透明 ≥ 28%（验收同 badge V2.6）
  □ 缩略图显示风格化结果（不是原图），原图永久保留
  □ DB 的 images 字段是 JSON 数组（["/static/uploads/styled/{uuid}_v1.png"]）
  □ **dizical-image-style skill 文档完整**：SKILL.md + 跨 3 profile symlink 同步
  □ HEIC 文件浏览器不支持显示但后端能存（保留原图，未来转码）

□ 编辑/删除
  □ 历史卡片有 ✏️ / 🗑 按钮
  □ ✏️ → 内联展开，预填当前值
  □ 🗑 → confirm 后从 DB 删除
  □ 编辑完保存 → DB 更新 + 卡片收起

□ 全端显示重排（4 个露出点）
  □ prepare 页：assignment 卡片改为 4 部分结构（科目名 + ID + 要求 a)b)c) + 图片）
  □ prepare 页：无图时不占位，有图 flex-wrap 卡片行
  □ practice 页：楼层 1 选中科目显示完整 4 部分，展开全部可见本周所有
  □ practice 页：`reqTip` 支持 images 渲染（img src 来自 /static/uploads/styled/）
  □ config-practice-log Tab2：历史卡片标题 📅日期 · 第 N 期，科目区块 4 部分
  □ config-practice-log Tab2：images 在卡片底部 flex-wrap 陈列
  □ config-practice-log Tab3：本周总览 assignment 卡片改为 4 部分（无日期，已限本周）
  □ 图片点击可放大（lightbox / modal 预览，V1 简单：新 tab 打开）

□ 周次匹配
  □ lesson_date=周六 也能在 prepare 页显示"本周要求"
  □ 用 get_weekly_assignment_for_week 而不是 get_weekly_assignment
  □ prepare 页 backend 返回 images 字段（当前只返回 items，需补）

□ 测试
  □ tests/test_assignment_display.py 覆盖 4 个露出点的渲染（mock response 解析 HTML）

□ 文档
  □ docs/assignment-config.md 给家长看的图文说明
  □ CHANGELOG.md 加 V2.11 条目

□ 收尾
  □ STATUS.md 更新
  □ vibe-coding-log.md 加当日记录
  □ handoff-YYYY-MM-DD.md 写完整
  □ Obsidian 镜像（PRD + handoff 双写）
```

## §6.5 收尾 checklist (必做)

按 `AGENTS.md` 走全流程：测试 → commit → push → PR → STATUS → vibe log → handoff → Obsidian 镜像 → wiki 沉淀。

## §7 待办 / 决策

| # | 问题 | 状态 | 备注 |
|---|------|------|------|
| 1 | stage 字段手动 vs 自动优先级 | ✓ 已定 | UI 优先，留空走自动 |
| 2 | 图片存储路径 | ✓ 已定 | `data/uploads/raw/` 原图 + `data/uploads/styled/` 风格化。**取代** phase 1b 的 `data/assignment_images/` |
| 3 | 编辑模式 | ✓ 已定 | 卡片内联展开（轻量） |
| 4 | 删图策略 | ✓ 已定 | 删 DB + 删文件（V1 简单） |
| 5 | HEIC 支持 | ✓ 已定 | 后端能存，浏览器不显示无所谓 |
| 6 | 拆 PR 还是单 PR | ✓ 已定 | 单 PR（4 缺口一锅端） |
| 7 | **通用工作流还是 assignments 专属** | ✓ 已定 | **通用 dizical-image-style skill**，assignments 是首个应用，未来 practice log/praise/achievements 复用 |
| 8 | **风格化是同步还是异步** | ✓ 已定 | **同步**（用户点选图 → 等生图完成 → 显示缩略图）。耗时 30-60s 用 loading spinner 覆盖。如超时或失败 → 显示原图 + "风格化失败，重试"按钮 |
| 9 | **原图是否保留** | ✓ 已定 | **永久保留**（不删原图，作为未来重新风格化素材 / 备份） |
| 10 | **风格化结果是否版本化** | ✓ 已定 | 是（同原图多次风格化时 `_v{n}.png`），UI 默认最新版 |
| 11 | **目录结构** | ✓ 已定 | `data/uploads/raw/` 原图，`data/uploads/styled/` 风格化，DB 存 `/static/uploads/...` URL。**取代** phase 1b 设想的 `data/assignment_images/` 目录（更通用） |
| 12 | **dizicute 风格 prompt 模板** | ✓ 已定 | 复用 DESIGN.md token 描述（珊瑚红 #FF6B6B + 暖白 #FFF8F0 + chibi Q版 + "保留原图构图和细节"），跟 badge V2.3 enamel pin prompt 同源 |

## §8 实现备注

> 本节实施时填，包含实际遇到的坑 / 偏差 / 用户纠正。

## §9 相关文档

- `AGENTS.md` §Badge V2.1 工作流 (跟生图工作流不一样，图片走的是教学要求，不是 badge 流程)
- `DESIGN.md` dizicute 设计系统 (风格化 prompt 的 token 来源)
- `DEVELOPMENT_PLAN.md` §配图目录约定 (`.gitignore`)
- `.hermes/plans/assign-phase1b-image-storage.md` (CLI 端 images 已落地，本次只补 Web UI)
- `docs/表结构.md` (weekly_assignments schema)
- `docs/badge-image-workflow.md` V2.6 (badge 风格化 + 去背工作流，可作 dizical-image-style skill 的参考实现)
- `~/.hermes/profiles/dizical/skills/badge-image/SKILL.md` (badge-image skill，跟新 skill 独立演进)

## §10 通用 dizical-image-style skill 设计 (V1)

### 触发条件
- 用户上传图片需要"dizicute 风格化卡片"展示（assignments / practice log / praise / achievements 任一场景）
- 风格统一、保留原图构图/细节

### 输入
- 原图路径（jpg/png/heic）
- 风格描述（默认 dizicute，可选 vintage / line-art / watercolor）

### 流程 (5 步)
1. **校验原图** — PIL 打开，确认不是 0 字节 + 提取尺寸 + 转 RGB (HEIC 转 PNG)
2. **拼 dizicute 风格化 prompt**：
   ```
   STYLE_PROMPT = """Style the reference image as a charming kid-friendly card in the dizicute design system:
   - Color palette: coral red #FF6B6B primary, cream white #FFF8F0 background, ink blue #2C3E50 for outlines
   - Style: chibi Q-version, friendly, supportive, never busy
   - Composition: preserve original layout, characters, and key details from the reference image
   - Background: clean cream white #FFF8F0, transparent PNG
   - Output: polished illustration, orthographic front view, high quality, isolated object"""
   ```
3. **调 hermes image_gen (image-to-image 模式)**：
   ```bash
   hermes chat -q "$PROMPT" -t image_gen --profile dizical -Q --yolo --reference "$原图路径"
   ```
4. **去背 + 4 角验收** (复用 badge V2.6 流水线):
   - PIL 阈值 245 + rembg U2-Net 双路执行
   - 4 角 alpha=0 + 透明比例 ≥ 28%
   - 不达标 → 重试 1 次 + 返回错误
5. **落盘 + 返回**：
   - `data/uploads/styled/{原图uuid}_v1.png`
   - 返回 `/static/uploads/styled/{原图uuid}_v1.png`

### 失败处理
| 失败 | 处理 |
|------|------|
| hermes subprocess 超时 60s | kill 进程，返回原图 + "风格化超时，可重试" |
| PIL 4 角不达标 | 重试 1 次（改 prompt 加 "white background, transparent"）|
| 重试仍失败 | 返回原图 + "风格化失败"提示（不阻塞用户操作）|
| rembg 不可用 | 走系统 Python subprocess 兜底（badge V2.6 同样处理）|

### 跨 profile 安装
跟 badge-image 一样，3 profile symlink 同步：
- `~/.hermes/profiles/dizical/skills/dizical-image-style/SKILL.md` (主)
- `~/.hermes/profiles/coder/skills/dizical-image-style` (symlink)
- `~/.hermes/skills/dizical-image-style` (symlink)

### 调用模式
- **CLI**: `hermes chat -q "..." -t image_style --profile dizical` (跟 badge-image 一致)
- **API**: dizical 后端可暴露 `/api/image/style` 端点供 Web UI 调用 (本 PR 实现)
- **subprocess 跟 badge-image 区别**: image_style 接收 `--reference` 参数 (原图路径)，badge-image 不接收

### 跟 badge-image 关系
| 维度 | badge-image | dizical-image-style |
|------|-------------|---------------------|
| 输入 | text prompt only | text prompt + reference image |
| 输出 | 纯透明 enamel pin badge | 风格化卡片（保留原图元素）|
| prompt 模板 | enamel pin (cloisonné + 厚金边) | dizicute (珊瑚红 + chibi Q版) |
| 应用场景 | 成就徽章 | 配图 / 表扬卡 / 纪念卡 |
| 演进 | V2.6 (PIL+rembg 双路) | V1 (借 badge-image 流水线) |