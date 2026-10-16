# brief-grok-fix-261016 · canvas-01 第一轮（owner: grok / 只改 canvas-01.html）

先读：同目录 `PLAN-demov34问题-261016.md`（我实测的根因与数）
红线：画布本体零改动（sha256 e86d4bc56163218d）· 不 commit / 不 push / 不加依赖

## 你现在就能做的（不依赖 agy 规格）

### ① 744 / 440 档：卡片高度按内容自适应（item 7.3 / 7.4 / 8）
```
现状实测（自定义六卡全开 · 744）：A/B/S/D/R/Q 全部 **708×460 固定**（y=604/1088/1572/2056/2540/3024）
根因：feed 档下卡高被写死 460
要求：744/440 档卡高**由内容决定**：
      ① 每卡 clientHeight == scrollHeight（卡内不出现纵向滚动条；R 卡尤其）
      ② 内容多的卡自然变高、内容少的卡变矮（给"内容量 → 高度"的正相关证据：至少两卡对比）
      ③ 1133 档的等高规则**不受影响**（组合1/2/3 仍按票卡高闭合）
自检：三档 × 六卡逐张给 rect + clientHeight/scrollHeight
```

### ② R 卡底色统一（item 6.3）
```
现状：`#czRecordsMini` 计算背景 = **rgb(232,229,224)**（灰）；dad 要求与"今日练习时长卡"统一 UI
基准：`practice-duration-card-01-v3.html` 的卡片底色/token（不要自己造色）
要求：R 迷你卡改用同一套底色与描边语言；给 before/after 计算色值
```

### ③ 清掉过时抽屉 + 扫"卡片下方的淡色底层"（item 5）
```
线索：`#pkRecordsDrawer`（旧"今日练习记录"抽屉，bg #FFF8F0 + 白色 ARTICLE.pk-drawer-item）停在 x=1133（画布右缘外）
      横向滑动时会露出来 → 疑似 dad 说的"卡片下面还有一个淡色背景"
要求：① 该抽屉若已废弃 → 从可见层里彻底移除/隐藏（保留 id 兼容可选，但不得出现在可视区）
      ② 在 1133 / 744 / 440 三档分别扫一遍：**卡片下方/右侧 60px 内有无非透明底层元素**（bg / shadow / pseudo），给清单
dad 给的色值是 #EEE93E（黄）——我在代码、四份文档的计算样式、6 张截图里都找不到该色；
      若你找到了确切元素，直接修；找不到就把"可疑底层"清单给我，我回给 dad 确认
```

### ④ 记录弹窗（item 3/4）——先确认现状
```
实测：点击 R 迷你卡 → `.popout-backdrop.is-open` + `.popout-panel` 600×274；body 内 `#czPopFrame`（srcdoc 48KB）
      渲染出表头「科目 总时长 速度 单次 明细 占比」+ 数据行
要求：① 给出现状证据（面板 rect + 表行数）② 若弹窗在 744/440 档过小/被裁 → 按窄档改成近全屏 + 表格可横向滚动
```

## 等 agy 规格后再做（别抢）
```
item 1   A 卡内部重排（宽扁比例）+ knob/arc/叠层错位  ← 等 pixel 走查 + spec-agy-eh-combo1-261016
item 2   卡槽做进 dashboard（现在高仅 18px）        ← 等 spec-agy-slot-size-261016
item 6.2 D 卡元素取舍（组合1 224 宽 / 组合3 360 宽） ← 等 spec-agy-combo1-d-r-261016
item 7.2 D 卡 744 档形态                            ← 等 spec-agy-feed744-261016
item 7.5 S 竖条 → 744/440 横条                      ← 等 spec-agy-s-hbar-261016
```

## 汇报
每条：真会话实测数（before → after）+ verdict 原文；负控至少跑一次 `?negctl=bus`（必须红 + verdict 带数值）。
