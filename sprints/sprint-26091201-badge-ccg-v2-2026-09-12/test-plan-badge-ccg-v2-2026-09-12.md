---
id: 26091201-test-plan
type: test-plan
version: 0.1.0
date: 2026-09-12
status: 进行中
tags: [test-plan, dizical, badge, ccg, theme]
---

# TEST-PLAN — 徽章 CCG v2

## 1. 视觉验证 (dad 真机, agent 不自 verify)

- 入口：`http://10.0.0.5:8765/static/badge-ccg-demo.html?mode=holo`
- 三端：Mac 1440 / iPad 竖 744×1133 / iPad 横 1133×744

## 2. 回归清单 (v1 修复项不能被打破)

- [ ] 指针移出画面窗(说明栏/页脚)时，镭射/防伪层无直角硬边 (commit 6bef848)
- [ ] 光斑滑出金框不压深色 (8af7ccc)
- [ ] holo-head 与金框间隙 +6px 级，不重叠
- [ ] 静止态聚光灯停在上金边，不压图案正中

## 3. 自动化

- `pytest tests/test_badge_claim.py`
- 三端 0 JS 报错（console 抓取）

## 4. 逐层消融探针 (伪影定位工具)

- `/tmp/ccg_ablate.py`：卡面平放 + 逐层 display:none + 贡献剖面 (行/列 20 带)
- 判据：某层贡献剖面出现「0% → 高阶跃」= 该层画出直角边界 ⇒ 就是伪影源
