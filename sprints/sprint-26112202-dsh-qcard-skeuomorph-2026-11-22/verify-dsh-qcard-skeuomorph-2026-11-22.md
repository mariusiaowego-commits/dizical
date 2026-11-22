---
type: sprint
sprint: "26112202"
doc: verify
date: 2026-11-22
---

# 验收记录

环境：8765（`dizical.kid-app` 注册端口），worktree `/Users/mt16/.codex/worktrees/1482/dizical` 代码，
Playwright Chromium + `deviceScaleFactor=2`，数据源云端 MySQL（默认科目 + `小看戏` 12 张卡）。

## 1. 静态

```
$ /usr/bin/python3 /private/tmp/qcard_nodecheck.py
blocks: 13 fails: 0
```

提取器只取内联段（`<script>` 且不含 `src=`，正则 `<script(?![^>]*\bsrc=)[^>]*>`），
每个文件独立跑 `node --check`。

## 2. 单测

```
$ pytest tests/test_practice_dsh*.py tests/test_practice_sessions*.py tests/test_practice_timer_frontend.py tests/test_config_practice_page.py
203 passed

$ pytest tests/ -q --ignore=tests/config_ui_fixes
5 failed, 1237 passed, 8 skipped
```

5 个失败与基线一致（`test_achievements_card_no`、`test_calc_seasonal_count`、`test_config_design` ×3），
本次新增 3 条结构契约（`.qc-shell` 实体边 / 宿主摘壳 / 2D 叠卡）全绿，计入 1237。

## 3. UI（Playwright，8765）

| 用例 | 结果 | 实测 |
|---|---|---|
| 440 档模块等宽左对齐 | PASS | A/Q/R `left=16, w=408` |
| 440 四角描边（浅色） | PASS | ΔY tl 52.5 / tr 52.5 / bl 39.7 / br 39.7 |
| 375 档（canvas `scale≈0.84`）四角 | PASS | ΔY 52.0 / 52.5 / 39.7 / 39.7 |
| 1133 档模块等高 | PASS | A/Q/R `top=78, bottom=822, h=744` |
| 1133 四角描边 | PASS | ΔY 52.5 / 52.5 / 40.1 / 39.7 |
| 深墨 1133 四角描边 | PASS | ΔY 37.7 / 37.7 / 52.8 / 53.7（先重推科目再拍，避开切肤重置） |
| 翻页（下一张/上一张） | PASS | 2026-11-21 → 11-14 → 11-21 |
| 翻页中间帧有 transform | PASS | 90ms `matrix(0.9999,-0.0129,0.0129,0.9999,-27.4,0.7)` + `is-dragging` |
| 翻页后四角 | PASS | 与翻页前同值（52.5/52.5/39.7/39.7） |
| 底栏在纸面内 | PASS | `sheetBottom=394, footBottom=394` |
| `__czQFeedAudit` | PASS | `{F1:true, F2:true, F3:null(无便签), ok:true}` |
| dots 收拢 | PASS | 12 张卡只渲染 7 点 |

四角判据：沿 45° 从角点向内采样 20 步，基准取对角线末端的纸面中位数；
浅色要求 `max(基准−像素) ≥ 20`，深墨要求 `max(像素−基准) ≥ 18`。

## 3.1 复审修复（第二轮，agy + Hooke + 自查）

`$ /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 /private/tmp/qcard_probe3.py`
→ **6 / 6 PASS**（1133×744，`deviceScaleFactor=2`）：

| 用例 | 结果 | 实测 |
|---|---|---|
| 空态卡不渲染底栏 | PASS | `hasFoot=false`，`class="deck-card is-empty is-active"` |
| `cz-feed` 短卡内印线闭合 | PASS | `flex: 1 0 auto`，`__czQFeedAudit.ok=true` |
| 深墨按钮不再被旧规则压成实底 | PASS | 删除 `:root[data-skin="ink"] .deck-btn` |
| 旧 `cz-vp440` 字阶反杀清理 | PASS | `.card-head-title` 18→12px；`.qc-bay-val` 15.5/14.5px 与 `.qc-bay` padding 删除 |
| `.qc-shell` 外落影 | PASS | `0 1px 2px --qc-drop-near, 0 12px 26px -12px --qc-drop-far` |
| `--font-mono` 补齐 | PASS | 日期 `font-family` 实算为 `ui-monospace, SFMono-Regular, Menlo…`，`11.5px/700` |
| 日期不被宿主 `!important` 压掉 | PASS | `html.cz-fill:not(.cz-qcard) .card-date-badge` → 实算 `11.5px/700` |
| 活页孔命中垫不重叠 | PASS | `pad=12px`、`pitch=16px`、`gap=10px` |
| 跨张点选直接换内容 | PASS | 点第 7 颗 → 90ms 内 `data-index=6`、`is-dragging` 计数 0 |

