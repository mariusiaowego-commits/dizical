---
source: ai-agent
type: prd
project: dizical
sprint: sprint-26091402-badge-ccg-modal-stage-2026-09-14
date: 2026-09-14
title: "AI-PRD-CCG卡面微调与modal把玩舞台-260914"
status: 已实施
---

# PRD · CCG 卡面微调与 Modal 把玩舞台优化

## 1. 需求背景与目标

在 PR #328 (Deploy #126) 生产上线后，Dad 在真机端验收 CCG 卡牌交互并提供现场截图，提出了 4 项核心体验优化诉求：
1. **Modal 遮罩太暗太闷**：黑色半透明遮罩将卡牌舞台空间压抑，需要更通透、现代的磨砂毛玻璃质感。
2. **卡背故事未撑满高度**：短/中文本未充分利用纵向空间即被强行裁切，下方留下大片空白。
3. **展开全文胶囊位置与热区问题**：原胶囊置于标题旁且整个故事文本区拦截点击，导致用户想翻转卡背却误触打字机托盘。
4. **淡色主题 Hover 像蒙版**：鼠标悬停时卡面整片泛白提亮，原画对比度下降严重，缺乏真实跟随光斑的立体聚光感。

### 核心目标
- 将 Modal 遮罩全面升级为磨砂玻璃 D 方案（高通透米白渐变）。
- 实现卡背故事区自适应填满，仅在真实物理溢出时优雅呈现底部渐隐与独立展开胶囊。
- 修复展开胶囊热区与翻卡事件隔离，实现“点正文翻卡、点胶囊呼出打字机”精准交互。
- 彻底解决 Pearl/Mint/Sakura 淡色系主题的“蒙版感”，还原清晰原画与灵动聚光灯效果。
- 绝对保持 3D 空间变换参数不变，深色主题保持逐像素零差异。

---

## 2. 详细功能需求

### FR-1: Modal 舞台遮罩磨砂玻璃优化 (D 方案)
- **视觉规格**：
  - 遮罩背景色：`rgba(253, 250, 244, 0.55)` (象牙暖白 55% 透明)。
  - 背景模糊度：`backdrop-filter: blur(7px);`（配合 `-webkit-backdrop-filter`）。
- **交互边界**：
  - 点击遮罩外部空白区域优雅收起 Modal。
  - 卡牌处于舞台中央，保持自然纵深感，不再出现生硬黑幕。

### FR-2.1: 卡背故事区空间自适应与真实溢出检测
- **排版要求**：
  - 移除硬编码的 `-webkit-line-clamp: 4`，卡背故事正文 `.ccg-back-val` 采用纯 CSS Flex 布局自然撑满可用高度。
  - 移除按字数（如 `>50` 字）猜测溢出的陈旧逻辑，使用真实物理尺寸判定（`scrollHeight > clientHeight + 1`）。
  - 当且仅当真实物理溢出时，触发 `.has-overflow` 状态，对故事正文施加底部 24px 渐隐蒙版：
    `mask-image: linear-gradient(180deg, #000 calc(100% - 24px), transparent 100%)`。
  - 若文本完全能容纳，则不显示渐隐蒙版，不显示展开胶囊，文本垂直居中或自然流动。

### FR-2.2: 独立“展开全文 ▾”胶囊与精准事件分流
- **视觉定位**：
  - 胶囊独立置于故事区域底部右侧（`margin-top: auto; align-self: flex-end;`），文案为 `展开全文 ▾`。
  - 伪元素放大触控热区至 $\ge 44 \times 32\text{px}$，满足移动端及 iPad 触控规范。
- **事件穿透与隔离**：
  - 卡背故事正文与背景保持 `pointer-events: none`（或将事件透传），用户点击故事空白或文字区域时，直接穿透至卡背容器，触发“翻转回正面”交互。
  - 展开胶囊设置 `pointer-events: auto`，点击胶囊时调用 `event.stopPropagation()` 阻止事件向上冒泡，仅触发打字机完整故事托盘展开/收起。

### FR-3: 淡色主题光照层真实高光化 (去蒙版)
- **作用域**：
  - 严格限制在 `[data-ccg-theme="pearl"]`, `[data-ccg-theme="mint"]`, `[data-ccg-theme="sakura"]` 选择器内。
- **物理光照优化**：
  - 聚光反光梯度 `--theme-glare-stops` 在 65% 处平滑收敛归零至 `transparent`，避免光斑扩散至全卡导致整体泛白。
  - 镭射高光混合模式 `--theme-foil-laser-blend` 恢复为 `color-dodge`，增强光泽锐度。
  - 镜面反射混合模式 `--theme-foil-spec-blend` 恢复为 `screen`。
  - 箔层基础不透明度 `--theme-foil-op` 从 0.55 下调至 0.42，使底层立绘原画细节与对比度完全保真。

---

## 3. 非目标与约束边界 (Strict Non-Goals)

1. **3D 几何与动画参数绝对禁止修改**：
   - 包含：`maxTilt = 22`，`ry = +nx * 22`，`rx = -ny * 22`，`state.lift = 20`，`IDLE_Y = 14%`，`perspective = 980px`，`perspective-origin = 50% 48%`，四角极限倾角 $\pm 21.82^\circ$ 等。
2. **深色主题零影响**：
   - `azure`, `bamboo`, `coral`, `imperial`, `frost` 等深色主题样式必须保证逐字节隔离，测试验证逐像素差异为 0。
3. **纯前端交付**：
   - 不修改后端 Python 代码，不改动 SQLite / Cloud MySQL 数据库结构或记录，不改动 API 协议。
4. **历史未决项隔离**：
   - `badges.html` 历史旧卡 `No.001` 回落问题按规划延后，本期不涉及。

---

## 4. 验收标准与验证矩阵

| 编号 | 需求项 | 验收标准 | 自动化探针 / 测量值 | 判定 |
|------|--------|----------|-------------------|------|
| 1 | Modal 遮罩 | 象牙米白 55% + blur 7px | `rgba(253, 250, 244, 0.55)`, `blur(7px)` | PASS |
| 2.1 | 故事高度撑满 | 移除 clamp，可用高度充分填充 | len=395 行数由 4 提升至 14/15，撑满 320px | PASS |
| 2.1 | 溢出渐隐 | 真实溢出挂 24px 渐变 mask | `mask-image` 仅在 `.has-overflow` 出现 | PASS |
| 2.2 | 胶囊钉底右侧 | 底部对齐，文案符合要求 | `margin-top: auto`, `展开全文 ▾` | PASS |
| 2.2 | 胶囊独立热区 | 仅胶囊可点，正文穿透翻面 | pill_hits=52, val_hits=0, 正文点击翻卡成功 | PASS |
| 2.3 | 短故事无扰 | 短文本无 mask，胶囊隐藏 | len=30/180/300 时 `display: none` | PASS |
| 3 | Pearl 去蒙版 | 高光局部聚焦，原画对比保留 | gt6% 像素从 89.39% 降至 47.93%，中心对齐 | PASS |
| 4 | 深色主题隔离 | Azure 主题静止/悬停无变化 | Max Diff = 0, Mean Diff = 0.0000 | PASS |
| 5 | 全局回归 | Python 全量单元测试全绿 | 768 passed, 8 skipped, 0 failed | PASS |
