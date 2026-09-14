# test-plan · sprint-26091402 · badge CCG 卡面+modal 微调

## 1. 自动化测试

- 本 sprint **未改后端 / 未引新依赖 / 不动 pytest** —— 不需要新 unit test。
- 全量回归（保险起见，建议 dad commit 前跑一遍）：

```
cd /Users/mt16/dev/dizical
pytest --ignore=tests/config_ui_fixes -q
```

期望：基线 **768 passed / 8 skipped / 0 failed**（基线锚点 = sprint-26091401 收尾）。

## 2. 独立闸门（真实指针 + pixel 量化，非自报）

复现台：`/tmp/ccgacc/`、`/tmp/ccgcmp/`，headless Chrome CDP **9447**，静态服 **8793**（harness_brief_b.html / harness_brief_e.html / harness_story.html）。

| # | 探针 | 实测 | 验收线 |
|---|------|------|--------|
| 1 | `probe9_briefE.py` —— modal overlay bg + backdrop | `rgba(253,250,244,0.55)` + `blur(7px)` | demo D 选中 |
| 2.1 | `probe10_story.py` —— 故事撑满率（len=30/180/300/450/700） | 12/51/83% 无 overflow + display:none；128/196% 真溢出挂 mask | 容器即上限 |
| 2.1 | mask 渐隐内容 | `linear-gradient(rgb(0,0,0) calc(100% - 24px), rgba(0,0,0,0) 100%)` | 仅溢出挂底渐隐 |
| 2.2 | `probe10_story.py` —— 胶囊热区（len=450） | pill_hits 52、val_hits **0**、btnRect `[824,686,74,24]` | 唯一可点 |
| 2.2 | `probe10_story.py` —— 打字机三态（真实指针） | tap1 typing 45 → 1.7s 105 → tap2 全显 450 → tap3 关 | 3 态全过 |
| 2.2 | `probe10_story.py` —— 点正文不翻面 | flipped=true（保持翻面状态） | 透传正确 |
| 3 | `probe_hover_file.py` —— pearl hover 局部化 | gt6%=47.93%、max @ [51.9%, 31.0%] | ≤ 55% + 卡面 30–70% |
| 3 | `probe_hover_file.py` —— azure 回归 | max=237 / gt6%=97.43 / gt12=147667 / gt25=136290 逐字段与 before 相同 | = 0 差异 |
| 3D | `probe9_briefE.py` —— perspective / origin | 980px / 210px 315px | 不动 |

**探针口径硬约束**：全部 `mouse.down/up` 真实指针事件，零 `.click()` 合成当 PASS。

## 3. 未覆盖 / 交 dad

- **视觉终验交 dad 真机**：2.2 胶囊热区真机点验、3 种故事长度（短/中/长）+ 真高光化观感。
- **生产路径未跑**：本 PR 合并 + deploy 前，生产仍是 #126 旧 CSS/旧 app.py。deploy 后用 `?cb=` 破缓存 + curl badge-ccg.css 内容长度核对。
- 老 P1（badges.html `No.001` 回落）按 dad 指示本 sprint 不动。
- `tests/config_ui_fixes`（缺 bs4）按 dad 指示未动。
- `_b6ab*.html` / `data/` / `dizical-ai/` / `docs/ai-inspire-plan-integration.md` 等未跟踪产物**未纳入本 sprint**，deploy 验收成功后建议单独清理。

## 4. 残留风险

- **3D 几何参数硬边界**（maxTilt 22 / ry=+nx*22 / rx=-ny*22 / state.lift 20 / IDLE_Y=14% / perspective 980px / origin 50% 48% / 四角 ±21.82°） —— 探针已证逐字符未动，**dad review diff 时请再扫一遍**。
- **`.ccg-back-inner` 全局 `pointer-events:none`** —— 只对 `.ccg-story-expand-btn` 单点恢复 `auto`；卡背再加可点元素须同样恢复（技术债务）。