落影与描边的分工：`.qc-shell` 负责外落影、1px 纸边与 2px 纸厚切面（`padding-bottom:2px`），`.qc-sheet` 负责裁剪纸面，
`.deck-card` 只做位姿；三者都不带 `preserve-3d`。

## 3.2 UIUX 审计（pixel）落地项

`$ /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 /private/tmp/qcard_probe5.py`
（`/private/tmp/qcard_probe6.py` 补环节名与正文的对比）：

| 项 | 结果 | 实测 |
|---|---|---|
| 环节名高于正文（三档） | PASS | 1133 档 18 vs 16；440 档 17 vs 16；368 档 16 vs 15 |
| 日期不再是「越窄越大」 | PASS | 12px（556）/ 11.5px（≤480）/ 11px（≤380） |
| 删掉 iPhone 视口字号覆盖 | PASS | `html.cz-vp440 .req-p` 实算 16px（原 17px），`.deck-btn` 回到 13px |
| 序号下限 | PASS | 368 档 11px（原 10px，iPad 0.8 缩后约 8px） |
| 速度章去掉看不见的内框 | PASS | 删 `inset 0 0 0 1px`；`-1.5deg` + `transform-origin: center` |
| 便签恢复投影 | PASS | 实算 `drop-shadow(rgba(44,62,80,.1) 0 1px 1px) drop-shadow(… 0 2px 6px)` |
| 深墨登记带与纸面分层 | PASS | `--qc-foot #1B222A`（对纸面 >1.08:1） |
| 深墨纸厚切面不再读成黑缝 | PASS | `--qc-edge-thick #3A434F`（比纸面亮） |
| 线语言分层 | PASS | 正文分组线 / 卡底分隔降为 `--qc-rule-soft`（浅 `.07` / 深 `.09`），内印框保持 `.13` |

**未采纳（需 dad 定或超范围）**：

- 卡底「`No.` 行 + 登记带」合并成一条 56px 带 —— 属结构性改版，本 PR 不动。
- 「最新」去掉细印框、科目 serif 改 21/20/19、内印线 8→10px、dots 改纯指示 —— 口味/交互决策，留待 dad 看真机。

## 4. 失败与跳过

| 项 | 状态 | 原因 |
|---|---|---|
| `runContractAudit` 的 `three viewports width must differ: 1133(330), 744(330), 440(330)` | **failed（历史项）** | 嵌入态 `html.cz-fill .req-card-chassis { width:100% }`，该断言只对独立打开有效。v3.54 主 checkout 同断言同样 330/330/330。 |
| `runContractAudit` D4-2 深墨未选点对比度 1.14:1 | **failed（历史项，审计口径缺陷）** | 审计 `getLum` 把未选点按浅底 `(240,243,246)`、`chLum=0.89` 混合，深墨下恒定误报：同一公式复算 v3.54 的 `#DED7CD` 为 **1.28:1**，同样不达 3.0:1。按真实底色复算 —— 深墨登记带 `#202730` 上 **4.24:1**、纸面 `#262D35` 上 **4.04:1**、`#2B323A` 上 **3.90:1**；浅色 `#F5F1E8` 上 **3.30:1**（与审计 3.33:1 同量级）。全部 ≥ 3.0:1。 |
| iPad Safari 真机四角 | **skipped** | 本机只能跑 Chromium；WebKit 的 `scale(k)` 重采样需 dad 在 iPad 上目视确认。 |
| 拖拽 >85px 抛飞后的四角 | **skipped** | 单卡数据下无可抛飞目标；按钮翻页已覆盖同一 `navTo` 路径。 |

### 4.1 已知问题（本 PR 未修，需 dad 裁决）

- **切深墨后 Q 卡回到空态**：`__cz.setSkin('ink')` → 宿主 `syncAll()` 重建模块 iframe → Q 模板回到
  初始 `ASSIGNMENTS_DATA = [{ id:'empty' }]`，3 秒内未被重新推送。`git diff e3c5f5d..HEAD` 未触碰
  `setSkin` / `syncAll` / `syncDashCover`，属既有行为；修它要改宿主重建顺序，超出本 PR 范围。
  验证影响：深墨截图需先重推 `updateSubjectAssignment({name:'小看戏'})` 再拍（本轮已如此）。
- **`total > 7` 时点窗口无总数提示**：已补 `title` / `aria-label="第 X / N 周"`，未加可见计数，
  避免在登记带上再叠一层文字。
- **新增单测仍是 CSS 文本断言**：`tests/test_practice_dsh.py` 里 3 条结构契约只能挡住选择器被删，
  挡不住 `box-shadow` 缺失或宿主 `!important` 覆盖。渲染级断言需要浏览器，本仓库 pytest 无此依赖，未加。

## 5. 截图

- `/private/tmp/v-440-before.png`（440 浅色）
- `/private/tmp/v-375.png`（375 缩放档）
- `/private/tmp/v-1133.png` / `/private/tmp/v-1133-ink.png`（横排浅/深）
