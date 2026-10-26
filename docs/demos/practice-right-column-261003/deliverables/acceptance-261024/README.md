---
source: ai-agent
project: dizical
sprint: demo-v3.6
date: 2026-10-25
---

# demo v3.6 验收包（2026-10-25）

## 怎么看

- 浏览器（推荐，可点可滚）：`docs/demos/practice-right-column-261003/deliverables/acceptance-261024/index.html`
  - 走本地服务：`http://127.0.0.1:8771/practice-right-column-261003/deliverables/acceptance-261024/index.html`
- 打印版：`dizical-demo-v3.6-验收包-261025.pdf`（A4 横向 11 页，图片为 2× 截图）
- 原始截图：`shots/`（31 张，2× DPR）

## 覆盖范围

| 分区 | 内容 | 张数 |
|---|---|---:|
| 主画布 1133 | 组合 1/2/3 × 准备/计时 | 6 |
| 主画布 744 / 440 | 组合 1/2/3 × 准备/计时 | 12 |
| 深墨皮肤 | 1133、744 组合1 计时 | 2 |
| 单卡页 | A / B / S / D / R / Q | 6 |
| 工具页 | 组合自选台、旧组合视图、骨架、共享尺子 | 4 |
| 总览页 | demo 入口页 | 1 |

## 本轮（S12）改动

1. **run 态直切视口/组合塌陷**（S8/S10/S11 连续三轮遗留）—— 三根因全修：feed 模式 `container-type: size` 吞掉内容高度、`updateCardSlotGeometry()` 把 `height:100%` 解析成 100px 锁死 iframe、`ticketBox()` 在票夹隐藏时返 0 导致组合高度基准丢失。附带把 `remeasureNarrow()` 改为去抖（rAF + 240ms）。
2. **「分钟」下标**：`calc(var(--readout-digits-h)/2)` + `font-weight:250`；实测 1133 38px / 744、440 33px。
3. **卡槽抽屉式落位**：`pkCardToSlot` / `pkCardToSlotFeed` 加 74% `+2px` 压槽沿、88% `-0.5px` 回弹；实测 832ms 出现 → 1057ms 压过 → 1133ms 归零（301ms），delay 0.78s 不变。
4. **记录小卡“次数”取错源**：原来读收拢态 `#pkCollapsedSessionVal`（本次练习内容），拼出「未选内容 次」；改读今日记录胶囊 `#pkRecords` 的 `N次`，分钟也改读胶囊的 `N分`。实测组合2 显示「3 次 / 15 分」。

## 门禁

```
node tools/verify.js --strict                 # 9 组合 × 11 项 PASS（exit 0）
python3 tools/sync-demo-templates.py --check  # 6 模板字节级一致
python3 tools/check-layout-modes.py           # CSS [data-vp] = 0
git diff --check                              # 干净
```

## 已知边界

- 截图只证结构与排版；**动效手感（插卡、票夹三态变形、节拍器拖拽）必须真机看**。
- 8771 服务只绑 `127.0.0.1`；iPad 访问需改绑 `0.0.0.0`。
- 工作区未 commit（含 dad 的 `data/` 与 PLAN 文档），未跑 `stamp-demo-version.py`，页面版本停在 demo v3.6。
