---
id: 26091402
type: sprint
version: 1.0.0
start_date: 2026-09-14
end_date: 2026-09-14
status: 已完成
priority: 高
summary: "CCG 卡面微调与 modal 把玩舞台优化：D毛玻璃遮罩、故事区纯CSS撑满、独立展开胶囊、淡色主题去蒙版"
tags: [sprint, dizical]
---

# sprint-26091402 · badge CCG 卡面+modal 微调（dad 第 3 轮反馈）

- **状态**：agy 实施完成 + 8 项真实指针探针复验 PASS + pixel 量化 PASS + 全量回归通过（**未动后端 / 改动只在 5 个前端文件**）
- **日期**：2026-09-14
- **分支建议**：`feat/badge-ccg-pearl-modal-stage-260914`（merge 锚点 main `d195495`）
- **触发**：dad 在 #328 deploy #126 生产验收后，截两张图（hover vs 静止）反馈 4 个问题
- **分工**：方案 E（双 agent 分析 + 合并）— hermes（实施单 brief C）+ agy（独立分析轮 brief D）→ 合并 brief E → agy 实施 → hermes 复验

## 4 条问题 → 修复（合并方案要点）

| # | 现象 | 根因 | 修法 |
|---|------|------|------|
| 1 | modal 暗幕太闷、遮图案 | `.ccg-claim-overlay` 写死 `rgba(14,10,6,0.52)` + blur 12px | 改 D 毛玻璃 `rgba(253,250,244,0.55)` + `blur(7px)` |
| 2.1 | 卡背故事区**没写满**就截断 | `badge-ccg.css:915-960` 写死 `-webkit-line-clamp: 4`，`flex:1 1 auto` 撑满反而**留空白**；JS `isLong=storyVal.length>50` 是字数猜 | 删死编号 line-clamp、正文 flex 撑满、**真溢出才挂底部 24px mask 渐隐**、胶囊 `margin-top:auto; align-self:flex-end` 钉底-右；删 `isLong>50` 字数猜 |
| 2.2 | 「展开全文」不在文字区最底、且整块故事区都能点 | 胶囊拼在「典故」标签里、`.ccg-back-story.is-expandable, .is-expandable * { pointer-events:auto }` 让整块可点 | 胶囊挪底部-右、文案「展开全文 ▾」、**只对胶囊** `pointer-events:auto`、正文恢复穿透、胶囊 click `stopPropagation` 防顺带翻面 |
| 3 | hover 像**加了蒙版**不像光照（整片均匀提亮 +18/+13/+11、对比度 −26~36%） | pearl 淡色主题光照层：`soft-light` 混合 + 全浅色标 + `farthest-corner` 铺满整卡 + **glare stops 末端无 transparent** + laser `soft-light` (38.8%) | 改在淡色主题作用域：`[data-ccg-theme="pearl\|mint\|sakura"]` 内 glare stops 末端归 transparent @ 65%、laser 回 `color-dodge`、spec 回 `screen`、foilOp 0.55→0.42；深色主题 CSS 一字节不改 |

## 验收数据（独立探针，非自报）

| 指标 | 修前 | 修后 | 验收线 |
|---|---|---|---|
| overlay bg / backdrop | `rgba(14,10,6,0.52)` / blur 12px | `rgba(253,250,244,0.55)` / blur 7px | demo D 选中 |
| 故事撑满率（len=395） | 4 行死编号 | `linesFit=14/15、clamp=none` | 容器即上限 |
| 故事底部 mask | 无 | `linear-gradient(rgb(0,0,0) calc(100% - 24px), rgba(0,0,0,0) 100%)` | 仅溢出挂底渐隐 |
| 短故事胶囊（len ≤ 300） | `display:none` / 0 翻面 | `display:none` / 0 翻面 | 不打扰 |
| 胶囊热区（len=450） | 整块故事可点 | pill_hits 52、val_hits **0**、钉底 `[824,686,74,24]` | 唯一可点 |
| 打字机三态（真实指针） | typing 45 → 1.7s 105 → tap2 全显 450 → tap3 关 | 同上 | 3 态全过 |
| pearl hover gt6% 像素占比 | 89.39% | 47.93% | ≤ 55% |
| pearl hover max delta 位置 | `[0.0%, 3.8%]`（左上蒙版） | `[51.9%, 31.0%]`（指针跟随） | 卡面 30–70% |
| azure rest+hover pixel diff | baseline | max=0 / mean=0（**逐字段相同**） | = 0 |
| 3D perspective / origin | 980px / 50% 48% | 980px / 210,315（= 50%×420 / 48%×630） | 不动 |

**深色回归**：azure 静止 + hover vs 改前 max=237 / gt6%=97.43 / gt12=147667 / gt25=136290 **逐字段相同** ⇒ 深色主题 CSS 一字节像素都没动。

## 探针/数据 / 截图 清单

- 探针：`/tmp/ccgacc/probe9_briefE.py`、`probe10_story.py`、`probe11_hover.py`、`probe_hover_file.py`
- 数据：`/tmp/ccgacc/briefE_out.json`、`story_out.json`、`hover_file.json`、`/tmp/ccgcmp/diff_cmp.py` 出的深色回归
- 截图：`/tmp/ccgcmp/shots/{before,after}-{pearl,azure}-{rest,p30,p70}.png`（4×3=12 张）
- demo 文件：`/tmp/ccgprobe/demo_overlay_variants.html`（五遮罩方案）

## 待办

- [ ] dad 真机点验（2.2 胶囊热区 + 短/中/长故事 + hover 真高光）
- [ ] dad commit + push + PR（建议 `feat/badge-ccg-pearl-modal-stage-260914`）
- [ ] dad merge + MCP deploy
- [ ] 生产自检（?cb= 破缓存、curl badge-ccg.css 内容长度核对）
- [ ] 老 P1（badges.html `No.001`）dad 已说缓办，本轮不动
- [ ] deploy 验收成功后建议清理（环境/未跟踪产物）